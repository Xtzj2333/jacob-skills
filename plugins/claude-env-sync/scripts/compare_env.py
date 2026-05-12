#!/usr/bin/env python3
"""
compare_env.py — diff a published environment snapshot against the local one.

v0.4 adds:
  - user skill BODY diff (SKILL.md text + bundled file list per skill)
  - external CLI inventory diff (`uv tool list`, `brew leaves`) so missing
    binaries that MCP servers depend on show up with an install hint.

v0.3 added installed-plugin version-pinning diff and central files
(~/Claude/manuscript-rules.md).

v0.2 added: settings.local.json, statusline, plugin-shipped skills, command
BODIES, agents, keybindings, and merged mcp_servers.

Backward-compatible: snapshots without a given field are treated as empty.

Usage:
  compare_env.py --snapshot snapshots/jacob_jz1.json
  compare_env.py --snapshot https://raw.githubusercontent.com/Xtzj2333/jacob-skills/main/snapshots/jacob_jz1.json
  compare_env.py --snapshot ... --out /tmp/diff.json
  compare_env.py --snapshot ... --html /tmp/diff.html
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Kept inline so this script is standalone.

# Script version — keep in sync with plugin.json. Surfaced to consumers so
# they can detect "snapshot is newer than my comparer" without grepping
# the script body for capabilities. Bumped together with plugin.json on every
# feature-affecting change.
SCRIPT_VERSION = "0.4.0"

CLAUDE_JSON_PUBLISHED_KEYS = {"mcpServers"}
SAFE_SETTINGS_KEYS = {
    "skillListingBudgetFraction", "permissions", "hooks", "statusLine",
    "enabledPlugins", "extraKnownMarketplaces", "effortLevel", "theme",
    "remoteControlAtStartup", "agentPushNotifEnabled",
    "skipAutoPermissionPrompt", "tui", "outputStyle", "language",
    "editorMode", "defaultShell", "attribution",
}

# --- Redaction (mirrors publish_snapshot.py so local reads compare apples-to-apples) ---
# Publisher writes snapshots with secrets replaced by tokens and ${HOME} normalized.
# Comparer must apply the same transforms to local reads, or self-compare will show
# every redacted value as a "difference" (it isn't — it's just the comparer reading raw).

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

SECRET_KEY_ALLOWLIST = {"AUTH"}


def _is_secret_key_name(key: str) -> bool:
    if not isinstance(key, str):
        return False
    if key in SECRET_KEY_ALLOWLIST:
        return False
    low = key.lower()
    return any(sub in low for sub in SECRET_KEY_SUBSTRINGS)


def _redact_string(s: str) -> str:
    if not isinstance(s, str):
        return s
    out = s
    for pat, repl in SECRET_PATTERNS:
        out = pat.sub(repl, out)
    return out


def _normalize_home(s: str) -> str:
    if not isinstance(s, str):
        return s
    home = str(Path.home())
    if home and home in s:
        s = s.replace(home, "${HOME}")
    return s


def redact_local(val, parent_key: str | None = None):
    """Apply the publisher's redaction + home-normalization to local reads.
    Without this, self-compare would show every secret-bearing field as 'different'."""
    if parent_key is not None and _is_secret_key_name(parent_key) and isinstance(val, str):
        return f"<REDACTED:{parent_key}>"
    if isinstance(val, str):
        return _normalize_home(_redact_string(val))
    if isinstance(val, dict):
        return {k: redact_local(v, parent_key=k) for k, v in val.items()}
    if isinstance(val, list):
        return [redact_local(item, parent_key=parent_key) for item in val]
    return val


def read_json_safe(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception as e:
        print(f"WARN: could not parse {path}: {e}", file=sys.stderr)
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
    big = read_json_safe(home / ".claude.json") or {}
    from_big = big.get("mcpServers", {}) or {}
    side = read_json_safe(home / ".claude" / ".mcp.json") or {}
    from_side = side.get("mcpServers", {}) or {}
    merged = dict(from_big)
    merged.update(from_side)
    return merged


def list_skills(skills_dir: Path, source_label: str) -> list[dict]:
    if not skills_dir.is_dir():
        return []
    out = []
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        if not (entry / "SKILL.md").exists():
            # Skip non-skill directories: .git/, bundle dirs without top-level SKILL.md, etc.
            continue
        out.append({"name": entry.name, "source": source_label})
    return out


def list_plugin_shipped_skills(home: Path) -> list[dict]:
    cache = home / ".claude" / "plugins" / "cache"
    if not cache.is_dir():
        return []
    out = []
    seen = set()
    for marketplace in sorted(cache.iterdir()):
        if not marketplace.is_dir():
            continue
        for plugin in sorted(marketplace.iterdir()):
            if not plugin.is_dir():
                continue
            for version in sorted(plugin.iterdir()):
                if not version.is_dir():
                    continue
                skills_dir = version / "skills"
                if not skills_dir.is_dir():
                    continue
                src = f"plugin:{plugin.name}@{marketplace.name}"
                for s in list_skills(skills_dir, source_label=src):
                    key = (s["name"], s["source"])
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(s)
    return out


def list_commands(commands_dir: Path) -> list[dict]:
    if not commands_dir.is_dir():
        return []
    out = []
    for f in sorted(commands_dir.iterdir()):
        if not f.is_file() or f.suffix.lower() != ".md":
            continue
        text = f.read_text(errors="replace")
        m = re.search(r"^---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL | re.MULTILINE)
        body_text = text[m.end():].strip() if m else text.strip()
        out.append({
            "name": f.stem,
            "body": body_text,
            "body_chars": len(body_text),
        })
    return out


# --- Skill body capture (mirrors publish_snapshot.py for self-compare) -----

SKILL_BUNDLE_FILE_MAX_BYTES = 150 * 1024
SKILL_BUNDLE_TOTAL_MAX_BYTES = 500 * 1024
SKILL_BUNDLE_TEXT_EXTENSIONS = {
    ".md", ".sh", ".py", ".json", ".yaml", ".yml", ".txt", ".toml", ".cfg",
    ".html", ".css", ".js", ".ts", ".sql", ".tex", ".bib", ".csv", ".tsv",
    ".rb", ".pl", ".r",
}
THIRD_PARTY_SKILL_MARKERS = {
    "LICENSE", "LICENSE.md", "LICENSE.txt",
    "package.json", "package-lock.json",
    "pyproject.toml", "uv.lock", "Cargo.toml",
    "CHANGELOG.md",
}
SKILL_BODY_OPTOUT_FILE = ".envsync-skip-body"


def list_user_skill_bodies(skills_dir: Path) -> list[dict]:
    """Mirror of publish_snapshot.list_user_skill_bodies — produces the same shape
    so theirs-vs-mine body diffing is apples-to-apples after redaction."""
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
        except Exception:
            continue
        skill_md_redacted = _normalize_home(_redact_string(skill_md_text))

        bundle_status = "captured"
        if (entry / SKILL_BODY_OPTOUT_FILE).exists():
            bundle_status = "skipped:opted_out"
        else:
            for marker in THIRD_PARTY_SKILL_MARKERS:
                if (entry / marker).exists():
                    bundle_status = f"skipped:third_party_marker:{marker}"
                    break

        files: list[dict] = []
        skipped: list[dict] = []
        if bundle_status == "captured":
            total_bytes = 0
            oversize_total = False
            for fp in sorted(entry.rglob("*")):
                if not fp.is_file() or fp == skill_md_path:
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
                        fp.read_bytes()[:4096].decode("utf-8")
                    except (UnicodeDecodeError, OSError):
                        skipped.append({"path": rel, "reason": "binary", "bytes": size})
                        continue
                try:
                    txt = fp.read_text(errors="replace")
                except Exception as e:
                    skipped.append({"path": rel, "reason": f"read_error:{e}"})
                    continue
                txt_redacted = _normalize_home(_redact_string(txt))
                files.append({"path": rel, "content": txt_redacted, "bytes": size})
                total_bytes += size
                if total_bytes > SKILL_BUNDLE_TOTAL_MAX_BYTES:
                    oversize_total = True
                    break
            if oversize_total:
                bundle_status = "skipped:total_size_exceeded"
                files = []
                skipped = []

        out.append({
            "name": entry.name,
            "skill_md": skill_md_redacted,
            "bundle_status": bundle_status,
            "files": files,
            "skipped": skipped,
        })
    return out


def capture_external_cli_inventory() -> dict:
    """Mirror of publish_snapshot.capture_external_cli_inventory — same shape so
    self-compare matches."""
    import subprocess as _sp
    CLI_INVENTORY_MAX_BYTES = 16 * 1024
    out: dict = {
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "uv_tool_list": None,
        "brew_leaves": None,
        "notes": [],
    }

    def run_safely(cmd, label):
        try:
            r = _sp.run(cmd, capture_output=True, text=True, timeout=10)
        except FileNotFoundError:
            out["notes"].append(f"{label}: {cmd[0]} not installed on this machine")
            return None
        except _sp.TimeoutExpired:
            out["notes"].append(f"{label}: timed out after 10s")
            return None
        except Exception as e:
            out["notes"].append(f"{label}: error {e!r}")
            return None
        if r.returncode != 0:
            out["notes"].append(f"{label}: exit {r.returncode}")
            return None
        txt = r.stdout or ""
        if len(txt.encode("utf-8")) > CLI_INVENTORY_MAX_BYTES:
            txt = txt[:CLI_INVENTORY_MAX_BYTES] + "\n# ...truncated\n"
        return (txt.rstrip() + "\n") if txt else ""

    out["uv_tool_list"] = run_safely(["uv", "tool", "list"], "uv_tool_list")
    out["brew_leaves"] = run_safely(["brew", "leaves"], "brew_leaves")
    return out


def list_agents(agents_dir: Path) -> list[dict]:
    if not agents_dir.is_dir():
        return []
    out = []
    for f in sorted(agents_dir.iterdir()):
        if not f.is_file() or f.suffix.lower() != ".md":
            continue
        out.append({"name": f.stem})
    return out


def _parse_version_tuple(v: str) -> tuple:
    """Parse 'a.b.c' → (a, b, c). Unparseable segments become 0."""
    out = []
    for part in (v or "").split("."):
        try:
            out.append(int(part))
        except (ValueError, TypeError):
            out.append(0)
    while len(out) < 3:
        out.append(0)
    return tuple(out[:3])


def check_version_skew(snapshot: dict) -> dict | None:
    """If the snapshot was produced by a publisher newer than this comparer,
    new fields may be present that we don't render. Surface that as a
    structured warning rather than silently dropping data."""
    snap_v = snapshot.get("snapshot_version", "0.1.0")
    if _parse_version_tuple(snap_v) > _parse_version_tuple(SCRIPT_VERSION):
        return {
            "kind": "snapshot_newer_than_comparer",
            "snapshot_version": snap_v,
            "comparer_version": SCRIPT_VERSION,
            "message": (
                f"Snapshot was produced by env-sync v{snap_v}, but this comparer "
                f"is v{SCRIPT_VERSION}. New sections in the snapshot will be ignored. "
                f"Upgrade the env-sync plugin: /plugin marketplace update jacob-skills "
                f"then /plugin install claude-env-sync@jacob-skills."
            ),
        }
    return None


def fetch_snapshot(src: str) -> dict:
    if src.startswith(("http://", "https://")):
        with urllib.request.urlopen(src, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    return json.loads(Path(src).expanduser().read_text())


def read_local_env() -> dict:
    home = Path.home()
    settings = read_json_safe(home / ".claude" / "settings.json") or {}
    settings_local = read_json_safe(home / ".claude" / "settings.local.json") or {}
    keybindings = read_json_safe(home / ".claude" / "keybindings.json") or {}
    statusline = read_json_safe(home / ".config" / "ccstatusline" / "settings.json") or {}
    raw = {
        "settings_json": settings,
        "settings_local_json": settings_local,
        "mcp_servers": read_mcp_servers(home),
        "global_claude_md": read_text_safe(home / ".claude" / "CLAUDE.md") or "",
        "central_files": {
            "manuscript-rules.md": read_text_safe(home / "Claude" / "manuscript-rules.md") or "",
        },
        "keybindings": keybindings,
        "statusline": statusline,
        "skills_user": list_skills(home / ".claude" / "skills", source_label="user"),
        "skills_user_bodies": list_user_skill_bodies(home / ".claude" / "skills"),
        "skills_plugin": list_plugin_shipped_skills(home),
        "commands": list_commands(home / ".claude" / "commands"),
        "agents": list_agents(home / ".claude" / "agents"),
        "installed_plugins": read_json_safe(home / ".claude" / "plugins" / "installed_plugins.json") or {},
        "external_clis": capture_external_cli_inventory(),
    }
    # Apply publisher's redaction + home-normalization so self-compare is clean.
    # (Without this, every redacted secret and every absolute path shows as a "diff".)
    return redact_local(raw)


# --- Diff helpers -----------------------------------------------------------

def diff_dict_by_key(theirs: dict, mine: dict) -> dict:
    only_theirs = {k: theirs[k] for k in theirs.keys() - mine.keys()}
    only_mine = {k: mine[k] for k in mine.keys() - theirs.keys()}
    both_diff = {}
    both_same = []
    for k in theirs.keys() & mine.keys():
        if theirs[k] == mine[k]:
            both_same.append(k)
        else:
            both_diff[k] = {"theirs": theirs[k], "mine": mine[k]}
    return {
        "only_theirs": only_theirs,
        "only_mine": only_mine,
        "both_different": both_diff,
        "both_same": sorted(both_same),
    }


def diff_named_lists(theirs: list[dict], mine: list[dict]) -> dict:
    t = {x["name"] for x in theirs if "name" in x}
    m = {x["name"] for x in mine if "name" in x}
    return {
        "only_theirs": sorted(t - m),
        "only_mine": sorted(m - t),
        "both": sorted(t & m),
    }


def diff_skills_with_source(theirs: list[dict], mine: list[dict]) -> dict:
    """Diff skills where each entry has (name, source). Items keyed by (name, source)."""
    def _key(x): return (x.get("name", ""), x.get("source", "user"))
    t = {_key(x): x for x in theirs}
    m = {_key(x): x for x in mine}
    return {
        "only_theirs": [t[k] for k in sorted(t.keys() - m.keys())],
        "only_mine": [m[k] for k in sorted(m.keys() - t.keys())],
        "both": [{"name": k[0], "source": k[1]} for k in sorted(t.keys() & m.keys())],
    }


def diff_commands_with_body(theirs: list[dict], mine: list[dict]) -> dict:
    """Diff commands by name; also flag body divergence for commands present on both sides."""
    t = {x["name"]: x for x in theirs if "name" in x}
    m = {x["name"]: x for x in mine if "name" in x}
    only_theirs = sorted(t.keys() - m.keys())
    only_mine = sorted(m.keys() - t.keys())
    both_same_body = []
    both_diff_body = []
    for name in sorted(t.keys() & m.keys()):
        tb = t[name].get("body", "")
        mb = m[name].get("body", "")
        if tb == mb:
            both_same_body.append(name)
        else:
            both_diff_body.append({
                "name": name,
                "theirs_body": tb,
                "mine_body": mb,
                "theirs_chars": len(tb),
                "mine_chars": len(mb),
            })
    return {
        "only_theirs": only_theirs,
        "only_mine": only_mine,
        "both_same_body": both_same_body,
        "both_diff_body": both_diff_body,
    }


def diff_hooks(theirs_hooks: dict, mine_hooks: dict) -> dict:
    out = {}
    for event in sorted(set(theirs_hooks.keys()) | set(mine_hooks.keys())):
        t = theirs_hooks.get(event, [])
        m = mine_hooks.get(event, [])
        if t == m:
            continue
        out[event] = {
            "theirs": t,
            "mine": m,
            "theirs_handler_count": len(t) if isinstance(t, list) else None,
            "mine_handler_count": len(m) if isinstance(m, list) else None,
        }
    return out


def diff_settings_top_level(theirs: dict, mine: dict) -> dict:
    out = {}
    keys = (set(theirs.keys()) | set(mine.keys())) & SAFE_SETTINGS_KEYS
    keys.discard("hooks")
    for k in sorted(keys):
        t = theirs.get(k, "<not set>")
        m = mine.get(k, "<not set>")
        if t != m:
            out[k] = {"theirs": t, "mine": m}
    return out


def diff_blob(theirs: dict, mine: dict) -> dict | None:
    """For settings.local, statusline, keybindings — small JSON blobs we just compare wholesale."""
    if theirs == mine:
        return None
    return {"theirs": theirs, "mine": mine}


def _summarize_plugin_install(plugin_value) -> dict:
    """Reduce an installed_plugins.json entry to (version, gitCommitSha, scope).
    The file stores a LIST of install records per plugin (to support multiple scopes /
    historical installs). We summarize the first record — current versions of Claude Code
    appear to only ever populate one — and surface a count so a future multi-record install
    doesn't silently hide a mismatch."""
    if not isinstance(plugin_value, list) or not plugin_value:
        return {"present": False}
    first = plugin_value[0]
    return {
        "present": True,
        "version": first.get("version"),
        "gitCommitSha": first.get("gitCommitSha"),
        "scope": first.get("scope"),
        "install_record_count": len(plugin_value),
    }


