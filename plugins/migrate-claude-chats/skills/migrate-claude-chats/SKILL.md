---
name: migrate-claude-chats
description: Use when transferring/migrating Claude Code chat history from one Mac (or user account) to another, and the moved chats fail in agent view — "Session can't start — source session ...", "session is not responding, restarting it", a crash-loop after pressing /bg or the left-arrow, or chats that resume fine in the terminal but won't background. Covers copying transcripts, re-homing them to the right project folder, and the cwd-rewrite repair that makes agent view work.
---

# Migrate Claude Code chats between Macs

## Overview

Moving a Claude Code chat to a new Mac is mostly a copy job — **except** for one non-obvious trap that breaks agent view. This skill covers the whole move and, critically, the repair.

**Core insight:** agent view (`claude agents`) re-hosts a backgrounded session **in the working directory recorded *inside* the transcript** — not where you launched it. Transcripts copied from another Mac still carry the old machine's home path (`/Users/<olduser>/...`), which doesn't exist on the new Mac. So the chat resumes fine in a terminal (you supply a live `cd`) but **crash-loops in agent view** ("session can't start / not responding"). The fix is to rewrite that recorded path.

## When to use

- Transferring chats between two Macs, or after a macOS username change.
- A moved chat **resumes in the terminal but fails in agent view** / won't `/bg`.
- You see `Session can't start — source session <path>` or `session is not responding, restarting it` looping.

**Not for:** chats already living on the right machine (nothing to migrate); fixing a *currently backgrounded, live* session (see the live-session warning below).

## How Claude Code stores chats

- Transcripts: `~/.claude/projects/<encoded-cwd>/<session-uuid>.jsonl`
- `<encoded-cwd>` = the chat's absolute working directory with **every non-alphanumeric character replaced by `-`**. In Python: `re.sub(r'[^A-Za-z0-9]','-', abspath)`.
- Each `.jsonl` line also stores `"cwd": "..."`. Agent view uses this to respawn the session. **This is the field the repair rewrites.**
- Default auto-prune is 30 days (`cleanupPeriodDays`); freshly-copied files reset that clock.

## Procedure

Do these **in order**. The fix must happen *before* you background anything.

1. **Copy the transcripts to the new Mac.** From the old Mac, copy the relevant `~/.claude/projects/<folder>/` directories (or individual `.jsonl` files) via iCloud Drive, AirDrop, or `scp` into a staging area on the new Mac. Keep an untouched backup copy — this is your safety net.

2. **Re-home each chat to the folder that matches where its files now live.** Decide the chat's real project directory on the new Mac (where its files actually are), compute `enc(that-abspath)`, and place the `.jsonl` in `~/.claude/projects/<enc>/`. If you want a chat to resume "on top of" a synced project folder, its encoded folder must match that folder's path.

3. **Run the repair script** (`scripts/fix_chat_cwd.py`). It rewrites the old→new path on every line, drops stale `bridge-session` markers, remaps any dead deeper/worktree cwd up to its nearest existing ancestor, and **only writes a file when the result is provably consistent** (home cwd exists AND encodes to its own folder); anything else is left untouched and FLAGGED. Always dry-run first:

   ```bash
   # PREVIEW — change nothing
   python3 scripts/fix_chat_cwd.py \
     --map "/Users/OLDUSER/Claude=>/Users/NEWUSER/Library/Mobile Documents/com~apple~CloudDocs/Sync workspace/Claude" \
     --filter "Sync-workspace-Claude" --dry-run

   # APPLY — with a fresh backup
   python3 scripts/fix_chat_cwd.py \
     --map "/Users/OLDUSER/Claude=>/Users/NEWUSER/Library/Mobile Documents/com~apple~CloudDocs/Sync workspace/Claude" \
     --filter "Sync-workspace-Claude" \
     --backup-dir ~/chat-migration-backup
   ```
   Pass multiple `--map` prefixes if chats came from several old locations (longest match wins). Run `python3 scripts/fix_chat_cwd.py -h` for all flags.

4. **Verify no loss and no broken paths.** Confirm the session-ID set matches your backup (`comm -23` of sorted `ls` listings → expect zero missing) and that no transcript still contains the old `/Users/OLDUSER` cwd or a home cwd that doesn't match its folder. The script's summary plus a quick re-scan covers this.

5. **Resume, then push into agent view.** For each chat:
   ```bash
   cd "/path/to/its/project/folder" && claude --resume <session-uuid>
   ```
   Wait for it to load, then type `/bg` (or press the `←` left-arrow on an empty prompt) to background it — agent view opens with it listed. Re-attach later from `claude agents` with `→`/Enter on its row. Large transcripts (tens of MB) take 10–20s to load; that's size, not a hang.

## Quick reference

| Thing | Value |
|---|---|
| Transcript path | `~/.claude/projects/<enc(cwd)>/<uuid>.jsonl` |
| Encoding | `re.sub(r'[^A-Za-z0-9]','-', abspath)` |
| Field agent view respawns in | `"cwd"` on each line |
| Send chat to agent view | `/bg` or `←` (identical) |
| Re-attach in agent view | `claude agents` → `→`/Enter |
| Repair | `scripts/fix_chat_cwd.py --map "OLD=>NEW" [--dry-run]` |

## Common mistakes

- **Running the fix on a live, backgrounded session.** Its `bridge-session` line is *live state*; stripping it disrupts the running session. Always fix **before** the first `/bg`. The normal order (copy → fix → resume → bg) avoids this. If a session is already backgrounded, stop it first.
- **`/bg` vs the arrow key.** They are identical — both background the session. If agent view fails, the cause is the recorded cwd, not which key you pressed.
- **Trusting title/size alone to pick a chat.** Duplicate titles exist; identify the right session by distinctive last-message content or session ID.
- **Skipping the dry run / backup.** The script edits transcripts in place. Dry-run first; keep the untouched copy from step 1.
- **Assuming the encoded folder decodes uniquely.** `-` is lossy (spaces, slashes, dots all become `-`). Derive folders by *encoding* a known absolute path, never by decoding the folder name.

## Real-world origin

Built from a real 271-transcript / 125-migrated move (old user `jacobzhang` → new Mac `jacq`, chats re-homed under an iCloud `Sync workspace/Claude`). Baseline: every moved chat crash-looped in agent view. After the rewrite (57k+ cwd lines, 969 stale bridge markers cleared, 18 subfolder/worktree edge-cases handled by the safety gate): all chats background cleanly. See `REFERENCE.html` for the human-readable walkthrough.
