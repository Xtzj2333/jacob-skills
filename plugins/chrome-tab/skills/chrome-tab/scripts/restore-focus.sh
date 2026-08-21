#!/bin/sh
# Shell fast-path for the restore-focus hooks.
#
# The Stop half runs on EVERY turn of EVERY session, including the overwhelming
# majority that never touch Chrome. Starting Python just to discover there is
# nothing to do costs ~40 ms of that turn; a test -e in shell costs ~3 ms. So the
# no-op path — by far the common one — never reaches Python.
#
#   restore-focus.sh --snapshot   (PreToolUse, mcp__claude-in-chrome__.*)
#   restore-focus.sh --restore    (Stop)
#
# stdin carries the hook payload; --restore needs session_id from it to find the
# right state file, so on the restore path we read stdin and hand it on.

here=$(cd "$(dirname "$0")" && pwd)
dir="${HOME}/.claude/.chrome-tab-focus"

case "$1" in
  --restore)
    # Nothing pending for any session? Then this turn never browsed. Leave.
    # (A `set --` glob test would be shorter but would clobber "$@".)
    [ -d "$dir" ] || exit 0
    found=0
    for f in "$dir"/*.json; do
      [ -e "$f" ] && { found=1; break; }
    done
    [ "$found" = 1 ] || exit 0
    ;;
esac

exec python3 "$here/restore-focus.py" "$@"