def diff_installed_plugins(theirs: dict, mine: dict) -> dict:
    """Diff per plugin-name key. Each plugin is summarized to (version, gitCommitSha),
    and we report: only-theirs, only-mine, version/sha mismatches, and identical installs."""
    t_plugins = theirs.get("plugins", {}) if isinstance(theirs, dict) else {}
    m_plugins = mine.get("plugins", {}) if isinstance(mine, dict) else {}
    only_theirs = []
    only_mine = []
    version_diff = []
    sha_only_diff = []
    same = []
    for name in sorted(set(t_plugins.keys()) | set(m_plugins.keys())):
        t = _summarize_plugin_install(t_plugins.get(name))
        m = _summarize_plugin_install(m_plugins.get(name))
        if t["present"] and not m["present"]:
            only_theirs.append({"name": name, **t})
        elif m["present"] and not t["present"]:
            only_mine.append({"name": name, **m})
        elif t["present"] and m["present"]:
            if t["version"] != m["version"]:
                version_diff.append({
                    "name": name,
                    "theirs_version": t["version"], "mine_version": m["version"],
                    "theirs_sha": t["gitCommitSha"], "mine_sha": m["gitCommitSha"],
                })
            elif t["gitCommitSha"] != m["gitCommitSha"]:
                sha_only_diff.append({
                    "name": name, "version": t["version"],
                    "theirs_sha": t["gitCommitSha"], "mine_sha": m["gitCommitSha"],
                })
            else:
                same.append({"name": name, "version": t["version"]})
    return {
        "only_theirs": only_theirs,
        "only_mine": only_mine,
        "version_diff": version_diff,
        "sha_only_diff": sha_only_diff,
        "same": same,
    }


