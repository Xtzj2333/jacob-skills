#!/usr/bin/env python3
"""sync-cowork-skill: one-way sync from Cowork to the jacob-skills marketplace.

SAFETY PROPERTIES:
1. The Cowork file is READ-ONLY here. This script never writes to Cowork.
2. Default mode is dry-run. The user must re-invoke with --apply to mutate
   the marketplace repo.
3. Sensitive-content scan is mandatory. With findings, --apply refuses unless
   SYNC_OVERRIDE_SENSITIVE=1 is set in the environment.
4. The marketplace repo is required to be clean (no uncommitted changes)
   before --apply will proceed — prevents tangling sync with unrelated edits.
5. The skill folder is mirrored fully (new/changed files copy, deleted files
   removed in GitHub). plugin.json sits OUTSIDE the synced folder, so
   marketplace-only metadata is never overwritten.
"""

from __future__ import annotations

import argparse
import difflib
import glob
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
COWORK_SKILLS_GLOB = str(
    HOME
    / "Library"
    / "Application Support"
    / "Claude"
    / "local-agent-mode-sessions"
    / "skills-plugin"
    / "*"
    / "*"
    / "skills"
)
MARKETPLACE_REPO = HOME / "jacob-skills"

SENSITIVE_PATTERNS: list[tuple[str, str]] = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "email address"),
    (r"\btracy\b", "name: tracy"),
    (r"tracywu", "handle: tracywu"),
    (r"@uchicago", "uchicago email"),
    (r"jacobz@", "specific jacob handle"),
    (r"@gmail\b", "gmail address"),
    (r"@outlook\b", "outlook address"),
    (r"@icloud\b", "icloud address"),
    (r"帅帅", "personal nickname (帅帅)"),
    (r"appointment confirmation", "real-appointment marker"),
    (r"\bSSN\b", "ssn"),
    (r"\b\d{3}-\d{2}-\d{4}\b", "ssn-shaped number"),
    (r"\b\+?1?\s*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "us phone number"),
    (r"\bsk-[A-Za-z0-9_-]{20,}\b", "openai-style api key"),
    (r"\bghp_[A-Za-z0-9]{30,}\b", "github personal access token"),
]


def find_cowork_skill_dir(skill_name: str) -> Path | None:
    matches = glob.glob(f"{COWORK_SKILLS_GLOB}/{skill_name}")
    matches = [m for m in matches if os.path.isdir(m)]
    if not matches:
        return None
    if len(matches) > 1:
        print(
            f"[sync-cowork-skill] WARNING: multiple Cowork copies of '{skill_name}' found:",
            file=sys.stderr,
        )
        for m in matches:
            print(f"  {m}", file=sys.stderr)
        matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        print(
            f"[sync-cowork-skill] using most recently modified: {matches[0]}",
            file=sys.stderr,
        )
    return Path(matches[0])


def find_marketplace_skill_dir(skill_name: str) -> Path:
    return MARKETPLACE_REPO / "plugins" / skill_name / "skills" / skill_name


def list_files_relative(root: Path) -> set[Path]:
    if not root.exists():
        return set()
    return {p.relative_to(root) for p in root.rglob("*") if p.is_file()}


def show_text_diff(src_text: str, dst_text: str, src_label: str, dst_label: str) -> bool:
    diff_lines = list(
        difflib.unified_diff(
            dst_text.splitlines(keepends=True),
            src_text.splitlines(keepends=True),
            fromfile=f"GitHub: {dst_label}",
            tofile=f"Cowork: {src_label}",
            n=3,
        )
    )
    if not diff_lines:
        return False
    sys.stdout.writelines(diff_lines)
    if not diff_lines[-1].endswith("\n"):
        sys.stdout.write("\n")
    return True


TEXT_EXTENSIONS = {
    ".md", ".txt", ".py", ".js", ".ts", ".sh", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".html", ".css", ".rst",
}


def is_text_file(p: Path) -> bool:
    if p.suffix.lower() in TEXT_EXTENSIONS:
        return True
    try:
        with p.open("rb") as f:
            chunk = f.read(8192)
        chunk.decode("utf-8")
        return b"\x00" not in chunk
    except Exception:
        return False


