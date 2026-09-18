---
name: chrome-tab
description: Use when opening an HTML file or URL in Chrome for the user on macOS — a rendered report, a local deliverable, any file:// page — or when the user asks which Chrome window something is in, or says pages open in the wrong window, jump the screen, or steal focus while they are working. macOS with Google Chrome only.
---

# chrome-tab

`open file.html` has three faults on macOS: it hands the file to whichever Chrome window was used *last*, it pulls Chrome in front of whatever the user was doing, and the tab carries no marker of which session opened it. `open -g` does **not** fix the focus steal — Chrome activates itself regardless (measured).

`chrome-tab` drives Chrome's AppleScript interface instead, which can add a tab to a *named* window without calling `activate`. With its optional **helper extension** running, it does the navigating through the extension API instead: tab groups, a real tab move, and no request to raise Chrome at all.

## Install

```bash
sh scripts/install.sh          # puts chrome-tab on PATH; --hook also installs the guard
chrome-tab doctor              # everything that fails silently, each with its fix
chrome-tab list                # confirm it works
```

**From the plugin** (`/plugin install chrome-tab@jacob-skills`), run the installer once from the
newest cached copy — the glob can match two version directories after an update, and `sh` would
run the first, so pick the highest:

```bash
sh "$(ls ~/.claude/plugins/cache/*/chrome-tab/*/skills/chrome-tab/scripts/install.sh | sort -V | tail -1)"
```

From a plugin cache the installer writes a *launcher*, not a symlink: it runs whichever copy
Claude Code has installed (`installed_plugins.json`), so after this one run
`claude plugin update chrome-tab@jacob-skills` is all a later update needs. Before 0.1.3 the PATH
entry was a symlink into the versioned cache directory, so an update reported success while the
old copy kept running (Tony, Sep 2026: 0.1.2 sat unused for two weeks). `chrome-tab doctor`
reports that state as STALE, and a stale copy hands over to the installed one by itself.

**PyObjC** makes the focus guard fast — 3 ms polls and an in-process re-activation. It ships
with Anaconda's python, not with Apple's or Homebrew's; without it the guard still works but
polls every 50 ms via `lsappinfo` + `open -b`, so a jump can show for a frame or two. `doctor`
prints the exact `pip install` line for whichever `python3` runs the tool (Homebrew's needs
`--break-system-packages`), and `open` says so on every run that took the slow path.

## Use

```bash
chrome-tab open report.html                       # the matching tab group, wherever it is; else a new one in the home window
chrome-tab open report.html --group "mail archive"  # name the topic when the file's folder isn't it
chrome-tab list                                   # windows by name, with their tab groups
chrome-tab open report.html --window "educ"       # a window the user keeps or named (rare)
chrome-tab open report.html --activate            # ...and bring Chrome forward
chrome-tab name "#3" "mail archive"               # label an unnamed window
chrome-tab home                                   # show the home window; `home NAME` sets it
chrome-tab where 940163608                        # which window (and group) holds a tab
chrome-tab move 940163608 --window "FE"           # move a tab for real (helper only)
```

Run `chrome-tab --help` for the rest (`--bind`, `--new-window`, `--color`, `--no-reuse`, `--force-reload`, `--no-select`, `--version`).

## The two conventions that matter

**Address windows by name, never by numeric id.** Chrome exposes the label set by right-clicking the tab strip → "Name window…" as a read/write `given name` property. `chrome-tab list` shows it. Asking "the `educ` window or the `LLM and Culture` one?" beats quoting `940044950`. Offer to name an unnamed window rather than describing it by its tabs.

**Every page lands in a tab group, and the tool picks it (0.4.0).** It takes a topic name — `--group`, else the `--window` name given on this call, else the group this session used before, else the file's project folder (`<project>/reports (claude)/…`), else the current folder — and matches it loosely against the groups in every window: same words ignoring case and punctuation, or every word of the shorter name starting a word of the longer one ("mail archive" → "Mail archive", "Furniture" → "Furnitures"; short names like "FE" only match exactly). A match wins wherever it lives, so a page for "FE4" goes into the FE window's FE4 group. No match: a new group in the home window (default "Claude sessions"; `chrome-tab home NAME` changes it), coloured by name. Claude-in-Chrome's own groups ("Claude", "✅Claude") are never matched or added to. The output says which group and why; when it made a new group it lists the others in that window, and re-running with `--group` moves the page (Chrome drops the emptied group). So: pass `--group` when the file's folder isn't the topic, reusing a name from `chrome-tab list` when one fits; leave `--window` for a window the user keeps or names, and `--new-window` for when they ask for one. Until 0.2.0 an unknown `--window` name made a brand-new window: 76 of them in five weeks on one Mac.

