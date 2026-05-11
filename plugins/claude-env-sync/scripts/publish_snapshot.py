#!/usr/bin/env python3
"""
publish_snapshot.py — capture a redacted snapshot of a Claude Code environment.

Reads ~/.claude/settings.json, ~/.claude.json's mcpServers block,
~/.claude/CLAUDE.md, and the names+descriptions of installed skills and
slash commands. Redacts API keys, OAuth tokens, and other secrets.
Writes a JSON snapshot to <marketplace>/snapshots/<owner>.json.

Usage:
  publish_snapshot.py --owner jacob --out ../../../snapshots/jacob.json
  publish_snapshot.py --owner jacob --out /path/to/snapshots/jacob.json --dry-run

Designed to be safe to commit to a public repo. The redaction is
conservative — when in doubt, redact. The output is also a human-readable
JSON file the user should eyeball before committing.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- Redaction patterns -----------------------------------------------------

# Compiled once. Each is a (pattern, replacement) pair.
SECRET_PATTERNS = [
    # Anthropic-style
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"), "<REDACTED:anthropic-key>"),
    # OpenAI-style
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), "<REDACTED:sk-key>"),
    # Tavily
    (re.compile(r"tvly-[A-Za-z0-9_-]{10,}"), "<REDACTED:tavily-key>"),
    # GitHub PATs
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}"), "<REDACTED:github-pat>"),
    (re.compile(r"\bgho_[A-Za-z0-9]{20,}"), "<REDACTED:github-oauth>"),
    (re.compile(r"\bghs_[A-Za-z0-9]{20,}"), "<REDACTED:github-server-token>"),
    (re.compile(r"\bghu_[A-Za-z0-9]{20,}"), "<REDACTED:github-user-token>"),
    # AWS
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<REDACTED:aws-access-key>"),
    # Bearer tokens in any string
    (re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"), "Bearer <REDACTED>"),
    # JWTs
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "<REDACTED:jwt>"),
    # Slack tokens
    (re.compile(r"\bxox[bps]-[A-Za-z0-9-]{20,}"), "<REDACTED:slack-token>"),
    # Google API keys
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}"), "<REDACTED:google-api-key>"),
]

# Object-key heuristic: if a key name contains any of these (case-insensitive),
# treat its string value as a secret.
SECRET_KEY_SUBSTRINGS = [
    "api_key", "apikey",
    "token", "secret", "password", "passwd",
    "auth", "bearer",
    "private_key", "privatekey",
    "credential",
]

# Keys to keep as-is even if their NAME matches secret heuristic
# (false-positive guard list).
SECRET_KEY_ALLOWLIST = {
    "AUTH",  # if a user actually names a key "AUTH" and means a non-secret, they can rename
    # leave empty for now
}

# ~/.claude.json contains a LOT of internal state we don't want to publish.
# Whitelist the only fields we WILL publish from it.
CLAUDE_JSON_PUBLISHED_KEYS = {"mcpServers"}


# --- Redaction helpers ------------------------------------------------------

def is_secret_key_name(key: str) -> bool:
    if not isinstance(key, str):
        return False
    if key in SECRET_KEY_ALLOWLIST:
        return False
    low = key.lower()
    return any(sub in low for sub in SECRET_KEY_SUBSTRINGS)


def redact_string(s: str, stats: dict) -> str:
    """Apply all secret-pattern regexes to a string."""
    if not isinstance(s, str):
        return s
    out = s
    for pat, repl in SECRET_PATTERNS:
        new = pat.sub(repl, out)
        if new != out:
            stats["secret_patterns_matched"] += len(pat.findall(out))
        out = new
    return out


def normalize_home(s: str, stats: dict) -> str:
    """Replace literal $HOME path with ${HOME} placeholder."""
    if not isinstance(s, str):
        return s
    home = str(Path.home())
    if home and home in s:
        stats["home_paths_normalized"] += s.count(home)
        s = s.replace(home, "${HOME}")
    return s


def redact_value(val, stats: dict, parent_key: str | None = None):
    """
    Recursively redact a JSON value.
    - If parent_key looks like a secret key, redact the entire value.
    - Otherwise, regex-redact strings and recurse into containers.
    """
    if parent_key is not None and is_secret_key_name(parent_key) and isinstance(val, str):
        stats["secret_keys_redacted"] += 1
        return f"<REDACTED:{parent_key}>"

    if isinstance(val, str):
        v = redact_string(val, stats)
        v = normalize_home(v, stats)
        return v

    if isinstance(val, dict):
        return {k: redact_value(v, stats, parent_key=k) for k, v in val.items()}

    if isinstance(val, list):
        return [redact_value(item, stats, parent_key=parent_key) for item in val]

    return val


# --- Source readers ---------------------------------------------------------

def read_json_safe(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception as e:
        print(f"WARN: could not read {path}: {e}", file=sys.stderr)
        return None


def read_text_safe(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text()
    except Exception as e:
        print(f"WARN: could not read {path}: {e}", file=sys.stderr)
        return None


def list_skills(skills_dir: Path) -> list[dict]:
    """Walk ~/.claude/skills/. Each direct subdir = one skill."""
    if not skills_dir.is_dir():
        return []
    out = []
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        description = ""
        if skill_md.exists():
            text = skill_md.read_text(errors="replace")
            # Pull description from YAML frontmatter if present
            m = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL | re.MULTILINE)
            if m:
                fm = m.group(1)
                d = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
                if d:
                    description = d.group(1).strip().strip('"').strip("'")
            if not description:
                # Fallback: first non-frontmatter, non-empty, non-heading line
                body = re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL).strip()
                for line in body.splitlines():
                    if line.strip() and not line.lstrip().startswith("#"):
                        description = line.strip()[:200]
                        break
        out.append({"name": entry.name, "description": description[:300]})
    return out


def list_commands(commands_dir: Path) -> list[dict]:
    """Walk ~/.claude/commands/. Each *.md = one slash command."""
    if not commands_dir.is_dir():
        return []
    out = []
    for f in sorted(commands_dir.iterdir()):
        if not f.is_file() or f.suffix != ".md":
            continue
        text = f.read_text(errors="replace")
        description = ""
        m = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL | re.MULTILINE)
        if m:
            fm = m.group(1)
            d = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
            if d:
                description = d.group(1).strip().strip('"').strip("'")
        if not description:
            body = re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL).strip()
            for line in body.splitlines():
                if line.strip() and not line.lstrip().startswith("#"):
                    description = line.strip()[:200]
                    break
        out.append({"name": f.stem, "description": description[:300]})
    return out


# --- Snapshot builder -------------------------------------------------------

def build_snapshot(owner: str) -> tuple[dict, dict]:
    home = Path.home()
    stats = {
        "secret_patterns_matched": 0,
        "secret_keys_redacted": 0,
        "home_paths_normalized": 0,
    }

    # --- settings.json ---
    settings_raw = read_json_safe(home / ".claude" / "settings.json") or {}

    # --- ~/.claude.json (only mcpServers) ---
    big_claude_json = read_json_safe(home / ".claude.json") or {}
    mcp_raw = big_claude_json.get("mcpServers", {})

    # --- global CLAUDE.md ---
    claude_md_raw = read_text_safe(home / ".claude" / "CLAUDE.md") or ""

    # --- skills + commands ---
    skills = list_skills(home / ".claude" / "skills")
    commands = list_commands(home / ".claude" / "commands")

    # --- redact ---
    settings = redact_value(settings_raw, stats)
    mcp = redact_value(mcp_raw, stats)
    claude_md = redact_string(claude_md_raw, stats)
    claude_md = normalize_home(claude_md, stats)
    skills = redact_value(skills, stats)
    commands = redact_value(commands, stats)

    snapshot = {
        "snapshot_version": "0.1.0",
        "owner": owner,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "platform": platform.system().lower(),
        "environment": {
            "settings_json": settings,
            "mcp_servers": mcp,
            "global_claude_md": claude_md,
            "skills": skills,
            "commands": commands,
        },
        "source_paths": {
            "settings_json": "~/.claude/settings.json",
            "mcp_servers": "~/.claude.json (mcpServers field only)",
            "global_claude_md": "~/.claude/CLAUDE.md",
            "skills": "~/.claude/skills/<name>/SKILL.md",
            "commands": "~/.claude/commands/<name>.md",
        },
        "redactions_applied": stats,
        "notes": [
            "All known API-key shapes (sk-, tvly-, ghp_, AKIA, JWT, etc.) replaced with <REDACTED:type> tokens.",
            "Object keys whose name contains api_key/token/secret/password/auth had their string values redacted.",
            "Local home paths (/Users/<you>/) normalized to ${HOME} for portability.",
            "Slash-command and skill listings include name + description only — full body not published.",
            "If you spot anything sensitive that wasn't caught, edit this file by hand before committing.",
        ],
    }
    return snapshot, stats


# --- CLI --------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--owner", required=True, help="Snapshot owner identifier (e.g. 'jacob')")
    ap.add_argument("--out", required=True, help="Output path for snapshot JSON")
    ap.add_argument("--dry-run", action="store_true", help="Print to stdout instead of writing")
    args = ap.parse_args()

    snapshot, stats = build_snapshot(args.owner)
    text = json.dumps(snapshot, indent=2, ensure_ascii=False)

    if args.dry_run:
        sys.stdout.write(text + "\n")
    else:
        out = Path(args.out).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n")
        print(f"Wrote snapshot: {out}")

    print(
        f"Redactions: {stats['secret_patterns_matched']} key-shape matches, "
        f"{stats['secret_keys_redacted']} key-name redactions, "
        f"{stats['home_paths_normalized']} home-path normalizations.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