def diff_central_files(theirs: dict, mine: dict) -> dict:
    """Diff each named central file by length + identity. Body text not included (would bloat the diff)."""
    out = {}
    for k in sorted(set(theirs.keys()) | set(mine.keys())):
        t = theirs.get(k, "")
        m = mine.get(k, "")
        out[k] = {
            "theirs_length_chars": len(t),
            "mine_length_chars": len(m),
            "identical": t == m,
            "theirs_present": k in theirs,
            "mine_present": k in mine,
        }
    return out


def diff_skill_bodies(theirs: list[dict], mine: list[dict]) -> dict:
    """Diff user skill BODIES (added in v0.4).
    Pairs by skill name and reports SKILL.md identity + bundle-file divergence."""
    t = {x["name"]: x for x in (theirs or []) if "name" in x}
    m = {x["name"]: x for x in (mine or []) if "name" in x}
    only_theirs = []
    only_mine = []
    both_same = []
    both_diff = []
    for name in sorted(set(t.keys()) | set(m.keys())):
        if name in t and name not in m:
            only_theirs.append({
                "name": name,
                "bundle_status": t[name].get("bundle_status"),
                "skill_md_chars": len(t[name].get("skill_md", "")),
                "bundle_files": len(t[name].get("files", [])),
            })
        elif name in m and name not in t:
            only_mine.append({
                "name": name,
                "bundle_status": m[name].get("bundle_status"),
                "skill_md_chars": len(m[name].get("skill_md", "")),
                "bundle_files": len(m[name].get("files", [])),
            })
        else:
            tt, mm = t[name], m[name]
            t_md = tt.get("skill_md", "")
            m_md = mm.get("skill_md", "")
            t_files = {f["path"]: f for f in tt.get("files", [])}
            m_files = {f["path"]: f for f in mm.get("files", [])}
            files_only_theirs = sorted(set(t_files) - set(m_files))
            files_only_mine = sorted(set(m_files) - set(t_files))
            files_both_diff = sorted(
                p for p in set(t_files) & set(m_files)
                if t_files[p].get("content") != m_files[p].get("content")
            )
            md_same = (t_md == m_md)
            if md_same and not (files_only_theirs or files_only_mine or files_both_diff):
                both_same.append(name)
            else:
                both_diff.append({
                    "name": name,
                    "skill_md_same": md_same,
                    "theirs_skill_md_chars": len(t_md),
                    "mine_skill_md_chars": len(m_md),
                    "theirs_skill_md": t_md if not md_same else None,
                    "mine_skill_md": m_md if not md_same else None,
                    "files_only_theirs": files_only_theirs,
                    "files_only_mine": files_only_mine,
                    "files_both_diff": files_both_diff,
                    "theirs_bundle_status": tt.get("bundle_status"),
                    "mine_bundle_status": mm.get("bundle_status"),
                })
    return {
        "only_theirs": only_theirs,
        "only_mine": only_mine,
        "both_same": both_same,
        "both_diff": both_diff,
    }


