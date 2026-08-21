#!/usr/bin/env python3
"""Install (or remove) the bare-`open` guard hook in ~/.claude/settings.json.

Run this yourself — Claude should not edit settings.json on your behalf.

    python3 "~/Claude/tools/chrome-tabs (claude)/hooks/install-hook.py"
    python3 "…/install-hook.py" --remove
    python3 "…/install-hook.py" --dry-run

Idempotent: running it twice does not duplicate the hook. Always writes a
timestamped backup of settings.json before changing anything.
"""

import argparse
import json
import pathlib
import shutil
import sys
import time

SETTINGS = pathlib.Path.home() / ".claude" / "settings.json"
# The .sh wrapper is the entry point: it rejects the common case (no "open" in
# the command) in shell at ~3.6 ms and only starts Python — ~12.5 ms — when the
# string is actually present. A PreToolUse/Bash hook runs on every Bash call, so
# the common path is the one worth optimising.
HOOK = str(pathlib.Path(__file__).resolve().parent / "block-bare-open.sh")
CMD = f'sh "{HOOK}"'


def load():
    if not SETTINGS.exists():
        return {}
    try:
        return json.loads(SETTINGS.read_text() or "{}")
    except json.JSONDecodeError as e:
        sys.exit(f"settings.json is not valid JSON ({e}). Fix it first; nothing was changed.")


def already_there(cfg):
    for m in cfg.get("hooks", {}).get("PreToolUse", []):
        for h in m.get("hooks", []):
            if "block-bare-open" in str(h.get("command", "")):
                return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remove", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not pathlib.Path(HOOK).exists():
        sys.exit(f"hook script missing: {HOOK}")

    cfg = load()
    hooks = cfg.setdefault("hooks", {})
    pre = hooks.setdefault("PreToolUse", [])

    if a.remove:
        before = len(pre)
        kept = []
        for m in pre:
            m["hooks"] = [h for h in m.get("hooks", [])
                          if "block-bare-open" not in str(h.get("command", ""))]
            if m["hooks"]:
                kept.append(m)
        hooks["PreToolUse"] = kept
        if not kept:
            hooks.pop("PreToolUse")
        if not hooks:
            cfg.pop("hooks")
        action = f"removed (PreToolUse entries: {before} -> {len(kept)})"
    else:
        if already_there(cfg):
            print("Already installed — nothing to do.")
            return
        pre.append({"matcher": "Bash", "hooks": [{"type": "command", "command": CMD}]})
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
    print(f"Hook {action} in {SETTINGS}")
    print("Live immediately — Claude Code file-watches settings.json, so running sessions\n"
          "pick hooks up without a restart (verified 2026-08-15). Note this differs from\n"
          "CLAUDE.md rules, which ARE frozen into a session at startup.")


if __name__ == "__main__":
    main()
