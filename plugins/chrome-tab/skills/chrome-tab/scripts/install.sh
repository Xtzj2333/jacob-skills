#!/bin/sh
# Put `chrome-tab` on your PATH. Safe to re-run.
#
#   sh install.sh            # symlink into ~/.local/bin
#   sh install.sh --hook     # ...and also install the bare-`open` guard hook
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
ln -sf "$here/chrome-tab" "$bindir/chrome-tab"
chmod +x "$here/chrome-tab" "$here/block-bare-open.sh" "$here/block-bare-open.py" "$here/install-hook.py"
echo "Linked $bindir/chrome-tab -> $here/chrome-tab"

case ":${PATH}:" in
  *":${bindir}:"*) ;;
  *) echo "NOTE: $bindir is not on your PATH. Add it in ~/.zshenv:"
     echo "      export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac

if [ "$1" = "--hook" ]; then
  python3 "$here/install-hook.py"
else
  echo
  echo "Optional: enforce it with a hook so bare \`open file.html\` is refused —"
  echo "  python3 \"$here/install-hook.py\"        (--dry-run to preview, --remove to undo)"
fi

echo
echo "Try it:  chrome-tab list"
