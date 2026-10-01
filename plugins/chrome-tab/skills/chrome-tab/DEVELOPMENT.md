# chrome-tab: developer notes

`SKILL.md` is for using the tool. This file is for changing it: what each file does, where the
tool keeps state, how to test without touching the user's Chrome, how to release, and the facts
about Chrome that took a day each to learn. Current version: 0.6.0 (2026-09-30).

## Files

| File | What it is |
|---|---|
| `scripts/chrome-tab` | The whole CLI: one Python 3 file, stdlib only (PyObjC optional, for the fast focus guard). `__version__` is near the top. |
| `helper/extension/` | The helper extension (Manifest V3; `tabs`, `tabGroups`, `nativeMessaging`, `alarms`). `background.js` holds `HANDLERS`: `ping`, `windows`, `open`, `createWindow`, `tab`, `move`, `moveGroup`, `reload`. Its id, `fjfhflgjjbjjlkbfhjegbnbommoiffie`, is fixed by the public `key` in `manifest.json`. It's loaded unpacked, so no private key exists or is needed. |
| `helper/chrome_tab_host.py` | The native-messaging host that Chrome starts for the extension. It relays between Chrome (stdin/stdout, 4-byte length + JSON) and a Unix socket (one JSON line in, one out). It answers `host` itself: its own pid, and Chrome's pid, which is its parent because the launcher `exec`s it. Nothing but framed messages may go to stdout. |
| `scripts/install.sh`, `scripts/session-check.sh` | PATH install: a symlink from a source checkout, a launcher from a plugin cache (see Background below). `session-check.sh` is the plugin's SessionStart hook. |
| `scripts/install-hook.py`, `scripts/block-bare-open.{sh,py}` | Optional PreToolUse/Bash guard that refuses bare `open <file>.html`. |
| `scripts/install-cic-hook.py` | Optional PostToolUse hook for the Claude-in-Chrome mover (`chrome-tab hook claude-in-chrome`). The user runs it because it edits `settings.json`, and it backs that file up first. `--remove` undoes it. |
| `scripts/restore-focus.*`, `install-focus-hook.py`, `focus-log-report.py`, `focus-probe.sh`, `focus-regression.py` | The Aug–Sep 2026 focus-steal instruments. Retired: recommended off since 2026-09-03 and kept as the record. |
| `scripts/test-*.py` | The four test suites (below). |

## How `open` places a page

`cmd_open` asks the helper for its host facts (`helper_host`). If the helper answers, window names are read by Chrome's pid (`list_windows(pid)`, JXA `Application(pid)`) and the window/group list comes from the extension (`helper_call("windows")`). Then:

1. `topic_name()`: `--group`, else the `--window` name given on this call, else the session's remembered group, else the file's project folder (`project_of`: the parent of `reports (claude)/`, or `~/Claude/reports/<topic>/`), else the current folder, else "Claude pages".
2. `plan_placement()` (pure; `test-target.py` pins it) matches the topic against every window's groups with `group_score()`. A score of 2 means the same words. A score of 1 means every word of the shorter name, with at least four letters, starts a word of the longer one. Short names match only exactly or as the other name's initials (`is_initials`: "FE" ⇔ "Free Expression"), and Claude-in-Chrome's groups (`CIC_GROUP`) never match. A hit wins in whichever window it lives; ties go to the home window, then the session's last window. With no hit, the page gets a new group named after the topic, in the `--window` target, else the window named for a folder the file or cwd sits in (`project_window`: exact name or initials only), else the home window.
3. The helper's `open` adds or reloads the tab and puts it in the group (`putInGroup`). The tab is created inactive and **nothing selects it** (0.5.0): `select` — `--select`, implied by `--activate` — is the only path that does. `looking` (Chrome frontmost *and* this is its front window) now decides one thing only: whether an open copy may be reloaded under the user, or whether the fresh render goes in a tab beside it (`added-beside`). The reply carries `showingBefore`/`showing`, the window's shown tab either side of the call; `check_switch()` turns that into the printed "still shows the tab it did", a `tab-switch` line in the focus log if it ever changed, and a "run chrome-tab helper install" note when the loaded extension is too old to report it. Without the helper, the AppleScript path puts the page in the window only, the output says groups were skipped, and since `make new tab` selects what it makes, `place_tab` puts the previously shown tab straight back.
4. `write_binding()` records the session's window and group, which is what the next flagless open and the Claude-in-Chrome hook read.

## The Claude-in-Chrome hook

`cmd_hook` runs as a PostToolUse hook whose matcher lists three tools (`tabs_context_mcp`, `navigate`, `browser_batch`), so Claude Code starts it for nothing else. `fresh_groups()` finds a brand-new session group in any of the three result shapes: `tabs_context_mcp`'s JSON block, the block appended to a `navigate` without a tab id, or `[tabs_context_mcp] {…}` lines in a batch. `claim_claude_tab()` then applies the guardrails: only a group this call reported, holding exactly that one tab, once (`moved.json`, 7 days), never an active tab, never a new window. `browse_target()` picks the window of the session's remembered group and anchors right after that group; otherwise the window named for the session's cwd (`project_window`), then the browse window, which defaults to the home window. The move is `moveGroup` with `afterGroupId`, followed by a poll until the tab sits in a group in the target window again. If the target window isn't open, the tab stays where it is and the session is told in one line. Every decision goes to `hook.log`.

