# chrome-tab: developer notes

`SKILL.md` is for using the tool. This file is for changing it: what each file does, where the
tool keeps state, how to test without touching the user's Chrome, how to release, and the facts
about Chrome that took a day each to learn. Current version: 0.5.0 (2026-09-20).

## Files

| File | What it is |
|---|---|
| `scripts/chrome-tab` | The whole CLI: one Python 3 file, stdlib only (PyObjC optional, for the fast focus guard). `__version__` is near the top. |
| `helper/extension/` | The helper extension (Manifest V3; `tabs`, `tabGroups`, `nativeMessaging`, `alarms`). `background.js` holds `HANDLERS`: `ping`, `windows`, `open`, `createWindow`, `tab`, `move`, `moveGroup`, `reload`. Its id, `fjfhflgjjbjjlkbfhjegbnbommoiffie`, is fixed by the public `key` in `manifest.json`. It's loaded unpacked, so no private key exists or is needed. |
| `helper/chrome_tab_host.py` | The native-messaging host that Chrome starts for the extension. It relays between Chrome (stdin/stdout, 4-byte length + JSON) and a Unix socket (one JSON line in, one out). It answers `host` itself: its own pid, and Chrome's pid, which is its parent because the launcher `exec`s it. Nothing but framed messages may go to stdout. |
| `scripts/install.sh`, `scripts/session-check.sh` | PATH install: a symlink from a source checkout, a launcher from a plugin cache (see SKILL.md). `session-check.sh` is the plugin's SessionStart hook. |
| `scripts/install-hook.py`, `scripts/block-bare-open.{sh,py}` | Optional PreToolUse/Bash guard that refuses bare `open <file>.html`. |
| `scripts/install-cic-hook.py` | Optional PostToolUse hook for the Claude-in-Chrome mover (`chrome-tab hook claude-in-chrome`). The user runs it because it edits `settings.json`, and it backs that file up first. `--remove` undoes it. |
| `scripts/restore-focus.*`, `install-focus-hook.py`, `focus-log-report.py`, `focus-probe.sh`, `focus-regression.py` | The Aug–Sep 2026 focus-steal instruments. Retired: recommended off since 2026-09-03 and kept as the record. |
| `scripts/test-*.py` | The four test suites (below). |

## How `open` places a page

`cmd_open` asks the helper for its host facts (`helper_host`). If the helper answers, window names are read by Chrome's pid (`list_windows(pid)`, JXA `Application(pid)`) and the window/group list comes from the extension (`helper_call("windows")`). Then:

1. `topic_name()`: `--group`, else the `--window` name given on this call, else the session's remembered group, else the file's project folder (`project_of`: the parent of `reports (claude)/`, or `~/Claude/reports/<topic>/`), else the current folder, else "Claude pages".
2. `plan_placement()` (pure; `test-target.py` pins it) matches the topic against every window's groups with `group_score()`. A score of 2 means the same words. A score of 1 means every word of the shorter name, with at least four letters, starts a word of the longer one. Short names match only exactly, and Claude-in-Chrome's groups (`CIC_GROUP`) never match. A hit wins in whichever window it lives; ties go to the home window, then the session's last window. With no hit, the page gets a new group named after the topic, in the `--window` target or else the home window.
3. The helper's `open` adds or reloads the tab and puts it in the group (`putInGroup`). The tab is created inactive and **nothing selects it** (0.5.0): `select` — `--select`, implied by `--activate` — is the only path that does. `looking` (Chrome frontmost *and* this is its front window) now decides one thing only: whether an open copy may be reloaded under the user, or whether the fresh render goes in a tab beside it (`added-beside`). The reply carries `showingBefore`/`showing`, the window's shown tab either side of the call; `check_switch()` turns that into the printed "still shows the tab it did", a `tab-switch` line in the focus log if it ever changed, and a "run chrome-tab helper install" note when the loaded extension is too old to report it. Without the helper, the AppleScript path puts the page in the window only, the output says groups were skipped, and since `make new tab` selects what it makes, `place_tab` puts the previously shown tab straight back.
4. `write_binding()` records the session's window and group, which is what the next flagless open and the Claude-in-Chrome hook read.

## The Claude-in-Chrome hook

`cmd_hook` runs as a PostToolUse hook whose matcher lists three tools (`tabs_context_mcp`, `navigate`, `browser_batch`), so Claude Code starts it for nothing else. `fresh_groups()` finds a brand-new session group in any of the three result shapes: `tabs_context_mcp`'s JSON block, the block appended to a `navigate` without a tab id, or `[tabs_context_mcp] {…}` lines in a batch. `claim_claude_tab()` then applies the guardrails: only a group this call reported, holding exactly that one tab, once (`moved.json`, 7 days), never an active tab, never a new window. `browse_target()` picks the window of the session's remembered group and anchors right after that group; otherwise it picks the browse window, which defaults to the home window. The move is `moveGroup` with `afterGroupId`, followed by a poll until the tab sits in a group in the target window again. Every decision goes to `hook.log`.

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
