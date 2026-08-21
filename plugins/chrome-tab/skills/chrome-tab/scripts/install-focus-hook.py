#!/usr/bin/env python3
"""Install (or remove) the restore-focus hooks in ~/.claude/settings.json.

Run this yourself — Claude should not edit settings.json on your behalf.

    python3 install-focus-hook.py             # install
    python3 install-focus-hook.py --dry-run   # show the resulting hooks block
    python3 install-focus-hook.py --remove    # undo

This is SEPARATE from the bare-`open` guard (`install-hook.py`). That one stops
Claude from opening files the wrong way; this one undoes the focus steal that
comes from the Claude-in-Chrome extension, which no rule can prevent.

It registers two entries:

    PreToolUse  matcher mcp__claude-in-chrome__.*   --snapshot   (where were you?)
    Stop                                            --restore    (put you back)

Idempotent, and backs up settings.json before changing anything.
"""

import argparse
import json
import pathlib
import shutil
import sys
import time

SETTINGS = pathlib.Path.home() / ".claude" / "settings.json"
SCRIPT = pathlib.Path(__file__).resolve().parent / "restore-focus.sh"
MATCHER = "mcp__claude-in-chrome__.*"
TAG = "restore-focus."


def load():
    if not SETTINGS.exists():
        return {}
    try:
        return json.loads(SETTINGS.read_text() or "{}")
    except json.JSONDecodeError as e:
        sys.exit(f"settings.json is not valid JSON ({e}). Fix it first; nothing was changed.")


def strip(hooks, event):
    """Drop our entries from one event, pruning matchers left empty."""
    kept = []
    for m in hooks.get(event, []):
        m["hooks"] = [h for h in m.get("hooks", []) if TAG not in str(h.get("command", ""))]
        if m["hooks"]:
            kept.append(m)
    if kept:
        hooks[event] = kept
    else:
        hooks.pop(event, None)


def present(cfg):
    for event in ("PreToolUse", "Stop"):
        for m in cfg.get("hooks", {}).get(event, []):
            for h in m.get("hooks", []):
                if TAG in str(h.get("command", "")):
                    return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remove", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not SCRIPT.exists():
        sys.exit(f"helper script missing: {SCRIPT}")

    cfg = load()
    hooks = cfg.setdefault("hooks", {})

    if a.remove:
        strip(hooks, "PreToolUse")
        strip(hooks, "Stop")
        if not hooks:
            cfg.pop("hooks")
        action = "removed"
    else:
        if present(cfg):
            print("Already installed — nothing to do.")
            return
        hooks.setdefault("PreToolUse", []).append({
            "matcher": MATCHER,
            "hooks": [{"type": "command", "command": f'sh "{SCRIPT}" --snapshot'}],
        })
        hooks.setdefault("Stop", []).append({
            "hooks": [{"type": "command", "command": f'sh "{SCRIPT}" --restore'}],
        })
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
    print(f"Restore-focus hooks {action} in {SETTINGS}")
    print("Live immediately — Claude Code file-watches settings.json, so running sessions\n"
          "pick hooks up without a restart (verified 2026-08-15). Note this differs from\n"
          "CLAUDE.md rules, which ARE frozen into a session at startup.")
    if action == "installed":
        print("\nWatch it decide:  export CHROME_TAB_FOCUS_DEBUG=1   (logs skip/restore reasons)")
        print("Undo:             python3 \"%s\" --remove" % pathlib.Path(__file__).resolve())


if __name__ == "__main__":
    main()
