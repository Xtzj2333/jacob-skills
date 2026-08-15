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

## Re-opening a file that is already open

It reloads that tab in place rather than piling up duplicates — **unless the user is reading it right now** (Chrome frontmost + that window on top + that tab active), in which case the new render opens in a tab beside their copy and their view is left alone.

Form state is never at risk either way: pages built with `decision-forms-html` persist to `localStorage` on every keystroke and restore on load. What a reload costs is scroll position and open `<details>`.

## Optional guard hook

`scripts/install-hook.py` adds a `PreToolUse`/`Bash` hook that refuses `open <file>.html` and names the replacement, so the habit can't survive a session that never read this skill. It exits in shell (~3.6 ms) unless the command contains "open" at all. It ignores `open -a`/`-b`, folders, PDFs, `openssl`, and `chrome-tab open`. `--remove` undoes it; it backs up `settings.json` first.

## Limits

- macOS + Google Chrome only; the tool exits with a clear error elsewhere.
- Creating a *new* window unavoidably raises it — the tool restores both the previous frontmost app and Chrome's window order afterwards, but there is a brief flash.
- Reuse searches only the target window; a copy dragged to another window won't refresh.
