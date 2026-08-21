#!/bin/sh
# One-line reading of the things the controlled focus test cares about:
#   idle=<seconds since last keyboard/mouse input>  front=<frontmost app>
#   chromefront=<id of Chrome's front window>        saver=<1 if screen saver running>
# Used after every browser operation during a hands-off run. Idle time must rise
# monotonically through the run — a drop means a human touched the machine and
# the run is contaminated.
idle=$(( $(ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print $NF; exit}') / (1000 * 1000 * 1000) ))
front=$(lsappinfo info -only name "$(lsappinfo front)" 2>/dev/null | sed -E 's/.*="(.*)"/\1/')
cw=$(osascript -e 'tell application "Google Chrome" to if (count of windows) > 0 then return id of front window' 2>/dev/null)
saver=0; pgrep -x ScreenSaverEngine >/dev/null 2>&1 && saver=1
printf 'idle=%s front=%s chromefront=%s saver=%s\n' "$idle" "$front" "${cw:-none}" "$saver"