def _parse_uv_tool_list(txt: str | None) -> set[str]:
    """Parse `uv tool list` output into a set of tool names.
    Lines look like 'mcp-youtube-transcript v0.3.5' followed by indented entry points."""
    if not txt:
        return set()
    names = set()
    for line in txt.splitlines():
        if not line or line[0] in " \t-":
            continue
        # First whitespace-separated token is the tool name.
        first = line.strip().split(None, 1)[0]
        if first:
            names.add(first)
    return names


def _parse_brew_leaves(txt: str | None) -> set[str]:
    """Parse `brew leaves` output (one formula per line, possibly tap-qualified)."""
    if not txt:
        return set()
    return {ln.strip() for ln in txt.splitlines() if ln.strip()}


def diff_external_clis(theirs: dict, mine: dict) -> dict:
    """Diff external CLI inventories. Surfaces tools present on theirs but not
    on mine — these are likely things MCP servers / hooks depend on that the
    receiving machine needs to install separately."""
    t = theirs or {}
    m = mine or {}
    t_uv = _parse_uv_tool_list(t.get("uv_tool_list"))
    m_uv = _parse_uv_tool_list(m.get("uv_tool_list"))
    t_brew = _parse_brew_leaves(t.get("brew_leaves"))
    m_brew = _parse_brew_leaves(m.get("brew_leaves"))
    return {
        "uv_only_theirs": sorted(t_uv - m_uv),
        "uv_only_mine": sorted(m_uv - t_uv),
        "uv_both": sorted(t_uv & m_uv),
        "brew_only_theirs": sorted(t_brew - m_brew),
        "brew_only_mine": sorted(m_brew - t_brew),
        "brew_both": sorted(t_brew & m_brew),
        "theirs_captured": t.get("uv_tool_list") is not None or t.get("brew_leaves") is not None,
        "mine_captured": m.get("uv_tool_list") is not None or m.get("brew_leaves") is not None,
        "theirs_notes": t.get("notes", []),
        "mine_notes": m.get("notes", []),
    }


def build_diff(snapshot: dict, local: dict) -> dict:
    env_t = snapshot.get("environment", {})
    env_m = local

    diff = {
        "compared_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "snapshot_owner": snapshot.get("owner", "<unknown>"),
        "snapshot_machine_id": snapshot.get("machine_id"),
        "snapshot_format_version": snapshot.get("snapshot_version", "0.1.0"),
        "snapshot_generated_at": snapshot.get("generated_at"),
        "snapshot_claude_version": snapshot.get("claude_version"),
        "summary_counts": {},
        "hooks": diff_hooks(
            env_t.get("settings_json", {}).get("hooks", {}),
            env_m.get("settings_json", {}).get("hooks", {}),
        ),
        "mcp_servers": diff_dict_by_key(
            env_t.get("mcp_servers", {}),
            env_m.get("mcp_servers", {}),
        ),
        "settings": diff_settings_top_level(
            env_t.get("settings_json", {}),
            env_m.get("settings_json", {}),
        ),
        "settings_local": diff_blob(
            env_t.get("settings_local_json", {}),
            env_m.get("settings_local_json", {}),
        ),
        "statusline": diff_blob(
            env_t.get("statusline", {}),
            env_m.get("statusline", {}),
        ),
        "keybindings": diff_blob(
            env_t.get("keybindings", {}),
            env_m.get("keybindings", {}),
        ),
        "skills_user": diff_named_lists(
            env_t.get("skills_user", env_t.get("skills", [])),  # back-compat: v0.1 used "skills"
            env_m.get("skills_user", []),
        ),
        "skills_plugin": diff_skills_with_source(
            env_t.get("skills_plugin", []),
            env_m.get("skills_plugin", []),
        ),
        "commands": diff_commands_with_body(
            env_t.get("commands", []),
            env_m.get("commands", []),
        ),
        "agents": diff_named_lists(
            env_t.get("agents", []),
            env_m.get("agents", []),
        ),
        "global_claude_md": {
            "theirs_length_chars": len(env_t.get("global_claude_md", "") or ""),
            "mine_length_chars": len(env_m.get("global_claude_md", "") or ""),
            "identical": env_t.get("global_claude_md", "") == env_m.get("global_claude_md", ""),
        },
        "central_files": diff_central_files(
            env_t.get("central_files", {}) or {},
            env_m.get("central_files", {}) or {},
        ),
        "installed_plugins": diff_installed_plugins(
            env_t.get("installed_plugins", {}) or {},
            env_m.get("installed_plugins", {}) or {},
        ),
        "skills_user_bodies": diff_skill_bodies(
            env_t.get("skills_user_bodies", []),
            env_m.get("skills_user_bodies", []),
        ),
        "external_clis": diff_external_clis(
            env_t.get("external_clis", {}) or {},
            env_m.get("external_clis", {}) or {},
        ),
    }

    s = diff["summary_counts"]
    s["snapshot_format"] = diff["snapshot_format_version"]
    s["hook_events_differing"] = len(diff["hooks"])
    s["mcp_servers_only_in_theirs"] = len(diff["mcp_servers"]["only_theirs"])
    s["mcp_servers_only_in_mine"] = len(diff["mcp_servers"]["only_mine"])
    s["mcp_servers_both_different"] = len(diff["mcp_servers"]["both_different"])
    s["settings_keys_differing"] = len(diff["settings"])
    s["settings_local_differs"] = diff["settings_local"] is not None
    s["statusline_differs"] = diff["statusline"] is not None
    s["keybindings_differs"] = diff["keybindings"] is not None
    s["user_skills_only_in_theirs"] = len(diff["skills_user"]["only_theirs"])
    s["user_skills_only_in_mine"] = len(diff["skills_user"]["only_mine"])
    s["plugin_skills_only_in_theirs"] = len(diff["skills_plugin"]["only_theirs"])
    s["plugin_skills_only_in_mine"] = len(diff["skills_plugin"]["only_mine"])
    s["commands_only_in_theirs"] = len(diff["commands"]["only_theirs"])
    s["commands_only_in_mine"] = len(diff["commands"]["only_mine"])
    s["commands_body_diverged"] = len(diff["commands"]["both_diff_body"])
    s["agents_only_in_theirs"] = len(diff["agents"]["only_theirs"])
    s["agents_only_in_mine"] = len(diff["agents"]["only_mine"])
    s["claude_md_identical"] = diff["global_claude_md"]["identical"]
    s["central_files_differing"] = sum(
        1 for v in diff["central_files"].values() if not v["identical"]
    )
    ip = diff["installed_plugins"]
    s["plugins_only_in_theirs"] = len(ip["only_theirs"])
    s["plugins_only_in_mine"] = len(ip["only_mine"])
    s["plugins_version_diff"] = len(ip["version_diff"])
    s["plugins_sha_only_diff"] = len(ip["sha_only_diff"])
    s["plugins_same"] = len(ip["same"])
    sb = diff["skills_user_bodies"]
    s["skill_bodies_only_in_theirs"] = len(sb["only_theirs"])
    s["skill_bodies_only_in_mine"] = len(sb["only_mine"])
    s["skill_bodies_diverged"] = len(sb["both_diff"])
    s["skill_bodies_same"] = len(sb["both_same"])
    ec = diff["external_clis"]
    s["uv_tools_only_in_theirs"] = len(ec["uv_only_theirs"])
    s["uv_tools_only_in_mine"] = len(ec["uv_only_mine"])
    s["brew_only_in_theirs"] = len(ec["brew_only_theirs"])
    s["brew_only_in_mine"] = len(ec["brew_only_mine"])
    return diff