def scan_for_sensitive(text: str) -> list[tuple[int, str, str]]:
    findings: list[tuple[int, str, str]] = []
    for line_num, line in enumerate(text.splitlines(), 1):
        for pattern, reason in SENSITIVE_PATTERNS:
            for m in re.finditer(pattern, line, re.IGNORECASE):
                findings.append((line_num, m.group(0), reason))
    return findings


def scan_directory(root: Path) -> list[tuple[Path, int, str, str]]:
    """Scan every text file under root. Returns (relpath, line, match, reason)."""
    out: list[tuple[Path, int, str, str]] = []
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        if not p.is_file() or not is_text_file(p):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_num, match, reason in scan_for_sensitive(text):
            out.append((p.relative_to(root), line_num, match, reason))
    return out


def repo_status_porcelain(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def repo_unpushed_commits(repo: Path) -> int:
    """Return the number of commits ahead of origin/HEAD on the current branch."""
    try:
        subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "@{u}"],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return 0
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--count", "@{u}..HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(result.stdout.strip() or "0")


def mirror_directory(src: Path, dst: Path) -> list[tuple[str, Path]]:
    """Copy src→dst, overwriting changed files and deleting files removed in src.

    Returns a list of (op, relative_path) operations, where op is one of
    {"ADD", "UPDATE", "DELETE"}. Same-content files produce no op.
    """
    if not dst.exists():
        dst.mkdir(parents=True, exist_ok=True)

    ops: list[tuple[str, Path]] = []
    src_files = list_files_relative(src)
    dst_files = list_files_relative(dst)

    for rel in sorted(src_files):
        s = src / rel
        d = dst / rel
        if not d.exists():
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
            ops.append(("ADD", rel))
        else:
            if s.read_bytes() != d.read_bytes():
                shutil.copy2(s, d)
                ops.append(("UPDATE", rel))

    for rel in sorted(dst_files - src_files):
        (dst / rel).unlink()
        ops.append(("DELETE", rel))

    return ops


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync a Cowork-side skill to the public jacob-skills marketplace.",
    )
    parser.add_argument(
        "skill_name",
        help="Name of the skill to sync (e.g., calendar-search). Must exist in Cowork.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform the copy + commit + push. Default is dry-run.",
    )
    parser.add_argument(
        "--commit-message",
        default=None,
        help="Override the default commit message.",
    )
    args = parser.parse_args()

    skill_name: str = args.skill_name

    print(f"[sync-cowork-skill] target skill: {skill_name}")
    print(f"[sync-cowork-skill] mode: {'APPLY' if args.apply else 'dry-run'}")
    print()

    cowork_dir = find_cowork_skill_dir(skill_name)
    if cowork_dir is None:
        print(
            f"ERROR: no Cowork-side skill named '{skill_name}'.\n"
            f"  Searched: {COWORK_SKILLS_GLOB}/{skill_name}",
            file=sys.stderr,
        )
        return 10

    cowork_skill_md = cowork_dir / "SKILL.md"
    if not cowork_skill_md.exists():
        print(
            f"ERROR: Cowork folder for '{skill_name}' has no SKILL.md.\n"
            f"  At: {cowork_dir}",
            file=sys.stderr,
        )
        return 11

    github_dir = find_marketplace_skill_dir(skill_name)
    github_skill_md = github_dir / "SKILL.md"
    new_plugin = not github_skill_md.exists()
    plugin_json = MARKETPLACE_REPO / "plugins" / skill_name / ".claude-plugin" / "plugin.json"
    plugin_json_exists = plugin_json.exists()

    print(f"[sync-cowork-skill] Cowork source : {cowork_dir}")
    print(f"[sync-cowork-skill] Marketplace  : {github_dir}")
    if new_plugin:
        print(
            "[sync-cowork-skill] NOTE: marketplace has no copy of this skill yet — this would be a NEW plugin."
        )
    if not plugin_json_exists:
        print(
            "[sync-cowork-skill] NOTE: plugin.json is missing. Set it up manually before --apply."
        )
    print()

    cowork_text = cowork_skill_md.read_text(encoding="utf-8")
    github_text = github_skill_md.read_text(encoding="utf-8") if not new_plugin else ""

    print("=== SKILL.md diff (- = current GitHub, + = Cowork) ===")
    if new_plugin:
        print("(no GitHub copy yet — full Cowork content will be added)")
    else:
        had_diff = show_text_diff(
            cowork_text,
            github_text,
            str(cowork_skill_md),
            str(github_skill_md),
        )
        if not had_diff:
            print("(SKILL.md identical)")
    print()

    src_files = list_files_relative(cowork_dir)
    dst_files = list_files_relative(github_dir)
    add_files = sorted(src_files - dst_files)
    del_files = sorted(dst_files - src_files)
    print(f"=== File-level summary ===")
    print(f"  Cowork has    {len(src_files)} file(s)")
    print(f"  GitHub has    {len(dst_files)} file(s)")
    if add_files:
        print(f"  Would ADD     ({len(add_files)}):")
        for r in add_files:
            print(f"    + {r}")
    if del_files:
        print(f"  Would DELETE  ({len(del_files)}):")
        for r in del_files:
            print(f"    - {r}")
    print()

    findings = scan_directory(cowork_dir)
    print(
        f"=== Sensitive-content scan across all text files in Cowork skill folder "
        f"({len(findings)} hit{'s' if len(findings) != 1 else ''}) ==="
    )
    if findings:
        for relpath, line_num, match, reason in findings:
            print(f"  {relpath}:L{line_num}: {match!r}  [{reason}]")
    else:
        print("  (clean)")
    print()

    if not args.apply:
        print("[sync-cowork-skill] dry-run complete. Re-run with --apply to commit + push.")
        if findings:
            print(
                "[sync-cowork-skill] sensitive findings detected — review them before applying."
            )
        if not plugin_json_exists:
            print(
                "[sync-cowork-skill] plugin.json missing — create it manually before --apply will succeed."
            )
        return 0

    if not plugin_json_exists:
        print(
            "ERROR: plugin.json is missing. --apply refuses to scaffold a new plugin silently. "
            "Add plugins/{name}/.claude-plugin/plugin.json with a proper description first.".format(
                name=skill_name
            ),
            file=sys.stderr,
        )
        return 12

    if findings and os.environ.get("SYNC_OVERRIDE_SENSITIVE") != "1":
        print(
            "ERROR: refusing to --apply with sensitive findings present. "
            "If you have reviewed and they are acceptable, "
            "re-run with: SYNC_OVERRIDE_SENSITIVE=1 ... --apply",
            file=sys.stderr,
        )
        return 13

    dirty = repo_status_porcelain(MARKETPLACE_REPO)
    if dirty:
        print(
            "ERROR: marketplace repo has uncommitted changes. Resolve them before --apply.\n"
            f"{dirty}",
            file=sys.stderr,
        )
        return 14

    ahead = repo_unpushed_commits(MARKETPLACE_REPO)
    if ahead:
        print(
            f"WARNING: marketplace repo has {ahead} unpushed commit(s) on the current branch. "
            f"Sync will push them along with the new commit.",
            file=sys.stderr,
        )

    ops = mirror_directory(cowork_dir, github_dir)
    if not ops:
        print("[sync-cowork-skill] no file-level changes after mirror — nothing to commit.")
        return 0

    print("=== Mirror operations performed ===")
    for op, rel in ops:
        print(f"  {op:6}  {rel}")
    print()

    relpath = github_dir.relative_to(MARKETPLACE_REPO)
    subprocess.run(
        ["git", "-C", str(MARKETPLACE_REPO), "add", str(relpath)],
        check=True,
    )
    staged = subprocess.run(
        ["git", "-C", str(MARKETPLACE_REPO), "diff", "--cached", "--stat"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    print("=== Staged for commit ===")
    print(staged)

    commit_msg = args.commit_message or f"Sync {skill_name} from Cowork"
    subprocess.run(
        ["git", "-C", str(MARKETPLACE_REPO), "commit", "-m", commit_msg],
        check=True,
    )

    push = subprocess.run(
        ["git", "-C", str(MARKETPLACE_REPO), "push"],
        capture_output=True,
        text=True,
    )
    if push.returncode != 0:
        print("Commit succeeded, but push FAILED:", file=sys.stderr)
        print(push.stderr, file=sys.stderr)
        print(
            "Run 'cd ~/jacob-skills && git push' manually to retry. "
            "(Local commit is preserved.)",
            file=sys.stderr,
        )
        return 15

    print(push.stdout)
    print(f"[sync-cowork-skill] sync complete: {skill_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
