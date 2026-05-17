#!/usr/bin/env python3
"""
publish_snapshot.py — capture a redacted snapshot of a Claude Code environment.

v0.5 adds (on top of v0.4):
  - Plugin USER CONFIGS (~/.claude/<plugin-name>/*.{json,toml,yaml,yml,ini,conf}).
    Many plugins persist user-tweakable settings outside settings.json — e.g.
    claude-notifications-go/config.json holds your sound choices, suppression
    timers, webhook setup. Captured per-plugin so collaborators can see and
    optionally import them.

v0.4 added (on top of v0.3):
  - User skill BODIES (full SKILL.md + bundled files under ~/.claude/skills/<name>/)
    so personal skills actually transfer, not just their names.
  - External CLI inventory (best-effort `uv tool list` + `brew leaves`)
    so the diff can surface "their MCP server needs tool X — install it via Y"
    instead of silently importing a broken config.

v0.3 adds (on top of v0.2):
  - ~/.claude/plugins/installed_plugins.json (per-plugin version + git SHA)
  - Central reference files under ~/Claude/ (e.g. manuscript-rules.md)

v0.2 added (on top of v0.1):
  - ~/.claude/.mcp.json, settings.local.json, ccstatusline, keybindings, agents
  - command BODIES, not just descriptions
  - plugin-shipped skills (vs user skills)
  - machine_id

Usage:
  publish_snapshot.py --owner jacob --machine-id main --out snapshots/jacob_main.json
  publish_snapshot.py --owner jacob --out snapshots/jacob.json --dry-run

Designed to be safe to commit to a public repo. Redaction is conservative;
the output is a human-readable JSON file the user should eyeball before commit.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- Snapshot format version ------------------------------------------------

# Stamped into every snapshot as `snapshot_version`. Kept in lock-step with
# plugins/claude-env-sync/.claude-plugin/plugin.json's "version" field — bump
# both whenever the publisher gains or changes a capture. The comparer reads
# this back and warns if its own SCRIPT_VERSION is older.
SNAPSHOT_FORMAT_VERSION = "0.6.0"

# Cap per-file body capture at ~150KB to keep snapshots tractable; warn if exceeded.
SKILL_BUNDLE_FILE_MAX_BYTES = 150 * 1024
# Cap total per-skill bundle bytes; over this we skip the bundle but keep SKILL.md.
SKILL_BUNDLE_TOTAL_MAX_BYTES = 500 * 1024
# Cap CLI inventory output to ~16KB each.
CLI_INVENTORY_MAX_BYTES = 16 * 1024
# File extensions whose body we capture inside a skill bundle (text-only allowlist).
SKILL_BUNDLE_TEXT_EXTENSIONS = {
    ".md", ".sh", ".py", ".json", ".yaml", ".yml", ".txt", ".toml", ".cfg",
    ".html", ".css", ".js", ".ts", ".sql", ".tex", ".bib", ".csv", ".tsv",
    ".rb", ".pl", ".r",
}
# If a skill root has ANY of these marker files, treat it as a third-party skill
# whose body should NOT be synced (the receiving machine should install it
# the upstream way: git clone, npm install, etc.).
THIRD_PARTY_SKILL_MARKERS = {
    "LICENSE", "LICENSE.md", "LICENSE.txt",
    "package.json", "package-lock.json",
    "pyproject.toml", "uv.lock", "Cargo.toml",
    "CHANGELOG.md",
}
# Explicit per-skill opt-out: drop a file named this at the skill root to keep
# its body out of snapshots.
SKILL_BODY_OPTOUT_FILE = ".envsync-skip-body"


def detect_upstream(skill_dir: Path) -> dict:
    """Best-effort: return upstream metadata for a third-party skill.

    Always gathers .git/config URL + HEAD SHA if present — those pin the exact
    version the snapshot owner is running. Then if README documents a cleaner
    install path (Claude Code marketplace), surfaces that as the install_kind
    so env-compare can render `/plugin marketplace add ...` instead of
    `git clone ...`.

    Shape:
      {
        "url":               <upstream URL — github repo or similar>,
        "sha":               <git HEAD SHA if available, else null>,
        "install_kind":      "plugin-marketplace" | "git-clone",
        "install_marketplace_handle": "<owner>/<repo>"  (only when install_kind=plugin-marketplace),
      }

    Returns {} if nothing found — env-compare will then fall back to "unknown upstream".
    """
    out: dict = {}

    # (a) .git/config — most authoritative pin
    git_config = skill_dir / ".git" / "config"
    if git_config.exists():
        try:
            text = git_config.read_text(errors="replace")
            m = re.search(r"url\s*=\s*(\S+)", text)
            if m:
                out["url"] = m.group(1)
        except Exception:
            pass
        head_file = skill_dir / ".git" / "HEAD"
        if head_file.exists():
            try:
                head = head_file.read_text().strip()
                if head.startswith("ref: "):
                    ref_path = skill_dir / ".git" / head[5:]
                    if ref_path.exists():
                        out["sha"] = ref_path.read_text().strip()
                else:
                    out["sha"] = head
            except Exception:
                pass

    # (b) README scan for /plugin marketplace add <owner>/<repo> — preferred install path
    readme = skill_dir / "README.md"
    marketplace_handle = None
    if readme.exists():
        try:
            rtext = readme.read_text(errors="replace")
            m = re.search(r"/plugin\s+marketplace\s+add\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", rtext)
            if m:
                marketplace_handle = m.group(1)
        except Exception:
            pass

    # (c) Fallback URL via README git clone or pyproject.toml — only if .git/config didn't have one
    if "url" not in out and readme.exists():
        try:
            rtext = readme.read_text(errors="replace")
            m = re.search(r"git\s+clone\s+(https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?)", rtext)
            if m:
                out["url"] = m.group(1)
        except Exception:
            pass
    if "url" not in out:
        pp = skill_dir / "pyproject.toml"
        if pp.exists():
            try:
                ptext = pp.read_text(errors="replace")
                for key in ("Homepage", "Repository", "homepage", "repository"):
                    m = re.search(rf'^{key}\s*=\s*["\'](https?://\S+?)["\']', ptext, re.MULTILINE)
                    if m:
                        out["url"] = m.group(1)
                        break
            except Exception:
                pass

    if marketplace_handle:
        out["install_kind"] = "plugin-marketplace"
        out["install_marketplace_handle"] = marketplace_handle
        if "url" not in out:
            out["url"] = f"https://github.com/{marketplace_handle}"
    elif "url" in out:
        out["install_kind"] = "git-clone"

    return out

# --- Redaction patterns -----------------------------------------------------

SECRET_PATTERNS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"), "<REDACTED:anthropic-key>"),
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), "<REDACTED:sk-key>"),
    (re.compile(r"tvly-[A-Za-z0-9_-]{10,}"), "<REDACTED:tavily-key>"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}"), "<REDACTED:github-pat>"),
    (re.compile(r"\bgho_[A-Za-z0-9]{20,}"), "<REDACTED:github-oauth>"),
    (re.compile(r"\bghs_[A-Za-z0-9]{20,}"), "<REDACTED:github-server-token>"),
    (re.compile(r"\bghu_[A-Za-z0-9]{20,}"), "<REDACTED:github-user-token>"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<REDACTED:aws-access-key>"),
    (re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"), "Bearer <REDACTED>"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "<REDACTED:jwt>"),
    (re.compile(r"\bxox[bps]-[A-Za-z0-9-]{20,}"), "<REDACTED:slack-token>"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}"), "<REDACTED:google-api-key>"),
]

SECRET_KEY_SUBSTRINGS = [
    "api_key", "apikey",
    "token", "secret", "password", "passwd",
    "auth", "bearer",
    "private_key", "privatekey",
    "credential",
]

SECRET_KEY_ALLOWLIST = {
    "AUTH",
}

# ~/.claude.json contains a LOT of internal state. Whitelist what we publish.
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
    if not isinstance(s, str):
        return s
    home = str(Path.home())
    if home and home in s:
        stats["home_paths_normalized"] += s.count(home)
        s = s.replace(home, "${HOME}")
    return s


def redact_value(val, stats: dict, parent_key: str | None = None):
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


def read_mcp_servers(home: Path) -> dict:
    """
    Merge mcpServers from ~/.claude.json and ~/.claude/.mcp.json.
    Both can define MCP servers. .mcp.json wins on conflict (the newer convention).
    """
    big = read_json_safe(home / ".claude.json") or {}
    from_big = big.get("mcpServers", {}) or {}

    side = read_json_safe(home / ".claude" / ".mcp.json") or {}
    from_side = side.get("mcpServers", {}) or {}

    merged = dict(from_big)
    merged.update(from_side)
    return merged


def read_machine_id(home: Path, override: str | None) -> str | None:
    if override:
        return override
    f = home / ".claude" / "machine_id"
    if f.exists():
        try:
            v = f.read_text().strip()
            return v or None
        except Exception:
            return None
    return None


def get_claude_version() -> str | None:
    try:
        r = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            return r.stdout.strip().splitlines()[0] if r.stdout else None
    except Exception:
        pass
    return None


def list_skills(skills_dir: Path, source_label: str) -> list[dict]:
    """Walk a directory of skill folders. Each direct subdir = one skill."""
    if not skills_dir.is_dir():
        return []
    out = []
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            # Skip non-skill directories: .git/, bundle dirs without top-level SKILL.md, etc.
            continue
        description = ""
        if skill_md.exists():
            text = skill_md.read_text(errors="replace")
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
        out.append({
            "name": entry.name,
            "description": description[:300],
            "source": source_label,
        })
    return out


def list_plugin_shipped_skills(home: Path) -> list[dict]:
    """
    Walk ~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/skills/
    Each plugin can ship multiple skills.
    """
    cache = home / ".claude" / "plugins" / "cache"
    if not cache.is_dir():
        return []
    out = []
    for marketplace in sorted(cache.iterdir()):
        if not marketplace.is_dir():
            continue
        for plugin in sorted(marketplace.iterdir()):
            if not plugin.is_dir():
                continue
            # versions are usually content-hash dirs; pick all and dedupe by skill name later
            for version in sorted(plugin.iterdir()):
                if not version.is_dir():
                    continue
                skills_dir = version / "skills"
                if not skills_dir.is_dir():
                    continue
                src = f"plugin:{plugin.name}@{marketplace.name}"
                out.extend(list_skills(skills_dir, source_label=src))
    # Dedupe by (name, source) — multiple version-cache dirs can produce duplicates
    seen = set()
    deduped = []
    for s in out:
        key = (s["name"], s["source"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(s)
    return deduped


def list_commands(commands_dir: Path, stats: dict) -> list[dict]:
    """Walk ~/.claude/commands/. Each *.md = one slash command. Captures BODY too."""
    if not commands_dir.is_dir():
        return []
    out = []
    for f in sorted(commands_dir.iterdir()):
        if not f.is_file() or f.suffix.lower() != ".md":
            continue
        text = f.read_text(errors="replace")
        description = ""
        body_text = ""
        m = re.search(r"^---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL | re.MULTILINE)
        if m:
            fm = m.group(1)
            d = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
            if d:
                description = d.group(1).strip().strip('"').strip("'")
            body_text = text[m.end():].strip()
        else:
            body_text = text.strip()
        if not description:
            for line in body_text.splitlines():
                if line.strip() and not line.lstrip().startswith("#"):
                    description = line.strip()[:200]
                    break
        # Redact body before publishing
        body_redacted = redact_string(body_text, stats)
        body_redacted = normalize_home(body_redacted, stats)
        out.append({
            "name": f.stem,
            "description": description[:300],
            "body": body_redacted,
            "body_chars": len(body_text),
        })
    return out


def list_agents(agents_dir: Path) -> list[dict]:
    """Forward-compat: walk ~/.claude/agents/. Each *.md = one agent."""
    if not agents_dir.is_dir():
        return []
    out = []
    for f in sorted(agents_dir.iterdir()):
        if not f.is_file() or f.suffix.lower() != ".md":
            continue
        text = f.read_text(errors="replace")
        description = ""
        m = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL | re.MULTILINE)
        if m:
            fm = m.group(1)
            d = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
            if d:
                description = d.group(1).strip().strip('"').strip("'")
        out.append({"name": f.stem, "description": description[:300]})
    return out


def list_user_skill_bodies(skills_dir: Path, stats: dict) -> list[dict]:
    """
    For each user skill at ~/.claude/skills/<name>/, capture the full SKILL.md text
    plus bundled text files. Third-party skills (those with LICENSE / pyproject.toml /
    etc. at the root) keep their SKILL.md but their bundle is skipped — installing
    them on a new machine should follow the upstream path, not env-sync.

    Returns a list of dicts shaped like:
        {
          "name": "html-review-builder",
          "skill_md": "<full redacted text>",
          "bundle_status": "captured" | "skipped:<reason>",
          "files": [{"path": ..., "content": ..., "bytes": int}, ...],
          "skipped": [{"path": ..., "reason": ..., "bytes": int}, ...],
        }

    Plugin-shipped skills (under ~/.claude/plugins/cache/...) are NOT included here —
    they transfer via the marketplace.
    """
    if not skills_dir.is_dir():
        return []
    out = []
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        skill_md_path = entry / "SKILL.md"
        if not skill_md_path.exists():
            continue
        try:
            skill_md_text = skill_md_path.read_text(errors="replace")
        except Exception as e:
            print(f"WARN: could not read {skill_md_path}: {e}", file=sys.stderr)
            continue
        skill_md_redacted = redact_string(skill_md_text, stats)
        skill_md_redacted = normalize_home(skill_md_redacted, stats)

        # Decide whether to skip bundle capture entirely.
        bundle_status = "captured"
        if (entry / SKILL_BODY_OPTOUT_FILE).exists():
            bundle_status = "skipped:opted_out"
        else:
            for marker in THIRD_PARTY_SKILL_MARKERS:
                if (entry / marker).exists():
                    bundle_status = f"skipped:third_party_marker:{marker}"
                    break
            # Also check for a .git/ remote pointing at a non-owner repo (covers
            # skills cloned from someone else's GitHub without a LICENSE file).
            if bundle_status == "captured":
                git_config = entry / ".git" / "config"
                if git_config.exists():
                    try:
                        text = git_config.read_text(errors="replace")
                        m = re.search(r"url\s*=\s*(\S+)", text)
                        if m:
                            url = m.group(1).lower()
                            if "jacob" not in url and "xtzj" not in url:
                                bundle_status = f"skipped:third_party_git_remote:{m.group(1)}"
                    except Exception:
                        pass

        # If we skipped, surface structured upstream metadata so env-compare can
        # render an install command instead of telling the collaborator to ask
        # the snapshot owner to promote the skill.
        upstream: dict = {}
        if bundle_status.startswith("skipped:third_party_"):
            upstream = detect_upstream(entry)

        files: list[dict] = []
        skipped: list[dict] = []

        if bundle_status == "captured":
            total_bytes = 0
            oversize_total = False
            for fp in sorted(entry.rglob("*")):
                if not fp.is_file():
                    continue
                if fp == skill_md_path:
                    continue
                rel = fp.relative_to(entry).as_posix()
                ext = fp.suffix.lower()
                try:
                    size = fp.stat().st_size
                except OSError:
                    continue
                if size > SKILL_BUNDLE_FILE_MAX_BYTES:
                    skipped.append({"path": rel, "reason": "too_large", "bytes": size})
                    continue
                if ext not in SKILL_BUNDLE_TEXT_EXTENSIONS:
                    try:
                        sample = fp.read_bytes()[:4096]
                        sample.decode("utf-8")
                    except (UnicodeDecodeError, OSError):
                        skipped.append({"path": rel, "reason": "binary", "bytes": size})
                        continue
                try:
                    txt = fp.read_text(errors="replace")
                except Exception as e:
                    skipped.append({"path": rel, "reason": f"read_error:{e}"})
                    continue
                txt_redacted = redact_string(txt, stats)
                txt_redacted = normalize_home(txt_redacted, stats)
                files.append({"path": rel, "content": txt_redacted, "bytes": size})
                total_bytes += size
                if total_bytes > SKILL_BUNDLE_TOTAL_MAX_BYTES:
                    oversize_total = True
                    break
            if oversize_total:
                bundle_status = "skipped:total_size_exceeded"
                files = []
                skipped = []

        record = {
            "name": entry.name,
            "skill_md": skill_md_redacted,
            "bundle_status": bundle_status,
            "files": files,
            "skipped": skipped,
        }
        if upstream:
            record["upstream"] = upstream
        out.append(record)
    return out


def capture_external_cli_inventory() -> dict:
    """
    Best-effort capture of externally-installed command-line tools that MCP servers,
    hooks, and statuslines may shell out to.

    These don't live in any Claude config, so without capturing them the snapshot
    can be imported on a fresh machine and the MCP server fails silently because
    the binary isn't installed.

    Returns:
        {
          "uv_tool_list": "<stdout>" | None,
          "brew_leaves": "<stdout>" | None,
          "captured_at": "<iso utc>",
          "notes": [...],
        }
    """
    out: dict = {
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "uv_tool_list": None,
        "brew_leaves": None,
        "notes": [],
    }

    def run_safely(cmd: list[str], label: str) -> str | None:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except FileNotFoundError:
            out["notes"].append(f"{label}: {cmd[0]} not installed on this machine")
            return None
        except subprocess.TimeoutExpired:
            out["notes"].append(f"{label}: timed out after 10s")
            return None
        except Exception as e:
            out["notes"].append(f"{label}: error {e!r}")
            return None
        if r.returncode != 0:
            out["notes"].append(f"{label}: exit {r.returncode}; stderr={r.stderr.strip()[:200]}")
            return None
        txt = r.stdout or ""
        if len(txt.encode("utf-8")) > CLI_INVENTORY_MAX_BYTES:
            txt = txt[:CLI_INVENTORY_MAX_BYTES] + "\n# ...truncated\n"
        return txt.rstrip() + "\n" if txt else ""

    out["uv_tool_list"] = run_safely(["uv", "tool", "list"], "uv_tool_list")
    out["brew_leaves"] = run_safely(["brew", "leaves"], "brew_leaves")
    return out


# --- Plugin user configs ----------------------------------------------------

# Cap per-file capture for plugin user configs; these should be small.
PLUGIN_USER_CONFIG_MAX_BYTES = 64 * 1024
PLUGIN_USER_CONFIG_EXTS = {".json", ".toml", ".yaml", ".yml", ".ini", ".conf"}
# Filenames or suffixes that indicate runtime state rather than user config.
PLUGIN_USER_CONFIG_SKIP_NAMES = {"plugin-root", "state.json", "cache.json"}
PLUGIN_USER_CONFIG_SKIP_SUFFIXES = (".log", ".lock", ".pid", ".cache", ".tmp")


def capture_plugin_user_configs(home: Path, enabled_plugins: dict, stats: dict) -> dict:
    """
    For each enabled plugin, look for user-customizable config files at
    ~/.claude/<plugin-name>/ and capture small text-config files.

    Many plugins (e.g. claude-notifications-go) persist user-tweakable
    settings here rather than in settings.json — sounds, suppression
    timers, webhook configs, etc. Without capturing these, the snapshot
    reports the plugin as installed but the receiving side has no way
    to mirror the actual customization.

    Captures only top-level files (no recursion into subdirs) to avoid
    hauling in large state caches. Skips dotfiles, log files, lock files,
    and anything over PLUGIN_USER_CONFIG_MAX_BYTES.

    Returns:
        {plugin_name: {filename: redacted-content}, ...}
        Empty dict if no enabled plugins have a matching directory.
    """
    out: dict = {}
    if not enabled_plugins:
        return out
    for full_name in enabled_plugins.keys():
        # enabledPlugins keys look like "<plugin>@<marketplace>"; the
        # directory under ~/.claude/ uses just the plugin part.
        plugin_name = full_name.split("@", 1)[0]
        plugin_dir = home / ".claude" / plugin_name
        if not plugin_dir.is_dir():
            continue
        captured: dict = {}
        try:
            entries = sorted(plugin_dir.iterdir())
        except PermissionError:
            continue
        for f in entries:
            if not f.is_file():
                continue
            if f.name.startswith("."):
                continue
            if f.name in PLUGIN_USER_CONFIG_SKIP_NAMES:
                continue
            if any(f.name.endswith(suf) for suf in PLUGIN_USER_CONFIG_SKIP_SUFFIXES):
                continue
            if f.suffix.lower() not in PLUGIN_USER_CONFIG_EXTS:
                continue
            try:
                size = f.stat().st_size
            except OSError:
                continue
            if size > PLUGIN_USER_CONFIG_MAX_BYTES:
                captured[f.name] = {
                    "_skipped": f"file larger than {PLUGIN_USER_CONFIG_MAX_BYTES} bytes ({size} bytes)",
                }
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if f.suffix.lower() == ".json":
                try:
                    parsed = json.loads(text)
                    captured[f.name] = redact_value(parsed, stats)
                    continue
                except json.JSONDecodeError:
                    pass  # fall through to text-redact path
            captured[f.name] = redact_string(normalize_home(text, stats), stats)
        if captured:
            out[plugin_name] = captured
    return out


# --- Snapshot builder -------------------------------------------------------

def build_snapshot(owner: str, machine_id: str | None) -> tuple[dict, dict]:
    home = Path.home()
    stats = {
        "secret_patterns_matched": 0,
        "secret_keys_redacted": 0,
        "home_paths_normalized": 0,
    }

    settings_raw = read_json_safe(home / ".claude" / "settings.json") or {}
    settings_local_raw = read_json_safe(home / ".claude" / "settings.local.json") or {}
    mcp_raw = read_mcp_servers(home)
    claude_md_raw = read_text_safe(home / ".claude" / "CLAUDE.md") or ""
    manuscript_rules_raw = read_text_safe(home / "Claude" / "manuscript-rules.md") or ""
    keybindings_raw = read_json_safe(home / ".claude" / "keybindings.json") or {}
    statusline_raw = read_json_safe(home / ".config" / "ccstatusline" / "settings.json") or {}
    installed_plugins_raw = read_json_safe(home / ".claude" / "plugins" / "installed_plugins.json") or {}

    user_skills = list_skills(home / ".claude" / "skills", source_label="user")
    user_skill_bodies = list_user_skill_bodies(home / ".claude" / "skills", stats)
    plugin_skills = list_plugin_shipped_skills(home)
    commands = list_commands(home / ".claude" / "commands", stats)
    agents = list_agents(home / ".claude" / "agents")
    external_clis = capture_external_cli_inventory()
    plugin_user_configs = capture_plugin_user_configs(
        home, settings_raw.get("enabledPlugins") or {}, stats
    )

    # Redact everything. Commands' body field is already redacted in list_commands.
    settings = redact_value(settings_raw, stats)
    settings_local = redact_value(settings_local_raw, stats)
    mcp = redact_value(mcp_raw, stats)
    claude_md = redact_string(claude_md_raw, stats)
    claude_md = normalize_home(claude_md, stats)
    manuscript_rules = redact_string(manuscript_rules_raw, stats)
    manuscript_rules = normalize_home(manuscript_rules, stats)
    keybindings = redact_value(keybindings_raw, stats)
    statusline = redact_value(statusline_raw, stats)
    installed_plugins = redact_value(installed_plugins_raw, stats)
    user_skills = redact_value(user_skills, stats)
    plugin_skills = redact_value(plugin_skills, stats)
    agents = redact_value(agents, stats)

    snapshot = {
        "snapshot_version": SNAPSHOT_FORMAT_VERSION,
        "owner": owner,
        "machine_id": machine_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "platform": platform.system().lower(),
        "claude_version": get_claude_version(),
        "environment": {
            "settings_json": settings,
            "settings_local_json": settings_local,
            "mcp_servers": mcp,
            "global_claude_md": claude_md,
            "central_files": {
                "manuscript-rules.md": manuscript_rules,
            },
            "keybindings": keybindings,
            "statusline": statusline,
            "skills_user": user_skills,
            "skills_user_bodies": user_skill_bodies,
            "skills_plugin": plugin_skills,
            "commands": commands,
            "agents": agents,
            "installed_plugins": installed_plugins,
            "external_clis": external_clis,
            "plugin_user_configs": plugin_user_configs,
        },
        "source_paths": {
            "settings_json": "~/.claude/settings.json",
            "settings_local_json": "~/.claude/settings.local.json",
            "mcp_servers": "~/.claude.json mcpServers + ~/.claude/.mcp.json mcpServers (merged)",
            "global_claude_md": "~/.claude/CLAUDE.md",
            "central_files": "~/Claude/<filename>.md — lab-agnostic central rules files referenced by project-local CLAUDE.md via @-import; flat name→content map",
            "keybindings": "~/.claude/keybindings.json",
            "statusline": "~/.config/ccstatusline/settings.json",
            "skills_user": "~/.claude/skills/<name>/SKILL.md — names + descriptions (always captured)",
            "skills_user_bodies": "~/.claude/skills/<name>/ — full SKILL.md text + bundled text files; binary or oversized files listed under 'skipped'",
            "skills_plugin": "~/.claude/plugins/cache/<mp>/<plugin>/<ver>/skills/<name>/SKILL.md",
            "commands": "~/.claude/commands/<name>.md (frontmatter + body)",
            "agents": "~/.claude/agents/<name>.md",
            "installed_plugins": "~/.claude/plugins/installed_plugins.json — per-plugin version, gitCommitSha, install path (gives strict version pinning)",
            "external_clis": "subprocess `uv tool list` + `brew leaves` — externally-installed CLIs that MCP servers / hooks may shell out to (e.g. mcp-youtube-transcript). Best-effort; null if tool not installed.",
            "plugin_user_configs": "~/.claude/<plugin-name>/{*.json,*.toml,*.yaml,*.yml,*.ini,*.conf} — per-plugin user-customized config files that plugins persist outside of settings.json (e.g. claude-notifications-go/config.json: sounds, suppression timers, webhook setup). Top-level files only; <64KB each; redacted.",
            "machine_id": "~/.claude/machine_id (one-line file)",
            "claude_version": "subprocess `claude --version`",
        },
        "redactions_applied": stats,
        "notes": [
            "All known API-key shapes (sk-, tvly-, ghp_, AKIA, JWT, etc.) replaced with <REDACTED:type> tokens.",
            "Object keys whose name contains api_key/token/secret/password/auth had their string values redacted.",
            "Local home paths (/Users/<you>/) normalized to ${HOME} for portability.",
            "Slash-command bodies are captured (redacted). User-skill bodies are captured under 'skills_user_bodies' (v0.4+); plugin-shipped skills travel via the marketplace, not this snapshot.",
            "Plugin-shipped skills are listed with source='plugin:<plugin>@<marketplace>'; user-level with source='user'.",
            "external_clis is best-effort: if `uv` or `brew` isn't installed on this machine the field is null. Receiving machines without those binaries can't act on it; that's fine — the field just won't trigger a diff.",
            "Forward-compat fields (agents, keybindings) may be empty if those directories don't exist on this machine.",
            "plugin_user_configs (v0.5+): captures per-plugin user config under ~/.claude/<plugin-name>/. Top-level files only; binary, oversized, or non-config-suffix files are skipped. Comparer surfaces these so a collaborator can mirror your tuning.",
            "If you spot anything sensitive that wasn't caught, edit this file by hand before committing.",
        ],
    }
    return snapshot, stats


# --- CLI --------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--owner", required=True, help="Snapshot owner identifier (e.g. 'jacob')")
    ap.add_argument("--machine-id", default=None,
                    help="Per-machine identifier (e.g. 'main', 'jz1'). "
                         "If omitted, reads ~/.claude/machine_id.")
    ap.add_argument("--out", required=True, help="Output path for snapshot JSON")
    ap.add_argument("--dry-run", action="store_true", help="Print to stdout instead of writing")
    args = ap.parse_args()

    machine_id = read_machine_id(Path.home(), args.machine_id)
    snapshot, stats = build_snapshot(args.owner, machine_id)
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
        f"{stats['home_paths_normalized']} home-path normalizations. "
        f"machine_id={machine_id!r}.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
