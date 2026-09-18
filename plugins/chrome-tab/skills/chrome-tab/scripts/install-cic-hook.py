#!/usr/bin/env python3
"""Install (or remove) the Claude-in-Chrome window hook in ~/.claude/settings.json.

Run this yourself. Claude does not edit settings.json on your behalf.

    python3 ~/.claude/skills/chrome-tab/scripts/install-cic-hook.py
    python3 …/install-cic-hook.py --remove
    python3 …/install-cic-hook.py --dry-run

The hook runs `chrome-tab hook claude-in-chrome` after three Claude-in-Chrome tools:
tabs_context_mcp, navigate and browser_batch. When one of them reports a brand-new session
tab group, the hook has the chrome-tab helper extension move that group into your browse
window. The browse window defaults to "Claude sessions"; set "browse_window" in
~/.config/chrome-tab/config.json to use another. It needs the helper
(`chrome-tab helper status`). Without the helper it only adds a one-line note to the session.

Running it twice doesn't add the hook twice. It writes a timestamped backup of
settings.json before any change.
"""

import argparse
import json
import pathlib
import shutil
import sys
import time

SETTINGS = pathlib.Path.home() / ".claude" / "settings.json"
MATCHER = "mcp__claude-in-chrome__(tabs_context_mcp|navigate|browser_batch)"
COMMAND = f'"{pathlib.Path.home() / ".local" / "bin" / "chrome-tab"}" hook claude-in-chrome'
MARK = "hook claude-in-chrome"


def load():
    if not SETTINGS.exists():
        return {}
    try:
        return json.loads(SETTINGS.read_text() or "{}")
    except json.JSONDecodeError as e:
        sys.exit(f"settings.json is not valid JSON ({e}). Fix it first; nothing was changed.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remove", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cfg = load()
    hooks = cfg.setdefault("hooks", {})
    post = hooks.setdefault("PostToolUse", [])
    present = any(MARK in str(h.get("command", "")) for m in post for h in m.get("hooks", []))

    if a.remove:
        kept = []
        for m in post:
            m["hooks"] = [h for h in m.get("hooks", []) if MARK not in str(h.get("command", ""))]
            if m["hooks"]:
                kept.append(m)
        hooks["PostToolUse"] = kept
        if not kept:
            hooks.pop("PostToolUse")
        if not hooks:
            cfg.pop("hooks")
        action = "removed" if present else "not present — nothing removed"
    else:
        if present:
            print("Already installed — nothing to do.")
            return
        post.append({"matcher": MATCHER,
                     "hooks": [{"type": "command", "command": COMMAND, "timeout": 20}]})
        action = "installed"

    if a.dry_run:
        print(f"[dry-run] would be {action}. Resulting hooks block:\n")
        print(json.dumps(cfg.get("hooks", {}), indent=2))
        return

    if SETTINGS.exists():
        bak = SETTINGS.with_suffix(f".json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(SETTINGS, bak)
        print(f"backup: {bak}")
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"Claude-in-Chrome window hook {action} in {SETTINGS}")
    print("Running sessions pick it up without a restart.")


if __name__ == "__main__":
    main()