Without the helper there are no groups: the page goes to the window only, and the output says groups were skipped. AppleScript has no tab-group class.

## The helper extension (optional)

```bash
chrome-tab helper install     # copies it to ~/.claude/chrome-tab-helper, registers its host with Chrome
chrome-tab helper status      # installed? loaded? answering? — each with its fix
```

The user loads it once. Open chrome://extensions, switch on Developer mode, click "Load unpacked", and pick `~/.claude/chrome-tab-helper/extension`. Its id is fixed by the `key` in its manifest, so the host registration always matches. From then on Chrome starts a small native-messaging host (`helper/chrome_tab_host.py`) that serves a Unix socket only this user can open. `chrome-tab` asks the extension to open, reuse, group and move tabs.

- **What it changes.** Tabs are added in the background by the extension, with nothing asking macOS to bring Chrome forward. Window names are read from the Chrome that runs the helper, by process id. That means a headless copy of Chrome launched by another job can't answer in its place. Groups and a real `move` become possible. AppleScript's `move` closes the tab and opens a blank one.
- **What it can't see.** Window names: the extension API has no field for them. `chrome-tab` reads them through Apple events and matches by id, and the ids are the same numbers on both sides.
- **Without it.** Everything falls back to the AppleScript path above and says what it couldn't do.
- **Tests.** `scripts/test-helper.py` and `scripts/test-cic-hook.py` run the real extension and host in a throwaway headless Chrome for Testing (set `CHROME_TAB_TEST_BROWSER`). Any browser launched for testing needs `--use-mock-keychain --password-store=basic`, or macOS puts a keychain password dialog in front of the user.

## Claude-in-Chrome tabs beside the session's pages (optional hook)

The Claude-in-Chrome extension puts each session's tab group in whichever window had focus last, and it has no setting for this. `scripts/install-cic-hook.py` (the user runs it; it edits `settings.json`) adds a PostToolUse hook, `chrome-tab hook claude-in-chrome`, on `tabs_context_mcp`, `navigate` and `browser_batch`. When one of those reports a brand-new one-tab session group, the hook has the helper move the whole group **right after the group this session's pages went to** (the session memory `chrome-tab open` writes), else into the browse window, which defaults to the home window (`browse_window` in `~/.config/chrome-tab/config.json` overrides). The browsing group can't merge into the topic group: the extension checks every tool call against its own group. `tabGroups.move` keeps the group's id, so the session keeps working. The hook's guardrails:
- it moves only a group the tool just reported, holding exactly that one tab, and only once;
- it never moves an active tab and never creates a window;
- if the browse window isn't open, the tab stays where it is and the session is told in one line.

Decisions are logged to `~/.claude/chrome-tab-helper/hook.log`.

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
- Setting a tab's URL by AppleScript *asks* macOS to bring Chrome forward — new window or existing one, twice, the second time ~0.4 s later (creating an empty tab and reloading do not). Whether macOS grants it depends on the user: measured 2026-08-20 (user idle 200+ s, Slack in front) it was granted every time; measured 2026-09-03 (user had touched the keyboard 3–20 s earlier) it was never granted, and neither was an `open -b` from the tool. So the flash happens when the user is reading, not typing. The tool cannot prevent the request; it undoes it: a guard thread (PyObjC, 3 ms poll, in-process re-activation; falls back to `lsappinfo` + `open -b`) runs from before the navigation until 1.6 s after and puts the user's app back the instant Chrome appears. Until 2026-09-03 the loop was 100 ms polling + `open -b` *after* the call, i.e. a visible 100–400 ms blink twice per page — that was the "takes me there and back" the user reported. The closing lines are measurements: how many times Chrome came forward and for how long, plus "(focus left where it was)"; anything else is a bug report, and a `guard` line goes to `~/.claude/chrome-tab-focus.log` whenever Chrome came forward at all. The helper extension (above) is that path with *no* request: with it running, pages are added by the extension and the guard only measures.
- Regression check without a human at the keyboard: `scripts/focus-regression.py` waits until the user has been idle 4 min, then runs the raw navigations and the real tool on every path (needs PyObjC and Slack; aborts the moment the idle clock drops). It still needs the user's fresh consent to run — see the `ask-before-taking-the-screen` rule.
- Reuse searches only the target window; a copy dragged to another window won't refresh.
