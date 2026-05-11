#!/usr/bin/env python3
"""
compare_env.py — diff a published environment snapshot against the local one.

Reads:
  - a snapshot JSON file (local path or HTTPS URL)
  - the local Claude Code environment (~/.claude/settings.json,
    ~/.claude.json mcpServers, ~/.claude/CLAUDE.md, ~/.claude/skills/,
    ~/.claude/commands/) — captured the same way publish_snapshot.py does

Outputs structured JSON describing:
  - hooks: which hooks are in the snapshot but not local, vice versa, and overlapping ones with diffs
  - mcp_servers: which MCPs are in the snapshot but not local, etc.
  - settings: a top-level field-by-field diff for the safe-to-share keys
  - skills + commands: which named items are in the snapshot but not local
  - global_claude_md: not diffed line-by-line here — just a side-by-side length report

The output is meant for the env-compare SKILL to read and present to the user
as a guided import flow. This script does NOT modify anything on disk.

Usage:
  compare_env.py --snapshot snapshots/jacob.json
  compare_env.py --snapshot https://raw.githubusercontent.com/Xtzj2333/jacob-skills/main/snapshots/jacob.json
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

# Reuse the read helpers from the publisher (kept inline so this script is standalone).

CLAUDE_JSON_PUBLISHED_KEYS = {"mcpServers"}
SAFE_SETTINGS_KEYS = {
    "skillListingBudgetFraction", "permissions", "hooks", "statusLine",
    "enabledPlugins", "extraKnownMarketplaces", "effortLevel", "theme",
    "remoteControlAtStartup", "agentPushNotifEnabled",
    "skipAutoPermissionPrompt", "tui", "outputStyle", "language",
    "editorMode", "defaultShell", "attribution",
}


def read_json_safe(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def read_text_safe(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text()
    except Exception:
        return None


def list_skills(skills_dir: Path) -> list[dict]:
    if not skills_dir.is_dir():
        return []
    out = []
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        out.append({"name": entry.name})
    return out


def list_commands(commands_dir: Path) -> list[dict]:
    if not commands_dir.is_dir():
        return []
    out = []
    for f in sorted(commands_dir.iterdir()):
        if not f.is_file() or f.suffix != ".md":
            continue
        out.append({"name": f.stem})
    return out


def fetch_snapshot(src: str) -> dict:
    """Load snapshot from local path or HTTPS URL."""
    if src.startswith(("http://", "https://")):
        with urllib.request.urlopen(src, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    return json.loads(Path(src).expanduser().read_text())


def read_local_env() -> dict:
    home = Path.home()
    settings = read_json_safe(home / ".claude" / "settings.json") or {}
    big = read_json_safe(home / ".claude.json") or {}
    return {
        "settings_json": settings,
        "mcp_servers": big.get("mcpServers", {}),
        "global_claude_md": read_text_safe(home / ".claude" / "CLAUDE.md") or "",
        "skills": list_skills(home / ".claude" / "skills"),
        "commands": list_commands(home / ".claude" / "commands"),
    }


# --- Diff helpers -----------------------------------------------------------

def diff_dict_by_key(theirs: dict, mine: dict) -> dict:
    """For dicts whose keys identify items: return only-theirs / only-mine / both-different / both-same."""
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


def diff_hooks(theirs_hooks: dict, mine_hooks: dict) -> dict:
    """
    Per-event diff: each hook event (Stop, Notification, etc.) is its own bucket.
    Within an event we just present theirs vs mine sub-arrays for human comparison;
    we don't try to align individual entries.
    """
    out = {}
    for event in sorted(set(theirs_hooks.keys()) | set(mine_hooks.keys())):
        t = theirs_hooks.get(event, [])
        m = mine_hooks.get(event, [])
        if t == m:
            continue
        out[event] = {"theirs": t, "mine": m}
    return out


def diff_settings_top_level(theirs: dict, mine: dict) -> dict:
    """Field-by-field diff for safe-to-share top-level settings keys (excluding hooks, handled separately)."""
    out = {}
    keys = (set(theirs.keys()) | set(mine.keys())) & SAFE_SETTINGS_KEYS
    keys.discard("hooks")  # handled by diff_hooks
    for k in sorted(keys):
        t = theirs.get(k, "<not set>")
        m = mine.get(k, "<not set>")
        if t != m:
            out[k] = {"theirs": t, "mine": m}
    return out


def build_diff(snapshot: dict, local: dict) -> dict:
    env_t = snapshot.get("environment", {})
    env_m = local

    diff = {
        "compared_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "snapshot_owner": snapshot.get("owner", "<unknown>"),
        "snapshot_generated_at": snapshot.get("generated_at"),
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
        "skills": diff_named_lists(env_t.get("skills", []), env_m.get("skills", [])),
        "commands": diff_named_lists(env_t.get("commands", []), env_m.get("commands", [])),
        "global_claude_md": {
            "theirs_length_chars": len(env_t.get("global_claude_md", "") or ""),
            "mine_length_chars": len(env_m.get("global_claude_md", "") or ""),
            "identical": env_t.get("global_claude_md", "") == env_m.get("global_claude_md", ""),
        },
    }

    # Counts the SKILL can show at a glance
    diff["summary_counts"] = {
        "hook_events_differing": len(diff["hooks"]),
        "mcp_servers_only_in_theirs": len(diff["mcp_servers"]["only_theirs"]),
        "mcp_servers_only_in_mine": len(diff["mcp_servers"]["only_mine"]),
        "mcp_servers_both_different": len(diff["mcp_servers"]["both_different"]),
        "settings_keys_differing": len(diff["settings"]),
        "skills_only_in_theirs": len(diff["skills"]["only_theirs"]),
        "skills_only_in_mine": len(diff["skills"]["only_mine"]),
        "commands_only_in_theirs": len(diff["commands"]["only_theirs"]),
        "commands_only_in_mine": len(diff["commands"]["only_mine"]),
        "claude_md_identical": diff["global_claude_md"]["identical"],
    }
    return diff


# --- HTML renderer ----------------------------------------------------------

HTML_HEAD = """<!doctype html>
<html><head><meta charset="utf-8"><title>Environment diff</title>
<style>
body {font: 15px/1.5 -apple-system,system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 18px;color:#1a1a1a;}
h1 {font-size: 22px; border-bottom: 2px solid #1a1a1a; padding-bottom: 8px;}
h2 {font-size: 18px; margin-top: 28px; border-bottom: 1px solid #d8d8d8; padding-bottom: 4px;}
h3 {font-size: 15px; margin-top: 16px; color: #335c81;}
.summary {background:#f4f4f1;padding:10px 14px;border-radius:4px;font-size:14px;}
.summary li {margin: 2px 0;}
.theirs-only {background:#ecf5ee;border-left:4px solid #2e7d32;padding:8px 12px;margin:8px 0;border-radius:0 4px 4px 0;}
.mine-only {background:#fdf6e3;border-left:4px solid #b8860b;padding:8px 12px;margin:8px 0;border-radius:0 4px 4px 0;}
.both-diff {background:#fef2f3;border-left:4px solid #b21f24;padding:8px 12px;margin:8px 0;border-radius:0 4px 4px 0;}
pre {background:#f4f4f1;padding:8px 10px;border-radius:3px;font-size:12.5px;overflow-x:auto;}
.col {display:inline-block;vertical-align:top;width:48%;margin-right:1%;}
.label {font-size:11.5px;color:#777;text-transform:uppercase;letter-spacing:.04em;margin-bottom:2px;}
code {background:#f4f4f1;padding:1px 4px;border-radius:2px;font-size:13px;}
.tag {display:inline-block;font-size:11px;padding:1px 6px;border-radius:8px;background:#e0e0e0;margin-right:4px;}
.tag.t {background:#c5e1c8;color:#1d4f1f;}
.tag.m {background:#f0e2b8;color:#7a5f10;}
.tag.b {background:#f5c5c8;color:#6e1418;}
</style></head><body>"""

HTML_FOOT = "</body></html>"


def html_pre(obj) -> str:
    return f"<pre>{json.dumps(obj, indent=2, ensure_ascii=False)}</pre>"


def render_html(diff: dict) -> str:
    s = diff["summary_counts"]
    parts = [HTML_HEAD]
    parts.append(f"<h1>Env diff — your env vs <code>{diff['snapshot_owner']}</code></h1>")
    parts.append(f"<p style='color:#555;font-size:13px;'>Snapshot generated <code>{diff.get('snapshot_generated_at','?')}</code>. Compared <code>{diff['compared_at']}</code>.</p>")

    parts.append("<div class='summary'><strong>At a glance:</strong><ul>")
    parts.append(f"<li><span class='tag t'>theirs only</span> {s['mcp_servers_only_in_theirs']} MCP servers · {s['skills_only_in_theirs']} skills · {s['commands_only_in_theirs']} commands</li>")
    parts.append(f"<li><span class='tag m'>yours only</span> {s['mcp_servers_only_in_mine']} MCP servers · {s['skills_only_in_mine']} skills · {s['commands_only_in_mine']} commands</li>")
    parts.append(f"<li><span class='tag b'>both, different</span> {s['mcp_servers_both_different']} MCP servers · {s['hook_events_differing']} hook events · {s['settings_keys_differing']} settings keys</li>")
    parts.append(f"<li>Global CLAUDE.md: {'identical' if s['claude_md_identical'] else 'differs (' + str(diff['global_claude_md']['theirs_length_chars']) + ' vs ' + str(diff['global_claude_md']['mine_length_chars']) + ' chars)'}</li>")
    parts.append("</ul></div>")

    # Hooks
    parts.append("<h2>Hooks</h2>")
    if not diff["hooks"]:
        parts.append("<p>No hook events differ. ✓</p>")
    else:
        for ev, both in diff["hooks"].items():
            parts.append(f"<h3>{ev}</h3>")
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
        for k in mcp["only_mine"]:
            parts.append(f" <code>{k}</code>")
        parts.append("</div>")
    if mcp["both_different"]:
        parts.append("<div class='both-diff'><strong>In both, but configured differently:</strong>")
        for k, v in mcp["both_different"].items():
            parts.append(f"<h3>{k}</h3>")
            parts.append("<div class='col'><div class='label'>Theirs</div>")
            parts.append(html_pre(v["theirs"]))
            parts.append("</div><div class='col'><div class='label'>Yours</div>")
            parts.append(html_pre(v["mine"]))
            parts.append("</div>")
        parts.append("</div>")
    if mcp["both_same"]:
        parts.append(f"<p style='color:#555;font-size:13px;'>Same in both: <code>{', '.join(mcp['both_same'])}</code></p>")

    # Settings
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

    # Skills
    parts.append("<h2>Skills</h2>")
    sk = diff["skills"]
    if sk["only_theirs"]:
        parts.append("<div class='theirs-only'><strong>Only in theirs:</strong> ")
        parts.append(", ".join(f"<code>{n}</code>" for n in sk["only_theirs"]))
        parts.append("</div>")
    if sk["only_mine"]:
        parts.append("<div class='mine-only'><strong>Only in yours:</strong> ")
        parts.append(", ".join(f"<code>{n}</code>" for n in sk["only_mine"]))
        parts.append("</div>")
    if sk["both"]:
        parts.append(f"<p style='color:#555;font-size:13px;'>Both have: <code>{', '.join(sk['both'])}</code></p>")

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
    if cm["both"]:
        parts.append(f"<p style='color:#555;font-size:13px;'>Both have: <code>{', '.join('/' + n for n in cm['both'])}</code></p>")

    # CLAUDE.md
    parts.append("<h2>Global CLAUDE.md</h2>")
    if diff["global_claude_md"]["identical"]:
        parts.append("<p>Identical. ✓</p>")
    else:
        parts.append(f"<p>Differ — theirs is <strong>{diff['global_claude_md']['theirs_length_chars']}</strong> chars, yours is <strong>{diff['global_claude_md']['mine_length_chars']}</strong> chars. (Full text in JSON output; not rendered here — open in a diff tool of your choice if needed.)</p>")

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
