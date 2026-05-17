#!/usr/bin/env python3
"""sync-cowork-skill: one-way sync from a canonical skill source to the jacob-skills marketplace.

Source can be EITHER:
  - Cowork sessions (~/Library/.../skills-plugin/*/*/skills/<name>/), historically the default
  - Claude Code user-level skills (~/.claude/skills/<name>/), used for skills authored
    directly via Claude Code rather than Cowork

The script picks whichever single source exists. If both exist, it refuses and asks for
--source-override so the user makes the call explicitly.

SAFETY PROPERTIES:
1. The source file is READ-ONLY here. This script never writes back to ~/.claude/skills/
   or Cowork.
2. Default mode is dry-run. The user must re-invoke with --apply to mutate the marketplace
   repo.
3. Sensitive-content scan is mandatory. With findings, --apply refuses unless
   SYNC_OVERRIDE_SENSITIVE=1 is set in the environment.
4. Third-party-skill guard: refuses to sync any source folder that contains LICENSE,
   pyproject.toml, package.json, Cargo.toml, or a .git/ pointing at a non-jacob remote.
   Prevents accidentally republishing someone else's work.
5. The marketplace repo is required to be clean (no uncommitted changes) before --apply
   will proceed — prevents tangling sync with unrelated edits.
6. The skill folder is mirrored fully (new/changed files copy, deleted files removed in
   GitHub). plugin.json sits OUTSIDE the synced folder, so marketplace-only metadata is
   never overwritten by content-mirror.
7. On first sync of a new skill, --apply auto-scaffolds plugin.json (description pulled
   from the skill's frontmatter) AND auto-registers it in .claude-plugin/marketplace.json.
   The user sees both proposed additions in the dry-run output before confirming.
"""

from __future__ import annotations

import argparse
import difflib
import glob
import json
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
USER_SKILLS_DIR = HOME / ".claude" / "skills"
MARKETPLACE_REPO = HOME / "jacob-skills"
MARKETPLACE_JSON = MARKETPLACE_REPO / ".claude-plugin" / "marketplace.json"

# Files / dirs that indicate the source folder is a third-party skill (someone else's
# work). Refuse to sync these — the receiving machine should install them upstream.
THIRD_PARTY_MARKERS = {
    "LICENSE", "LICENSE.md", "LICENSE.txt",
    "package.json", "package-lock.json",
    "pyproject.toml", "uv.lock", "Cargo.toml",
    "CHANGELOG.md",
}
# Patterns inside the SOURCE folder we never want to copy into the published plugin.
SKIP_REL_NAMES = {".DS_Store", "_archive", "test-run.log", ".git"}

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
            f"[sync] WARNING: multiple Cowork copies of '{skill_name}' found:",
            file=sys.stderr,
        )
        for m in matches:
            print(f"  {m}", file=sys.stderr)
        matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        print(
            f"[sync] using most recently modified Cowork copy: {matches[0]}",
            file=sys.stderr,
        )
    return Path(matches[0])


def find_user_skill_dir(skill_name: str) -> Path | None:
    cand = USER_SKILLS_DIR / skill_name
    if cand.is_dir() and (cand / "SKILL.md").exists():
        return cand
    return None


def resolve_source(skill_name: str, override: str | None) -> tuple[Path, str]:
    """Return (source_dir, provenance_label). Raises SystemExit with a specific code on failure.

    override: None, "user-skills", "cowork", or an explicit path string.
    """
    if override:
        if override == "user-skills":
            d = find_user_skill_dir(skill_name)
            if not d:
                print(f"ERROR: --source-override user-skills but {USER_SKILLS_DIR / skill_name} not found.", file=sys.stderr)
                raise SystemExit(10)
            return d, "user-skills"
        if override == "cowork":
            d = find_cowork_skill_dir(skill_name)
            if not d:
                print(f"ERROR: --source-override cowork but no match for '{skill_name}' under {COWORK_SKILLS_GLOB}", file=sys.stderr)
                raise SystemExit(10)
            return d, "cowork"
        p = Path(override).expanduser()
        if not (p.is_dir() and (p / "SKILL.md").exists()):
            print(f"ERROR: --source-override path {p} is not a skill folder (must contain SKILL.md).", file=sys.stderr)
            raise SystemExit(10)
        return p, f"explicit:{p}"

    user_dir = find_user_skill_dir(skill_name)
    cowork_dir = find_cowork_skill_dir(skill_name)
    if user_dir and cowork_dir:
        print(
            f"ERROR: '{skill_name}' exists in BOTH source locations:\n"
            f"  user-skills: {user_dir}\n"
            f"  cowork:      {cowork_dir}\n"
            f"Pass --source-override user-skills|cowork to pick the canonical one explicitly.",
            file=sys.stderr,
        )
        raise SystemExit(16)
    if user_dir:
        return user_dir, "user-skills"
    if cowork_dir:
        return cowork_dir, "cowork"
    print(
        f"ERROR: no source skill named '{skill_name}'.\n"
        f"  Looked for: {USER_SKILLS_DIR / skill_name}\n"
        f"  And:        {COWORK_SKILLS_GLOB}/{skill_name}",
        file=sys.stderr,
    )
    raise SystemExit(10)