# --- HTML renderer ----------------------------------------------------------

HTML_HEAD = """<!doctype html>
<html><head><meta charset="utf-8"><title>Environment diff</title>
<style>
body {font: 15px/1.5 -apple-system,system-ui,sans-serif;max-width:920px;margin:24px auto;padding:0 18px;color:#1a1a1a;}
h1 {font-size: 22px; border-bottom: 2px solid #1a1a1a; padding-bottom: 8px;}
h2 {font-size: 18px; margin-top: 28px; border-bottom: 1px solid #d8d8d8; padding-bottom: 4px;}
h3 {font-size: 15px; margin-top: 16px; color: #335c81;}
.summary {background:#f4f4f1;padding:10px 14px;border-radius:4px;font-size:14px;}
.summary li {margin: 2px 0;}
.theirs-only {background:#ecf5ee;border-left:4px solid #2e7d32;padding:8px 12px;margin:8px 0;border-radius:0 4px 4px 0;}
.mine-only {background:#fdf6e3;border-left:4px solid #b8860b;padding:8px 12px;margin:8px 0;border-radius:0 4px 4px 0;}
.both-diff {background:#fef2f3;border-left:4px solid #b21f24;padding:8px 12px;margin:8px 0;border-radius:0 4px 4px 0;}
pre {background:#f4f4f1;padding:8px 10px;border-radius:3px;font-size:12.5px;overflow-x:auto;white-space:pre-wrap;}
.col {display:inline-block;vertical-align:top;width:48%;margin-right:1%;}
.label {font-size:11.5px;color:#777;text-transform:uppercase;letter-spacing:.04em;margin-bottom:2px;}
code {background:#f4f4f1;padding:1px 4px;border-radius:2px;font-size:13px;}
.tag {display:inline-block;font-size:11px;padding:1px 6px;border-radius:8px;background:#e0e0e0;margin-right:4px;}
.tag.t {background:#c5e1c8;color:#1d4f1f;}
.tag.m {background:#f0e2b8;color:#7a5f10;}
.tag.b {background:#f5c5c8;color:#6e1418;}
.muted {color:#666;font-size:12.5px;}
</style></head><body>"""

HTML_FOOT = "</body></html>"


def html_pre(obj) -> str:
    if isinstance(obj, str):
        return f"<pre>{obj}</pre>"
    return f"<pre>{json.dumps(obj, indent=2, ensure_ascii=False)}</pre>"


