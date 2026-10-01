---
name: chrome-tab
description: Use when opening an HTML file or URL in Chrome for the user on macOS — a rendered report, a local deliverable, any file:// page — or when the user asks which Chrome window something is in, or says pages open in the wrong window, jump the screen, or steal focus while they are working. macOS with Google Chrome only.
---

# chrome-tab

`chrome-tab open <file>` puts a page into the matching Chrome tab group without bringing Chrome forward or changing the tab any window shows. Use it instead of `open file.html`, which lands in whichever window was used last and steals focus (`open -g` doesn't help).

## Install

```bash
sh scripts/install.sh          # puts chrome-tab on PATH; --hook also installs the guard
chrome-tab doctor              # what's missing, each with its fix
```

From the plugin, run the installer once from the newest cached copy; after that, `claude plugin update chrome-tab@jacob-skills` is all an update needs:

```bash
sh "$(ls ~/.claude/plugins/cache/*/chrome-tab/*/skills/chrome-tab/scripts/install.sh | sort -V | tail -1)"
```

## Use

```bash
chrome-tab open report.html                       # the matching tab group, wherever it is; else a new one
chrome-tab open report.html --group "mail archive"  # name the topic when the file's folder isn't it
chrome-tab list                                   # windows by name, with their tab groups
chrome-tab open report.html --window "educ"       # a window the user keeps or named (rare)
chrome-tab open report.html --activate            # ...and bring Chrome forward, showing the page
chrome-tab open report.html --select              # ...and show it in its window, Chrome left where it is
chrome-tab name "#3" "mail archive"               # label an unnamed window
chrome-tab home                                   # show the home window; `home NAME` sets it
chrome-tab where 940163608                        # which window (and group) holds a tab
chrome-tab move 940163608 --window "FE"           # move a tab for real (helper only)
```

Run `chrome-tab --help` for the rest (`--bind`, `--new-window`, `--color`, `--no-reuse`, `--force-reload`, `--version`).

## Two conventions

**Name windows, not ids.** `chrome-tab list` shows windows by their given name (right-click the tab strip → Name window…). Ask "the *educ* window or *LLM and Culture*?", never quote an id; offer to name an unnamed window (`chrome-tab name`).

**The tool picks the tab group.** The topic is `--group` (or the `--window` name), else this session's earlier group, else the file's project folder or the current folder. A group matching it wins wherever it is; else a new group goes to the window named for the project, else to the home window. Pass `--group` when the folder isn't the topic, reusing a name from `chrome-tab list`. Use `--window` only for a window the user names, `--new-window` only when asked. The output says which group it chose and why.

## The helper extension (optional)

Gives tab groups and fully silent opens. `chrome-tab helper install`, then the user loads `~/.claude/chrome-tab-helper/extension` once (chrome://extensions → Developer mode → Load unpacked). `chrome-tab helper status` names what's wrong and the fix. Without it, pages go to the window only and the output says groups were skipped.

## Claude-in-Chrome tabs beside the session's pages (optional hook)

`scripts/install-cic-hook.py` (the user runs it; it edits `settings.json`) moves each new Claude-in-Chrome tab group beside this session's pages, else into the window named for the session's project folder, else into the home window. It never moves a tab the user is looking at. Decisions go to `~/.claude/chrome-tab-helper/hook.log`.

## Pages open in the background

chrome-tab never brings Chrome forward, changes the tab any window shows, or leaves a minimized window restored. `--select` (show it in its window) and `--activate` (also bring Chrome forward) are only for when the user asks to be taken there.

So when telling the user a page is ready, **say where it landed**: the window and group from the output ("in *miscellaneous*, group *Proseminar*").

If the output says "⚠ that window switched to this page on its own", that is a chrome-tab bug: tell the user.

## Re-opening a file that is already open

It reloads that tab in place, unless the user is reading it right now; then the new render goes in a tab behind theirs. A reload loses scroll position, not form answers (decision-forms pages keep them).

## Optional guard hook

`scripts/install-hook.py` adds a hook that refuses `open <file>.html` and names the replacement. `--remove` undoes it.

## Limits

- macOS + Google Chrome only.
- Without the helper, AppleScript asks macOS to raise Chrome on each navigation; a guard puts the user's app back at once (fastest with PyObjC, which `doctor` explains). The output says whether Chrome came forward.
- Reuse looks only in the target window: a copy dragged elsewhere won't be refreshed.