def check_third_party(source_dir: Path) -> list[str]:
    """Return a list of third-party-marker reasons. Empty list = clean."""
    reasons = []
    for m in THIRD_PARTY_MARKERS:
        if (source_dir / m).exists():
            reasons.append(f"{m} present at skill root")
    git_config = source_dir / ".git" / "config"
    if git_config.exists():
        try:
            text = git_config.read_text(errors="replace")
            m = re.search(r"url\s*=\s*(\S+)", text)
            if m and "jacob" not in m.group(1).lower() and "xtzj" not in m.group(1).lower():
                reasons.append(f".git/ remote points at non-jacob repo: {m.group(1)}")
        except Exception:
            pass
    return reasons


def find_marketplace_skill_dir(skill_name: str) -> Path:
    return MARKETPLACE_REPO / "plugins" / skill_name / "skills" / skill_name


def find_plugin_json(skill_name: str) -> Path:
    return MARKETPLACE_REPO / "plugins" / skill_name / ".claude-plugin" / "plugin.json"


def extract_frontmatter_description(skill_md: Path) -> str:
    text = skill_md.read_text(errors="replace")
    m = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL | re.MULTILINE)
    if not m:
        return ""
    fm = m.group(1)
    d = re.search(r"^description:\s*(.+(?:\n[ ]+.+)*)", fm, re.MULTILINE)
    if not d:
        return ""
    return d.group(1).strip().strip('"').strip("'")


def list_files_relative(root: Path) -> set[Path]:
    if not root.exists():
        return set()
    out = set()
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in SKIP_REL_NAMES for part in rel.parts):
            continue
        out.add(rel)
    return out