## State on disk

| Path | What |
|---|---|
| `~/.claude/chrome-sessions/<session-id>.json` | Per-session binding: `{session, window_name, group, cwd}` (`CHROME_TAB_STATE_DIR`). |
| `~/.config/chrome-tab/config.json` | `home_window` (`chrome-tab home NAME`) and `browse_window`. Env overrides: `CHROME_TAB_HOME_WINDOW`, `CHROME_TAB_BROWSE_WINDOW`. |
| `~/.claude/chrome-tab-helper/` | Written by `chrome-tab helper install`: the extension copy Chrome loads, the host, the `host` launcher, `bridge.sock` (0600, in a 0700 folder), `host.log`, `hook.log`, `moved.json`. |
| `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.jacob_skills.chrome_tab.json` | The host registration (`CHROME_TAB_NMH_DIR`). |
| `~/.claude/chrome-tab-focus.log` | A `guard` line whenever Chrome came forward during an open. |

Other environment variables: `CHROME_TAB_HELPER_DIR` and `CHROME_TAB_SOCKET` move the helper files; `CHROME_TAB_NO_APPLESCRIPT=1` makes every Apple-event call fail (the tests use it); `CHROME_TAB_NO_FORWARD` stops a stale copy handing over to the installed one; `CHROME_TAB_TEST_BROWSER` and `CHROME_TAB_SLOW_TESTS` are for the tests.

## Testing

```bash
set -e; cd chrome-tab
for t in test-target test-pickup test-cic-hook test-helper; do python3 scripts/$t.py; done
```

- `test-target.py` (placement logic) and `test-pickup.py` (install and update pickup; uses a throwaway `$HOME`) never touch Chrome.
- `test-cic-hook.py` and `test-helper.py` each have an end-to-end part that loads the real extension and host in a throwaway headless **Chrome for Testing** with its own profile and `NativeMessagingHosts`. They find it through `$CHROME_TAB_TEST_BROWSER`, or under `~/.cache/chrome-tab-test/` or `~/.cache/puppeteer/`. To install one: `npx @puppeteer/browsers install chrome@stable --path ~/.cache/chrome-tab-test`. Without it those parts skip and say so. A skip is not a pass.
- `CHROME_TAB_SLOW_TESTS=1` adds the host-restart test (about two minutes).
- Check each exit code. A pipeline like `python3 scripts/test-x.py | tail -1 && next` keeps going after a failure.

