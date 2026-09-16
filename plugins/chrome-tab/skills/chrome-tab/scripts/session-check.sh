#!/bin/sh
# chrome-tab SessionStart hook — registered by the *plugin* (hooks/hooks.json), never by a
# source checkout. Two jobs, both quiet when there is nothing to say:
#
#   1. Keep the PATH entry current. If ~/.local/bin/chrome-tab is missing, or is a symlink
#      into a versioned plugin-cache directory (what install.sh wrote before 0.1.3 — it goes
#      stale on every `claude plugin update`), replace it with the launcher by running this
#      copy's install.sh. A symlink to a source checkout is deliberate and is left alone.
#   2. Print what `chrome-tab doctor --quiet` finds — PyObjC missing, PATH problems — so it is
#      in front of Claude at the start of the session instead of failing silently mid-task.
#
# Always exits 0: a hook error would be noise on every session start.

here=$(cd "$(dirname "$0")" && pwd)
entry="${HOME}/.local/bin/chrome-tab"

refresh=""
if [ ! -e "$entry" ] && [ ! -L "$entry" ]; then
  refresh="installed"
elif [ -L "$entry" ]; then
  case "$(readlink "$entry")" in
    */plugins/cache/*) refresh="replaced the version-pinned symlink with" ;;
  esac
fi

if [ -n "$refresh" ]; then
  if sh "$here/install.sh" >/dev/null 2>&1; then
    echo "chrome-tab: $refresh a launcher at $entry (runs the installed plugin copy; survives updates)"
  else
    echo "chrome-tab: could not write $entry — run:  sh \"$here/install.sh\""
  fi
fi

python3 "$here/chrome-tab" doctor --quiet 2>/dev/null || true
exit 0
