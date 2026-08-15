#!/usr/bin/env python3
"""PreToolUse hook — stop Claude shelling out to bare `open` for an HTML file.

Why this exists
---------------
`open file.html` hands the file to whichever Chrome window was used last and
yanks the frontmost app away from you mid-task. The obvious remedy, `open -g`,
does NOT work: Chrome activates itself regardless (measured 2026-08-15).
`chrome-tab` places the tab in a named window without stealing focus.

A rule in CLAUDE.md only reaches sessions that loaded it, and only if Claude
remembers. This hook is enforced by the harness, so it also covers sessions that
started before the rule existed.

Scope is deliberately narrow. It blocks ONLY an `open` whose target is a
.html/.htm file. It leaves alone:
  - `open -a "App"` / `open -b com.foo`   (launching an application)
  - opening a folder, a PDF, an image, or any other file type
  - the word "open" appearing inside a longer command name or a quoted string

Exit 0 = allow. Exit 2 = block; stderr is fed back to Claude as the reason.
"""

import json
import re
import shlex
import sys

MSG = """BLOCKED: bare `open` on an HTML file steals the user's focus and lands the tab in
an arbitrary Chrome window. `open -g` does not fix it — Chrome activates anyway.

Use instead:
  chrome-tab open <file> --window "<name>"     # place it in a named window, quietly
  chrome-tab list                              # see windows by their given name

Convention: one reused window per project/topic. See `chrome-tab --help`.
"""

# split a command line into simple commands on ; && || | & and newlines
SPLIT = re.compile(r'(?:\|\||&&|[;&|\n])')


def offending(segment: str) -> bool:
    try:
        toks = shlex.split(segment)
    except ValueError:
        toks = segment.split()
    if not toks:
        return False

    # strip leading env assignments (FOO=bar open ...)
    i = 0
    while i < len(toks) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*=.*', toks[i]):
        i += 1
    if i >= len(toks):
        return False

    # the command itself must be `open` (allow /usr/bin/open)
    if toks[i].rsplit('/', 1)[-1] != 'open':
        return False
    args = toks[i + 1:]

    # `open -a App` / `open -b bundle` are app launches, not file opens
    for a in args:
        if re.fullmatch(r'-[a-zA-Z]*[ab]', a):
            return False

    # block only if some non-flag argument is an .html/.htm target
    return any(not a.startswith('-') and re.search(r'\.html?$', a, re.I) for a in args)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") not in (None, "Bash"):
        return 0
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if not cmd:
        return 0

    if any(offending(seg) for seg in SPLIT.split(cmd)):
        sys.stderr.write(MSG)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