Rules for any browser you launch while testing:
- Pass `--use-mock-keychain --password-store=basic`. Without them, macOS shows the user a "Chromium Safe Storage" keychain password dialog, and the answer is Deny.
- Kill only processes whose `--user-data-dir` is your own scratch profile. Other jobs run Chrome for Testing too, so never `pkill` by app name.
- Never launch the user's `Google Chrome.app` headless. AppleScript's `tell application "Google Chrome"` may then answer from that copy. (With the helper running, chrome-tab reads by pid and is immune, but other tools aren't.)
- Never script tab moves or navigation in the user's Chrome with AppleScript or JXA to "check something" (see below).

## Releasing

1. Bump `__version__` in `scripts/chrome-tab`, and `version` in `helper/extension/manifest.json` when the extension or host changed (`helper status` compares the running extension with the files).
2. Run all four suites, with Chrome for Testing present.
3. Merge through a PR in the skills repo.
4. On a machine where the helper is loaded, `chrome-tab helper install` copies the new files and asks the running extension to reload itself, with no click. `chrome-tab helper status` should then show the new version running.
5. Publish to the marketplace (the author's `jacob-skills`). Sync the skill folder, then on the marketplace side bump `plugins/chrome-tab/.claude-plugin/plugin.json` and add a CHANGELOG entry written for someone who only runs `claude plugin update`. Touch `SKILLS_OVERVIEW.md` and the README when behaviour changed. The plugin's `hooks/hooks.json` registers only the SessionStart check. The Claude-in-Chrome hook stays opt-in, because it only makes sense with the helper loaded.
6. Keep this folder's wording generic ("the user"), because the marketplace copy is public.

## Background moved out of SKILL.md (0.6.0)

On 2026-09-30 SKILL.md was cut to what a session needs to use the tool (about 3,800 → 1,150 tokens per
load). The history and detail it carried are kept here, verbatim, except where a section above already
says the same thing.

### Why not `open`

`open file.html` has three faults on macOS: it hands the file to whichever Chrome window was used *last*, it pulls Chrome in front of whatever the user was doing, and the tab carries no marker of which session opened it. `open -g` does **not** fix the focus steal — Chrome activates itself regardless (measured).

`chrome-tab` drives Chrome's AppleScript interface instead, which can add a tab to a *named* window without calling `activate`. With its optional **helper extension** running, it does the navigating through the extension API instead: tab groups, a real tab move, and no request to raise Chrome at all.

### Install from a plugin cache

The install line in SKILL.md sorts with `sort -V | tail -1` because the glob can match two version directories after an update, and `sh` would run the first.

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

### Placement history

Until 0.2.0 an unknown `--window` name made a brand-new window: 76 of them in five weeks on one Mac.

### Nothing the user is looking at changes

That is the rule the tool enforces (since 2026-09-03): not their app, not Chrome's window order, not whether a window is minimized, and — since 0.5.0 — **not which tab any window is showing**. A page is always added in the background, inside its tab group, and waits there; the output names the window and the group so it can be found. A minimized target is re-minimized right after (Chrome un-minimizes it on navigation — measured).

Until 0.5.0 the rule protected only the window in front: a page opened while the user was in *another* window (or in another app, then walking into Chrome) was left selected there, so the tab strip they came back to had changed under them. That was the "sometimes it jumps to the new tab" the user reported on 2026-09-20. Creating the tab group is not what moved them — measured the same day, `tabs.group`, `tabGroups.move` and a background `tabs.create` all leave the shown tab alone; the one and only cause was the explicit select.

### The guard hook

`scripts/install-hook.py` adds a `PreToolUse`/`Bash` hook that refuses `open <file>.html` and names the replacement, so the habit can't survive a session that never read this skill. It exits in shell (~3.6 ms) unless the command contains "open" at all. It ignores `open -a`/`-b`, folders, PDFs, `openssl`, and `chrome-tab open`. `--remove` undoes it; it backs up `settings.json` first.

### AppleScript focus (the path without the helper)

Setting a tab's URL by AppleScript *asks* macOS to bring Chrome forward — new window or existing one, twice, the second time ~0.4 s later (creating an empty tab and reloading do not). Whether macOS grants it depends on the user: measured 2026-08-20 (user idle 200+ s, Slack in front) it was granted every time; measured 2026-09-03 (user had touched the keyboard 3–20 s earlier) it was never granted, and neither was an `open -b` from the tool. So the flash happens when the user is reading, not typing. The tool cannot prevent the request; it undoes it: a guard thread (PyObjC, 3 ms poll, in-process re-activation; falls back to `lsappinfo` + `open -b`) runs from before the navigation until 1.6 s after and puts the user's app back the instant Chrome appears. Until 2026-09-03 the loop was 100 ms polling + `open -b` *after* the call, i.e. a visible 100–400 ms blink twice per page — that was the "takes me there and back" the user reported. The closing lines are measurements: how many times Chrome came forward and for how long, plus "(focus left where it was)"; anything else is a bug report, and a `guard` line goes to `~/.claude/chrome-tab-focus.log` whenever Chrome came forward at all. The helper extension (above) is that path with *no* request: with it running, pages are added by the extension and the guard only measures.

Regression check without a human at the keyboard: `scripts/focus-regression.py` waits until the user has been idle 4 min, then runs the raw navigations and the real tool on every path (needs PyObjC and Slack; aborts the moment the idle clock drops). It still needs the user's fresh consent to run — see the `ask-before-taking-the-screen` rule.

### Retired: restore-focus hooks (recommended off since 2026-09-03)

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

## Facts that took a day each to learn

- **AppleScript `move tab` destroys the tab.** In Chromium it inserts a blank New Tab and closes the original (`window_applescript.mm`). Use the helper's `move`/`moveGroup`.
- **AppleScript `set URL` asks macOS to raise Chrome twice**, about 0.4 s apart. macOS grants that only when the user has been idle a while, so a flash appears while they read, not while they type. The helper path makes no such request. `open -g` doesn't help either.
- **The extension API has no window name.** Names ("Name window…") exist only as AppleScript's `given name`. Window ids are the same numbers on both sides, so the tool joins them by id.
- **Chrome deletes a group when its last tab closes.** A session's remembered group can be gone the next time it opens a page; placement then makes a fresh group of the same name.
- **`tabGroups.move` keeps the group id**, but while the group moves, its tab reports `groupId` -1 and then comes back.
- **Nothing in the extension API selects a tab by itself** (measured 2026-09-20, headless Chrome for Testing 153): `tabs.create({active: false})`, `tabs.group()` making a brand-new group, `tabGroups.update` and `tabGroups.move` into another window all leave every window showing the tab it showed. Only `tabs.update({active: true})` moves it. So when a page "jumps to the front", look for an explicit select, not for a side effect of grouping.
- **Claude-in-Chrome** creates its session group in `chrome.windows.getLastFocused()` and titles it "Claude" ("Claude (MCP)" in older versions; ⌛/🔔/✅ prefixes from the side panel). It checks every tool call against its own group, so a page must never be added to that group. In a real browser its listener regroups a tab that moves to another window into a *new* group, so the group id changes after every cross-window move. Nothing in the hook depends on the id.
- **A PostToolUse hook gets an MCP result as a list of content blocks**, not a string. Hooks added to `settings.json` take effect in sessions that are already running (seen 2026-09-17).
- **A headless copy of the real Chrome app answers AppleScript.** That's why the host reports Chrome's pid and names are read through `Application(pid)`.