def render_html(diff: dict) -> str:
    s = diff["summary_counts"]
    parts = [HTML_HEAD]
    machine = f" ({diff['snapshot_machine_id']})" if diff.get("snapshot_machine_id") else ""
    parts.append(f"<h1>Env diff — your env vs <code>{diff['snapshot_owner']}{machine}</code></h1>")
    parts.append(
        f"<p class='muted'>Snapshot format <code>{diff['snapshot_format_version']}</code> "
        f"· comparer <code>{SCRIPT_VERSION}</code> "
        f"· generated <code>{diff.get('snapshot_generated_at','?')}</code> "
        f"· compared <code>{diff['compared_at']}</code> "
        f"· their claude version: <code>{diff.get('snapshot_claude_version') or 'unknown'}</code>.</p>"
    )
    skew = diff.get("version_skew_warning")
    if skew:
        parts.append(
            "<div style='background:#fef2e6;border-left:4px solid #b8860b;"
            "padding:10px 14px;border-radius:0 4px 4px 0;margin:10px 0;'>"
            f"<strong>⚠ Version skew:</strong> {skew['message']}"
            "</div>"
        )

    parts.append("<div class='summary'><strong>At a glance:</strong><ul>")
    parts.append(
        f"<li><span class='tag t'>theirs only</span> "
        f"{s['mcp_servers_only_in_theirs']} MCP · "
        f"{s['user_skills_only_in_theirs']} user-skills · "
        f"{s['plugin_skills_only_in_theirs']} plugin-skills · "
        f"{s['commands_only_in_theirs']} commands · "
        f"{s['agents_only_in_theirs']} agents</li>"
    )
    parts.append(
        f"<li><span class='tag m'>yours only</span> "
        f"{s['mcp_servers_only_in_mine']} MCP · "
        f"{s['user_skills_only_in_mine']} user-skills · "
        f"{s['plugin_skills_only_in_mine']} plugin-skills · "
        f"{s['commands_only_in_mine']} commands · "
        f"{s['agents_only_in_mine']} agents</li>"
    )
    parts.append(
        f"<li><span class='tag b'>both, different</span> "
        f"{s['mcp_servers_both_different']} MCP · "
        f"{s['hook_events_differing']} hook events · "
        f"{s['settings_keys_differing']} settings keys · "
        f"{s['commands_body_diverged']} commands (body diverged)</li>"
    )
    parts.append(
        f"<li>settings.local: {'differs' if s['settings_local_differs'] else 'identical/empty'} · "
        f"statusline: {'differs' if s['statusline_differs'] else 'identical/empty'} · "
        f"keybindings: {'differs' if s['keybindings_differs'] else 'identical/empty'}</li>"
    )
    parts.append(
        f"<li>Global CLAUDE.md: "
        f"{'identical' if s['claude_md_identical'] else 'differs (' + str(diff['global_claude_md']['theirs_length_chars']) + ' vs ' + str(diff['global_claude_md']['mine_length_chars']) + ' chars)'}</li>"
    )
    parts.append(
        f"<li>Installed plugins: "
        f"{s.get('plugins_same', 0)} same · "
        f"{s.get('plugins_version_diff', 0)} version-diff · "
        f"{s.get('plugins_sha_only_diff', 0)} sha-only-diff · "
        f"{s.get('plugins_only_in_theirs', 0)} only theirs · "
        f"{s.get('plugins_only_in_mine', 0)} only yours</li>"
    )
    parts.append(
        f"<li>Skill bodies (v0.4): "
        f"{s.get('skill_bodies_same', 0)} identical · "
        f"{s.get('skill_bodies_diverged', 0)} diverged · "
        f"{s.get('skill_bodies_only_in_theirs', 0)} only theirs · "
        f"{s.get('skill_bodies_only_in_mine', 0)} only yours</li>"
    )
    parts.append(
        f"<li>External CLIs (v0.4): "
        f"<code>uv</code> {s.get('uv_tools_only_in_theirs', 0)} only-theirs / {s.get('uv_tools_only_in_mine', 0)} only-yours · "
        f"<code>brew</code> {s.get('brew_only_in_theirs', 0)} only-theirs / {s.get('brew_only_in_mine', 0)} only-yours</li>"
    )
    parts.append("</ul></div>")

    # Hooks
    parts.append("<h2>Hooks</h2>")
    if not diff["hooks"]:
        parts.append("<p>No hook events differ. ✓</p>")
    else:
        for ev, both in diff["hooks"].items():
            parts.append(
                f"<h3>{ev} <span class='muted'>"
                f"({both.get('theirs_handler_count','?')} handlers theirs · "
                f"{both.get('mine_handler_count','?')} yours)</span></h3>"
            )
            parts.append("<div class='col'><div class='label'>Theirs</div>")
            parts.append(html_pre(both["theirs"]))
            parts.append("</div><div class='col'><div class='label'>Yours</div>")
            parts.append(html_pre(both["mine"]))
            parts.append("</div>")

    # MCP servers
    parts.append("<h2>MCP servers</h2>")
    mcp = diff["mcp_servers"]
    if mcp["only_theirs"]:
        parts.append("<div class='theirs-only'><strong>Only in theirs:</strong>")
        for k, v in mcp["only_theirs"].items():
            parts.append(f"<h3>{k}</h3>{html_pre(v)}")
        parts.append("</div>")
    if mcp["only_mine"]:
        parts.append("<div class='mine-only'><strong>Only in yours:</strong>")
        for k, v in mcp["only_mine"].items():
            parts.append(f"<h3>{k}</h3>{html_pre(v)}")
        parts.append("</div>")
    if mcp["both_different"]:
        parts.append("<div class='both-diff'><strong>In both, configured differently:</strong>")
        for k, v in mcp["both_different"].items():
            parts.append(f"<h3>{k}</h3>")
            parts.append("<div class='col'><div class='label'>Theirs</div>")
            parts.append(html_pre(v["theirs"]))
            parts.append("</div><div class='col'><div class='label'>Yours</div>")
            parts.append(html_pre(v["mine"]))
            parts.append("</div>")
        parts.append("</div>")
    if mcp["both_same"]:
        parts.append(f"<p class='muted'>Same in both: <code>{', '.join(mcp['both_same'])}</code></p>")

    # Settings (top-level safe keys)
    parts.append("<h2>Settings (safe-to-share top-level keys)</h2>")
    if not diff["settings"]:
        parts.append("<p>No safe-to-share settings differ. ✓</p>")
    else:
        for k, v in diff["settings"].items():
            parts.append(f"<h3>{k}</h3>")
            parts.append("<div class='col'><div class='label'>Theirs</div>")
            parts.append(html_pre(v["theirs"]))
            parts.append("</div><div class='col'><div class='label'>Yours</div>")
            parts.append(html_pre(v["mine"]))
            parts.append("</div>")

    # settings.local
    parts.append("<h2>settings.local.json</h2>")
    if diff["settings_local"] is None:
        parts.append("<p>Identical or both empty. ✓</p>")
    else:
        parts.append("<div class='both-diff'>")
        parts.append("<div class='col'><div class='label'>Theirs</div>")
        parts.append(html_pre(diff["settings_local"]["theirs"]))
        parts.append("</div><div class='col'><div class='label'>Yours</div>")
        parts.append(html_pre(diff["settings_local"]["mine"]))
        parts.append("</div></div>")

    # statusline
    parts.append("<h2>Status line config (ccstatusline)</h2>")
    if diff["statusline"] is None:
        parts.append("<p>Identical or both empty. ✓</p>")
    else:
        parts.append("<div class='both-diff'>")
        parts.append("<div class='col'><div class='label'>Theirs</div>")
        parts.append(html_pre(diff["statusline"]["theirs"]))
        parts.append("</div><div class='col'><div class='label'>Yours</div>")
        parts.append(html_pre(diff["statusline"]["mine"]))
        parts.append("</div></div>")

    # keybindings
    parts.append("<h2>Keybindings</h2>")
    if diff["keybindings"] is None:
        parts.append("<p>Identical or both empty. ✓</p>")
    else:
        parts.append("<div class='both-diff'>")
        parts.append("<div class='col'><div class='label'>Theirs</div>")
        parts.append(html_pre(diff["keybindings"]["theirs"]))
        parts.append("</div><div class='col'><div class='label'>Yours</div>")
        parts.append(html_pre(diff["keybindings"]["mine"]))
        parts.append("</div></div>")

    # User skills
    parts.append("<h2>User-level skills (~/.claude/skills/)</h2>")
    sk = diff["skills_user"]
    if sk["only_theirs"]:
        parts.append("<div class='theirs-only'><strong>Only in theirs:</strong> ")
        parts.append(", ".join(f"<code>{n}</code>" for n in sk["only_theirs"]))
        parts.append("</div>")
    if sk["only_mine"]:
        parts.append("<div class='mine-only'><strong>Only in yours:</strong> ")
        parts.append(", ".join(f"<code>{n}</code>" for n in sk["only_mine"]))
        parts.append("</div>")
    if sk["both"]:
        parts.append(f"<p class='muted'>Both have: <code>{', '.join(sk['both'])}</code></p>")
    if not (sk["only_theirs"] or sk["only_mine"] or sk["both"]):
        parts.append("<p class='muted'>None on either side.</p>")

    # Plugin-shipped skills
    parts.append("<h2>Plugin-shipped skills</h2>")
    psk = diff["skills_plugin"]
    if psk["only_theirs"]:
        parts.append("<div class='theirs-only'><strong>Only in theirs:</strong><ul>")
        for s_ in psk["only_theirs"]:
            parts.append(f"<li><code>{s_['name']}</code> from <code>{s_['source']}</code></li>")
        parts.append("</ul></div>")
    if psk["only_mine"]:
        parts.append("<div class='mine-only'><strong>Only in yours:</strong><ul>")
        for s_ in psk["only_mine"]:
            parts.append(f"<li><code>{s_['name']}</code> from <code>{s_['source']}</code></li>")
        parts.append("</ul></div>")
    if psk["both"]:
        parts.append(f"<p class='muted'>Both have {len(psk['both'])} plugin-skills (matched on name+source).</p>")

    # Commands
    parts.append("<h2>Slash commands</h2>")
    cm = diff["commands"]
    if cm["only_theirs"]:
        parts.append("<div class='theirs-only'><strong>Only in theirs:</strong> ")
        parts.append(", ".join(f"<code>/{n}</code>" for n in cm["only_theirs"]))
        parts.append("</div>")
    if cm["only_mine"]:
        parts.append("<div class='mine-only'><strong>Only in yours:</strong> ")
        parts.append(", ".join(f"<code>/{n}</code>" for n in cm["only_mine"]))
        parts.append("</div>")
    if cm["both_diff_body"]:
        parts.append("<div class='both-diff'><strong>In both, but body diverged:</strong>")
        for c in cm["both_diff_body"]:
            parts.append(
                f"<h3>/{c['name']} <span class='muted'>"
                f"(theirs {c['theirs_chars']}ch · yours {c['mine_chars']}ch)</span></h3>"
            )
            parts.append("<div class='col'><div class='label'>Theirs body</div>")
            parts.append(html_pre(c["theirs_body"]))
            parts.append("</div><div class='col'><div class='label'>Yours body</div>")
            parts.append(html_pre(c["mine_body"]))
            parts.append("</div>")
        parts.append("</div>")
    if cm["both_same_body"]:
        parts.append(f"<p class='muted'>Identical body in both: <code>{', '.join('/' + n for n in cm['both_same_body'])}</code></p>")

    # Agents
    parts.append("<h2>Agents</h2>")
    ag = diff["agents"]
    if ag["only_theirs"]:
        parts.append("<div class='theirs-only'><strong>Only in theirs:</strong> ")
        parts.append(", ".join(f"<code>{n}</code>" for n in ag["only_theirs"]))
        parts.append("</div>")
    if ag["only_mine"]:
        parts.append("<div class='mine-only'><strong>Only in yours:</strong> ")
        parts.append(", ".join(f"<code>{n}</code>" for n in ag["only_mine"]))
        parts.append("</div>")
    if ag["both"]:
        parts.append(f"<p class='muted'>Both have: <code>{', '.join(ag['both'])}</code></p>")
    if not (ag["only_theirs"] or ag["only_mine"] or ag["both"]):
        parts.append("<p class='muted'>No user-level agents on either side.</p>")

    # Central reference files (~/Claude/)
    parts.append("<h2>Central reference files (~/Claude/)</h2>")
    cf = diff.get("central_files", {})
    if not cf:
        parts.append("<p class='muted'>None tracked.</p>")
    else:
        rows = []
        for name, v in cf.items():
            if not v["theirs_present"]:
                status = f"<span class='tag m'>only yours</span> ({v['mine_length_chars']} chars)"
            elif not v["mine_present"]:
                status = f"<span class='tag t'>only theirs</span> ({v['theirs_length_chars']} chars)"
            elif v["identical"]:
                status = "identical ✓"
            else:
                status = (
                    f"<span class='tag b'>differs</span> "
                    f"(theirs {v['theirs_length_chars']} vs yours {v['mine_length_chars']} chars)"
                )
            rows.append(f"<li><code>{name}</code> — {status}</li>")
        parts.append("<ul>" + "".join(rows) + "</ul>")

    # Installed plugins (version pinning)
    parts.append("<h2>Installed plugins (version pinning)</h2>")
    ip = diff["installed_plugins"]
    if ip["only_theirs"]:
        parts.append("<div class='theirs-only'><strong>Only on theirs:</strong><ul>")
        for p in ip["only_theirs"]:
            parts.append(
                f"<li><code>{p['name']}</code> · version <code>{p.get('version','?')}</code>"
                f" · sha <code>{(p.get('gitCommitSha') or '?')[:12]}</code></li>"
            )
        parts.append("</ul></div>")
    if ip["only_mine"]:
        parts.append("<div class='mine-only'><strong>Only on yours:</strong><ul>")
        for p in ip["only_mine"]:
            parts.append(
                f"<li><code>{p['name']}</code> · version <code>{p.get('version','?')}</code>"
                f" · sha <code>{(p.get('gitCommitSha') or '?')[:12]}</code></li>"
            )
        parts.append("</ul></div>")
    if ip["version_diff"]:
        parts.append("<div class='both-diff'><strong>Installed on both, different versions:</strong><ul>")
        for p in ip["version_diff"]:
            parts.append(
                f"<li><code>{p['name']}</code> — "
                f"theirs <code>{p['theirs_version']}</code> "
                f"(<code>{(p.get('theirs_sha') or '?')[:12]}</code>) "
                f"vs yours <code>{p['mine_version']}</code> "
                f"(<code>{(p.get('mine_sha') or '?')[:12]}</code>)</li>"
            )
        parts.append("</ul></div>")
    if ip["sha_only_diff"]:
        parts.append("<div class='both-diff'><strong>Same version, different git SHA "
                     "(repo moved without a version bump):</strong><ul>")
        for p in ip["sha_only_diff"]:
            parts.append(
                f"<li><code>{p['name']}</code> @ <code>{p['version']}</code> — "
                f"theirs <code>{(p.get('theirs_sha') or '?')[:12]}</code> "
                f"vs yours <code>{(p.get('mine_sha') or '?')[:12]}</code></li>"
            )
        parts.append("</ul></div>")
    if ip["same"]:
        parts.append(
            f"<p class='muted'>Identical on both ({len(ip['same'])}): "
            + ", ".join(f"<code>{p['name']}</code>@<code>{p['version']}</code>" for p in ip["same"])
            + "</p>"
        )
    if not (ip["only_theirs"] or ip["only_mine"] or ip["version_diff"] or ip["sha_only_diff"] or ip["same"]):
        parts.append("<p class='muted'>No installed-plugins data on either side "
                     "(snapshot may be v0.1 or v0.2 — capture added in v0.3).</p>")

    # User skill BODIES (v0.4)
    parts.append("<h2>User skill bodies (SKILL.md + bundled files)</h2>")
    sb = diff.get("skills_user_bodies", {"only_theirs": [], "only_mine": [], "both_same": [], "both_diff": []})
    if not (sb["only_theirs"] or sb["only_mine"] or sb["both_diff"] or sb["both_same"]):
        parts.append("<p class='muted'>No skill bodies in the snapshot — that snapshot may be v0.3 or earlier "
                     "(skill-body capture was added in v0.4). Re-publish to surface this section.</p>")
    else:
        if sb["only_theirs"]:
            parts.append("<div class='theirs-only'><strong>Only in theirs — paste these into <code>~/.claude/skills/&lt;name&gt;/</code> to acquire:</strong><ul>")
            for x in sb["only_theirs"]:
                parts.append(
                    f"<li><code>{x['name']}</code> — SKILL.md {x['skill_md_chars']} chars, "
                    f"{x['bundle_files']} bundle files (status: <code>{x.get('bundle_status','?')}</code>). "
                    f"Body in JSON diff under <code>skills_user_bodies.only_theirs</code>.</li>"
                )
            parts.append("</ul></div>")
        if sb["only_mine"]:
            parts.append("<div class='mine-only'><strong>Only in yours:</strong><ul>")
            for x in sb["only_mine"]:
                parts.append(f"<li><code>{x['name']}</code> ({x['skill_md_chars']} chars)</li>")
            parts.append("</ul></div>")
        if sb["both_diff"]:
            parts.append("<div class='both-diff'><strong>In both, content diverged:</strong>")
            for x in sb["both_diff"]:
                parts.append(f"<h3>{x['name']}</h3>")
                bits = []
                if not x["skill_md_same"]:
                    bits.append(f"SKILL.md differs (theirs {x['theirs_skill_md_chars']} vs yours {x['mine_skill_md_chars']} chars)")
                if x["files_only_theirs"]:
                    bits.append(f"<span class='tag t'>only theirs:</span> <code>{', '.join(x['files_only_theirs'])}</code>")
                if x["files_only_mine"]:
                    bits.append(f"<span class='tag m'>only yours:</span> <code>{', '.join(x['files_only_mine'])}</code>")
                if x["files_both_diff"]:
                    bits.append(f"<span class='tag b'>content differs:</span> <code>{', '.join(x['files_both_diff'])}</code>")
                parts.append("<p>" + " · ".join(bits) + "</p>")
                if not x["skill_md_same"]:
                    parts.append("<div class='col'><div class='label'>Theirs SKILL.md (first 1200 chars)</div>")
                    parts.append(html_pre((x.get("theirs_skill_md") or "")[:1200]))
                    parts.append("</div><div class='col'><div class='label'>Yours SKILL.md (first 1200 chars)</div>")
                    parts.append(html_pre((x.get("mine_skill_md") or "")[:1200]))
                    parts.append("</div>")
            parts.append("</div>")
        if sb["both_same"]:
            parts.append(f"<p class='muted'>Identical bodies: <code>{', '.join(sb['both_same'])}</code></p>")

    # External CLI inventory (v0.4)
    parts.append("<h2>External command-line tools (uv + brew)</h2>")
    ec = diff.get("external_clis", {})
    if not ec or (not ec.get("theirs_captured") and not ec.get("mine_captured")):
        parts.append("<p class='muted'>No external-CLI capture in either snapshot "
                     "(snapshot may be v0.3 or earlier — added in v0.4).</p>")
    else:
        if ec["uv_only_theirs"]:
            parts.append("<div class='theirs-only'><strong>uv tools their machine has, yours doesn't — likely MCP-server dependencies:</strong><ul>")
            for name in ec["uv_only_theirs"]:
                parts.append(f"<li><code>{name}</code> — install on your machine: <code>uv tool install {name}</code></li>")
            parts.append("</ul></div>")
        if ec["brew_only_theirs"]:
            parts.append("<div class='theirs-only'><strong>brew formulas their machine has, yours doesn't:</strong><ul>")
            for name in ec["brew_only_theirs"]:
                parts.append(f"<li><code>{name}</code> — install: <code>brew install {name}</code></li>")
            parts.append("</ul></div>")
        if ec["uv_only_mine"] or ec["brew_only_mine"]:
            parts.append("<div class='mine-only'><strong>You have, theirs doesn't:</strong> ")
            mine_bits = []
            if ec["uv_only_mine"]:
                mine_bits.append("uv: " + ", ".join(f"<code>{n}</code>" for n in ec["uv_only_mine"]))
            if ec["brew_only_mine"]:
                mine_bits.append("brew: " + ", ".join(f"<code>{n}</code>" for n in ec["brew_only_mine"]))
            parts.append(" · ".join(mine_bits))
            parts.append("</div>")
        if not (ec["uv_only_theirs"] or ec["uv_only_mine"] or ec["brew_only_theirs"] or ec["brew_only_mine"]):
            parts.append("<p>External CLI inventories match. ✓</p>")
        if ec.get("theirs_notes") or ec.get("mine_notes"):
            parts.append("<p class='muted'>Capture notes (e.g. missing uv/brew on one side): "
                         f"theirs={ec.get('theirs_notes', [])}, yours={ec.get('mine_notes', [])}</p>")

    # CLAUDE.md
    parts.append("<h2>Global CLAUDE.md</h2>")
    if diff["global_claude_md"]["identical"]:
        parts.append("<p>Identical. ✓</p>")
    else:
        parts.append(
            f"<p>Differ — theirs is <strong>{diff['global_claude_md']['theirs_length_chars']}</strong> chars, "
            f"yours is <strong>{diff['global_claude_md']['mine_length_chars']}</strong> chars. "
            f"(Full text in JSON output.)</p>"
        )

    parts.append(HTML_FOOT)
    return "\n".join(parts)


# --- CLI --------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", required=True, help="Path or HTTPS URL to snapshot JSON")
    ap.add_argument("--out", help="Write diff JSON to this path (else stdout)")
    ap.add_argument("--html", help="Also write HTML report to this path")
    args = ap.parse_args()

    snapshot = fetch_snapshot(args.snapshot)
    local = read_local_env()
    diff = build_diff(snapshot, local)
    skew = check_version_skew(snapshot)
    if skew:
        diff["version_skew_warning"] = skew
        print(f"WARN: {skew['message']}", file=sys.stderr)

    text = json.dumps(diff, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).expanduser().write_text(text + "\n")
        print(f"Wrote diff JSON: {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text + "\n")

    if args.html:
        html_path = Path(args.html).expanduser()
        html_path.write_text(render_html(diff))
        print(f"Wrote diff HTML: {html_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
