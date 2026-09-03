---
name: chrome-tab
description: Use when opening an HTML file or URL in Chrome for the user on macOS — a rendered report, a local deliverable, any file:// page — or when the user asks which Chrome window something is in, or says pages open in the wrong window, jump the screen, or steal focus while they are working. macOS with Google Chrome only.
---

# chrome-tab

`open file.html` has three faults on macOS: it hands the file to whichever Chrome window was used *last*, it pulls Chrome in front of whatever the user was doing, and the tab carries no marker of which session opened it. `open -g` does **not** fix the focus steal — Chrome activates itself regardless (measured).

`chrome-tab` drives Chrome's AppleScript interface instead, which can add a tab to a *named* window without calling `activate`.

## Install

```bash
sh scripts/install.sh          # symlink onto PATH; --hook also installs the guard
chrome-tab list                # confirm it works
```

## Use

```bash
chrome-tab list                                   # windows by name, not by opaque id
chrome-tab open report.html --window "educ"       # place it, quietly
chrome-tab open report.html --activate            # ...and bring Chrome forward
chrome-tab name "#3" "mail archive"               # label an unnamed window
```

Run `chrome-tab --help` for the rest (`--bind`, `--new-window`, `--no-reuse`, `--force-reload`, `--no-select`).

## The two conventions that matter

**Address windows by name, never by numeric id.** Chrome exposes the label set by right-clicking the tab strip → "Name window…" as a read/write `given name` property. `chrome-tab list` shows it. Asking "the `educ` window or the `LLM and Culture` one?" beats quoting `940044950`. Offer to name an unnamed window rather than describing it by its tabs.

**One reused window per project/topic.** The window *is* the grouping. Chrome's coloured tab groups cannot be scripted at all — they are an extension-only API, and the Claude-in-Chrome extension refuses `file://` URLs — so a named window is the only per-session grouping available to local files.

## Nothing the user is looking at changes

That is the rule the tool enforces (since 2026-09-03): not their app, not Chrome's window order, not the tab of a window they have in front, not whether a window is minimized. A page opens in the background and is there when they look. Concretely: if Chrome is frontmost and the target window is the one on top, a new tab is added *behind* the tab they are on and a reload doesn't switch tabs; otherwise the new or reloaded tab is left selected so it is what they see when they come to that window. A minimized target is re-minimized right after (Chrome un-minimizes it on navigation — measured). `--activate` is the explicit opt-out.

## Re-opening a file that is already open

It reloads that tab in place rather than piling up duplicates — **unless the user is reading it right now** (Chrome frontmost + that window on top + that tab active), in which case the new render opens in a tab behind their copy and their view is left alone.

Form state is never at risk either way: pages built with `decision-forms-html` persist to `localStorage` on every keystroke and restore on load. What a reload costs is scroll position and open `<details>`.

## Optional guard hook

`scripts/install-hook.py` adds a `PreToolUse`/`Bash` hook that refuses `open <file>.html` and names the replacement, so the habit can't survive a session that never read this skill. It exits in shell (~3.6 ms) unless the command contains "open" at all. It ignores `open -a`/`-b`, folders, PDFs, `openssl`, and `chrome-tab open`. `--remove` undoes it; it backs up `settings.json` first.

## Optional restore-focus hooks (experimental — recommended OFF since 2026-09-03)

**Verdict 2026-09-03:** remove them (`scripts/install-focus-hook.py --remove`, run by the user — done on this Mac 2026-09-03 02:22). They answered their question on 2026-08-20 (the extension never moves focus). Left installed, their only remaining effect was on the user: five `RESTORED` firings 27 Aug–1 Sep, every one within a minute of a `chrome-tab open` in the same session — the user had walked into Chrome to read the page just opened, and the Stop hook "restored" them to the app they had been in before. The rest of this section is the history.

`scripts/install-focus-hook.py` adds a second, separate pair: `PreToolUse` on
`mcp__claude-in-chrome__.*` records where the user was before Claude browses, and `Stop` puts them
back — app, Chrome window, and tab index. It acts only when it is confident (nothing to undo if the
user isn't in Chrome at end of turn, or was already in Chrome when Claude started); every decision is
logged under `CHROME_TAB_FOCUS_DEBUG=1`.

**Status: unproven.** Measured 2026-08-15 on a quiet machine, no browser operation stole focus at all
— not tab-group creation, navigation, or screenshots. Earlier readings that suggested otherwise were
contaminated by the user's own clicking. So install it as an *instrument* (does the steal ever happen
in real use?) rather than as a known fix. It cannot distinguish "the extension pulled you into Chrome"
from "you walked into Chrome yourself", so it will occasionally put you back when you didn't want it.

A `RESTORED` in the log is a **candidate**, not a finding: anything else that drives app focus —
another session's AppleScript `activate`, `open -a`, a screen recorder, or `chrome-tab` itself —
produces the same line. `scripts/focus-log-report.py` checks each RESTORED against the session
transcripts for exactly that and says whether it is admissible. The one catch so far (2026-08-16)
turned out to be `chrome-tab`'s own add-tab path, fixed 2026-08-20 — the extension has never been
seen to move focus across two controlled runs (`scripts/focus-probe.sh` is the probe used).

A `restore-focus.sh` wrapper exits in ~5.7 ms when no snapshot is pending — worth having because the
`Stop` half has no matcher and so runs on every turn of every session.

## Limits

- macOS + Google Chrome only; the tool exits with a clear error elsewhere.
- Setting a tab's URL by AppleScript *asks* macOS to bring Chrome forward — new window or existing one, twice, the second time ~0.4 s later (creating an empty tab and reloading do not). Whether macOS grants it depends on the user: measured 2026-08-20 (user idle 200+ s, Slack in front) it was granted every time; measured 2026-09-03 (user had touched the keyboard 3–20 s earlier) it was never granted, and neither was an `open -b` from the tool. So the flash happens when the user is reading, not typing. The tool cannot prevent the request; it undoes it: a guard thread (PyObjC, 3 ms poll, in-process re-activation; falls back to `lsappinfo` + `open -b`) runs from before the navigation until 1.6 s after and puts the user's app back the instant Chrome appears. Until 2026-09-03 the loop was 100 ms polling + `open -b` *after* the call, i.e. a visible 100–400 ms blink twice per page — that was the "takes me there and back" the user reported. The closing lines are measurements: how many times Chrome came forward and for how long, plus "(focus left where it was)"; anything else is a bug report, and a `guard` line goes to `~/.claude/chrome-tab-focus.log` whenever Chrome came forward at all. A path with *no* request would need a Chrome extension (extensions add background tabs to a chosen window natively); not built.
- Regression check without a human at the keyboard: `scripts/focus-regression.py` waits until the user has been idle 4 min, then runs the raw navigations and the real tool on every path (needs PyObjC and Slack; aborts the moment the idle clock drops). It still needs the user's fresh consent to run — see the `ask-before-taking-the-screen` rule.
- Reuse searches only the target window; a copy dragged to another window won't refresh.