def show_text_diff(src_text: str, dst_text: str, src_label: str, dst_label: str) -> bool:
    diff_lines = list(
        difflib.unified_diff(
            dst_text.splitlines(keepends=True),
            src_text.splitlines(keepends=True),
            fromfile=f"GitHub: {dst_label}",
            tofile=f"Source: {src_label}",
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
    out: list[tuple[Path, int, str, str]] = []
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        if not p.is_file() or not is_text_file(p):
            continue
        rel = p.relative_to(root)
        if any(part in SKIP_REL_NAMES for part in rel.parts):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_num, match, reason in scan_for_sensitive(text):
            out.append((rel, line_num, match, reason))
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

    Returns a list of (op, relative_path) operations.
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


def marketplace_has_entry(skill_name: str) -> bool:
    if not MARKETPLACE_JSON.exists():
        return False
    try:
        data = json.loads(MARKETPLACE_JSON.read_text())
    except Exception:
        return False
    return any(p.get("name") == skill_name for p in data.get("plugins", []))


def register_in_marketplace(skill_name: str, description: str) -> bool:
    """Append a plugin entry. Returns True if file was modified, False if no-op."""
    if marketplace_has_entry(skill_name):
        return False
    data = json.loads(MARKETPLACE_JSON.read_text())
    data.setdefault("plugins", []).append({
        "name": skill_name,
        "source": f"./plugins/{skill_name}",
        "description": description or f"Skill: {skill_name}",
    })
    MARKETPLACE_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return True


def scaffold_plugin_json(skill_name: str, description: str) -> bool:
    """Write plugin.json. Returns True if written, False if already existed."""
    pj = find_plugin_json(skill_name)
    if pj.exists():
        return False
    pj.parent.mkdir(parents=True, exist_ok=True)
    pj.write_text(json.dumps({
        "name": skill_name,
        "description": description or f"Skill: {skill_name}",
        "author": {"name": "Jacob Zhang"},
    }, indent=2, ensure_ascii=False) + "\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync a skill from ~/.claude/skills/ or Cowork to the public jacob-skills marketplace.",
    )
    parser.add_argument(
        "skill_name",
        help="Name of the skill to sync (e.g., calendar-search).",
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
    parser.add_argument(
        "--source-override",
        default=None,
        help="Force source: 'user-skills', 'cowork', or an explicit path. "
             "Use when both locations exist or to override auto-detection.",
    )
    args = parser.parse_args()

    skill_name: str = args.skill_name

    print(f"[sync] target skill: {skill_name}")
    print(f"[sync] mode: {'APPLY' if args.apply else 'dry-run'}")

    source_dir, provenance = resolve_source(skill_name, args.source_override)
    print(f"[sync] source: {provenance} → {source_dir}")

    # Third-party guard: refuse to publish someone else's work.
    third_party_reasons = check_third_party(source_dir)
    if third_party_reasons:
        print(
            "ERROR: source skill looks like third-party work — refusing to publish:",
            file=sys.stderr,
        )
        for r in third_party_reasons:
            print(f"  - {r}", file=sys.stderr)
        print(
            "If you really want to publish this anyway, copy the content into a clean "
            "folder under ~/.claude/skills/<name>/ without LICENSE/pyproject/.git, then re-run.",
            file=sys.stderr,
        )
        return 17

    source_skill_md = source_dir / "SKILL.md"
    if not source_skill_md.exists():
        print(
            f"ERROR: source folder for '{skill_name}' has no SKILL.md.\n  At: {source_dir}",
            file=sys.stderr,
        )
        return 11

    github_dir = find_marketplace_skill_dir(skill_name)
    github_skill_md = github_dir / "SKILL.md"
    new_plugin = not github_skill_md.exists()
    plugin_json = find_plugin_json(skill_name)
    plugin_json_exists = plugin_json.exists()
    is_registered = marketplace_has_entry(skill_name)
    source_description = extract_frontmatter_description(source_skill_md)

    print(f"[sync] marketplace dst : {github_dir}")
    if new_plugin:
        print(
            "[sync] NOTE: marketplace has no copy of this skill yet — this would be a NEW plugin."
        )
    if not plugin_json_exists:
        print(
            f"[sync] NOTE: plugin.json missing — --apply will auto-scaffold from frontmatter "
            f"description ({len(source_description)} chars)."
        )
    if not is_registered:
        print(
            f"[sync] NOTE: .claude-plugin/marketplace.json has no entry for '{skill_name}' — "
            f"--apply will append one."
        )
    print()

    source_text = source_skill_md.read_text(encoding="utf-8")
    github_text = github_skill_md.read_text(encoding="utf-8") if not new_plugin else ""

    print("=== SKILL.md diff (- = current GitHub, + = source) ===")
    if new_plugin:
        print("(no GitHub copy yet — full source content will be added)")
    else:
        had_diff = show_text_diff(
            source_text,
            github_text,
            str(source_skill_md),
            str(github_skill_md),
        )
        if not had_diff:
            print("(SKILL.md identical)")
    print()

    src_files = list_files_relative(source_dir)
    dst_files = list_files_relative(github_dir)
    add_files = sorted(src_files - dst_files)
    del_files = sorted(dst_files - src_files)
    print(f"=== File-level summary ===")
    print(f"  Source has    {len(src_files)} file(s)")
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

    findings = scan_directory(source_dir)
    print(
        f"=== Sensitive-content scan across all text files in source skill folder "
        f"({len(findings)} hit{'s' if len(findings) != 1 else ''}) ==="
    )
    if findings:
        for relpath, line_num, match, reason in findings:
            print(f"  {relpath}:L{line_num}: {match!r}  [{reason}]")
    else:
        print("  (clean)")
    print()

    if not args.apply:
        print("[sync] dry-run complete. Re-run with --apply to commit + push.")
        if findings:
            print("[sync] sensitive findings detected — review them before applying.")
        return 0

    # --- APPLY mode ---

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

    scaffolded = scaffold_plugin_json(skill_name, source_description)
    if scaffolded:
        print(f"[sync] scaffolded {plugin_json}")
    registered = register_in_marketplace(skill_name, source_description)
    if registered:
        print(f"[sync] registered '{skill_name}' in {MARKETPLACE_JSON}")

    ops = mirror_directory(source_dir, github_dir)
    if not ops and not scaffolded and not registered:
        print("[sync] no file-level changes after mirror — nothing to commit.")
        return 0

    if ops:
        print("=== Mirror operations performed ===")
        for op, rel in ops:
            print(f"  {op:6}  {rel}")
        print()

    relpath = github_dir.relative_to(MARKETPLACE_REPO)
    paths_to_add = [str(relpath)]
    if scaffolded:
        paths_to_add.append(str(plugin_json.relative_to(MARKETPLACE_REPO)))
    if registered:
        paths_to_add.append(str(MARKETPLACE_JSON.relative_to(MARKETPLACE_REPO)))

    subprocess.run(
        ["git", "-C", str(MARKETPLACE_REPO), "add", *paths_to_add],
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

    commit_msg = args.commit_message or f"Sync {skill_name} from {provenance}"
    if scaffolded or registered:
        commit_msg += " (first-time publish)"
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
    print(f"[sync] sync complete: {skill_name} (from {provenance})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
