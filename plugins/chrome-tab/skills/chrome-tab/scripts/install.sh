#!/bin/sh
# Put `chrome-tab` on your PATH. Safe to re-run.
#
#   sh install.sh            # ~/.local/bin/chrome-tab (launcher or symlink, see below)
#   sh install.sh --hook     # ...and also install the bare-`open` guard hook
#
# From a Claude Code plugin cache (~/.claude/plugins/cache/<marketplace>/chrome-tab/<version>/)
# this writes a small LAUNCHER that runs whichever chrome-tab copy Claude Code has
# installed, so a later `claude plugin update chrome-tab@<marketplace>` takes effect
# by itself. A plain symlink would pin PATH to *this version's* directory and keep
# running it after an update while the update reported success — that is what
# happened before 0.1.3 (2026-09-15). From a source checkout (e.g. ~/.claude/skills)
# it is a plain symlink, so edits there are live.
#
# It ends with `chrome-tab doctor`, which says whether PyObjC is installed for your
# python3 (without it the focus guard is on a slower path) and whether ~/.local/bin
# is on your PATH.
#
# The guard hook is optional and separate: it blocks `open <file>.html` in Bash
# so Claude can't fall back to the focus-stealing habit. Install it only if you
# want that enforced.

set -e
here=$(cd "$(dirname "$0")" && pwd)
bindir="${HOME}/.local/bin"

case "$(uname -s)" in
  Darwin) ;;
  *) echo "chrome-tab requires macOS (it drives Chrome via AppleScript)." >&2; exit 1 ;;
esac

mkdir -p "$bindir"
for f in chrome-tab block-bare-open.sh block-bare-open.py install-hook.py; do
  if [ -f "$here/$f" ]; then chmod +x "$here/$f"; fi
done

case "$here" in
  */plugins/cache/*)
    rm -f "$bindir/chrome-tab"
    cat > "$bindir/chrome-tab" <<EOF
#!/usr/bin/env python3
# chrome-tab launcher (written by install.sh) - do not edit; re-run install.sh instead.
# Runs the chrome-tab copy Claude Code has installed (per installed_plugins.json), so a
# plugin update takes effect without touching this file. Falls back to the highest
# non-orphaned version in the plugin cache, then to the copy this was installed from.
import json, os, re, sys
from pathlib import Path

FROZEN = "$here/chrome-tab"
REL = Path("skills") / "chrome-tab" / "scripts" / "chrome-tab"


def cfg():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))


def installed():
    try:
        data = json.loads((cfg() / "plugins" / "installed_plugins.json").read_text())
        plugins = data.get("plugins", data) if isinstance(data, dict) else {}
        for key, entries in plugins.items():
            if key.split("@", 1)[0] != "chrome-tab":
                continue
            for e in entries if isinstance(entries, list) else [entries]:
                ip = e.get("installPath") if isinstance(e, dict) else None
                if ip and (Path(ip) / REL).exists():
                    return Path(ip) / REL
    except Exception:
        pass

    def key(c):
        d = c.parents[3]
        nums = tuple(int(x) for x in d.name.split(".")) if re.fullmatch(r"[0-9]+([.][0-9]+)*", d.name) else ()
        try:
            mtime = d.stat().st_mtime
        except OSError:
            mtime = 0.0
        return (nums, mtime)

    cands = list((cfg() / "plugins" / "cache").glob("*/chrome-tab/*/" + REL.as_posix()))
    live = [c for c in cands if not (c.parents[3] / ".orphaned_at").exists()]
    cands = live or cands
    return max(cands, key=key) if cands else None


target = installed() or Path(FROZEN)
os.execve(sys.executable, [sys.executable, str(target), *sys.argv[1:]],
          dict(os.environ, CHROME_TAB_NO_FORWARD="1"))
EOF
    chmod +x "$bindir/chrome-tab"
    echo "Installed launcher $bindir/chrome-tab — it runs the installed plugin copy, so future"
    echo "\`claude plugin update\` runs need no re-install."
    ;;
  *)
    ln -sf "$here/chrome-tab" "$bindir/chrome-tab"
    echo "Linked $bindir/chrome-tab -> $here/chrome-tab"
    ;;
esac

if [ "$1" = "--hook" ]; then
  python3 "$here/install-hook.py"
else
  echo
  echo "Optional: enforce it with a hook so bare \`open file.html\` is refused —"
  echo "  python3 \"$here/install-hook.py\"        (--dry-run to preview, --remove to undo)"
fi

echo
python3 "$here/chrome-tab" doctor || true
