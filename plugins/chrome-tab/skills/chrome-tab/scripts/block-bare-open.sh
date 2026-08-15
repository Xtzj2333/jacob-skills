#!/bin/sh
# PreToolUse hook entry point — cheap pre-filter in front of block-bare-open.py.
#
# A PreToolUse hook with matcher "Bash" runs on EVERY Bash tool call, so its
# cost is paid by tasks that have nothing to do with Chrome. Measured on this
# Mac (100 runs, warm):
#
#   /bin/cat, spawn only ......... 1.7 ms   (floor for any hook at all)
#   this script, no "open" ....... 3.6 ms
#   invoking python directly ..... 12.5 ms
#
# So: reject the overwhelmingly common case (command contains no "open" at all)
# in shell, and only pay for the Python interpreter when the string is present
# and careful parsing is actually needed. 3.5x cheaper on the common path.
#
# Exit 0 = allow. Exit 2 = block, with the Python script's stderr as the reason.

in=$(cat)

# Fast reject: no occurrence of "open" anywhere in the payload.
case "$in" in
  *open*) ;;
  *) exit 0 ;;
esac

# "open" is present somewhere — hand off for real parsing (which correctly
# allows `chrome-tab open`, `open -a App`, `openssl`, `open file.pdf`, etc).
printf '%s' "$in" | python3 "$(dirname "$0")/block-bare-open.py"
exit $?
