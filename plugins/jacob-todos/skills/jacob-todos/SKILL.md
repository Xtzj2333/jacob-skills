---
name: jacob-todos
description: Manage Jacob's personal to-do system built on Google Calendar + an HTML check-in surface. Use this skill whenever the user mentions tasks, to-dos, weekly consolidation, calendar cleanup, adding or merging tasks, acting on docx comments, bracket tags, inbox.md, checking what's on their plate, the morning check-in, the recommendations doc, or anything related to their task management workflow. Triggers on "my tasks", "consolidate", "rank my tasks", "add a task", "docx comments", "stack it", "what should I work on", "update the to-do doc", "commit today", "quick wins", "deadline radar", "check-in", "morning review", "regenerate check-in", "pickup actions", and on first-time-setup phrases like "set up the to-do system", "install jacob-todos", "scaffold the to-do system".
---

# Jacob's To-Do Management System (v3, HTML-first)

A personal to-do system on top of Google Calendar with an HTML decision surface. Everything lives in `<workspace>/to do/`:

- `scripts/tasks_v3.json` is the single source of truth for tasks (v3 schema).
- `state_v3.json` (root) holds system state — `calendar_config`, `stacking_day`, `thresholds`, `pruning_rules`, `landmarks`, `recent_notes`, last-run timestamps. **Always read live values from here; do not hard-code or assume.**
- `check_in.html` is the primary decision surface (built by `scripts/build_check_in.js`).
- `recs/rec_<task_id>.html` are per-task recommendation pages, linked from check-in via "View suggested plan →" (built by `scripts/build_per_task_recs.js`).
- `inbox.md` is the open-questions queue; `someday_list.md` is the low-urgency parking lot; `done.md` is the closed-task archive.

---

## First-time setup

If the user asks to "set up the to-do system" / "install jacob-todos" / "scaffold the to-do system" — and `<workspace>/to do/` does not exist yet — run this once:

1. **Pick the workspace.** Default is the user's `~/Claude/` (or whichever folder they treat as their workspace root). Ask if unclear.
2. **Create the folder structure.**
   ```
   mkdir -p "<workspace>/to do/scripts" "<workspace>/to do/recs"
   ```
3. **Copy the bundled `system/` files into place.** This skill ships templates under `system/` inside the plugin. Resolve that path (it lives next to this SKILL.md), then copy:
   - `system/state_v3.template.json` → `<workspace>/to do/state_v3.json`
   - `system/tasks_v3.template.json` → `<workspace>/to do/scripts/tasks_v3.json`
   - `system/cowork_instructions.md` → `<workspace>/to do/cowork_instructions.md`
   - `system/gcal_todo_instructions.md` → `<workspace>/to do/gcal_todo_instructions.md`
   - `system/MAP.md` → `<workspace>/to do/MAP.md`
   - `system/scripts/*` (build_check_in.js, build_per_task_recs.js, pickup_actions.js, parse_comments.py, task_verbs.js, package.json) → `<workspace>/to do/scripts/`

   Do not overwrite files that already exist — warn instead.
4. **Install script dependencies.**
   ```
   cd "<workspace>/to do/scripts" && npm install
   ```
   Installs `marked` (the markdown renderer used by `build_per_task_recs.js`).
5. **Prompt the user to fill in their calendar config.** Open `<workspace>/to do/state_v3.json` and tell them to populate:
   - `calendar_config.user_email` — their primary Google account
   - `calendar_config.todo_calendars[]` — list of calendars that contain to-dos (each with `name`, `id`, and optional `color` / `role` / `notes`)
   - `calendar_config.excluded_calendars[]` — calendars to skip (meetings, courses, etc.)

   They can get calendar IDs from Google Calendar → Settings → "Integrate calendar" → "Calendar ID".
6. **First check-in.** Once `calendar_config` is filled and there's at least one real task in `tasks_v3.json`, run:
   ```
   node scripts/build_check_in.js
   node scripts/build_per_task_recs.js
   ```
   Then open `check_in.html` in a browser.

If `<workspace>/to do/` already exists, this is not a first-time setup — proceed with the regular operating-manual flow below.

---

## Read first — these are the operating manual

This SKILL.md is the trigger surface only. For any non-trivial operation, read these:

- **`to do/cowork_instructions.md`** — calendar gestures (stacking, N+ overlap, black-events), wording/approval workflow, merging, logical subtasks, ranking philosophy, suggested-plan quality criteria, file conventions. Source of truth for skill behavior.
- **`to do/gcal_todo_instructions.md`** — calendar query rules. Reads `state_v3.json → calendar_config` for which calendars to query.
- **`to do/MAP.md`** — folder layout, what's canonical vs. retired.

If memory and the canonical files disagree, the canonical files win.

## Pipeline cheat sheet

| Situation | Run |
|---|---|
| `check_in.html` is older than `tasks_v3.json` | `node scripts/build_check_in.js` |
| `recs/` is stale, or any `solution` field changed | `node scripts/build_per_task_recs.js` |
| The user downloaded a check-in action JSON | `node scripts/pickup_actions.js` |
| The user annotated `to do.docx` with Word comments (legacy path) | `python scripts/parse_comments.py [docx]` — use span-based attribution (never naive text-order matching) |

The current channel for "Claude, do X to this task" is the form in `check_in.html`, not docx comments. Old docx-comment files in `archive/` are historical record, not instructions.

All deliverables land in `<workspace>/to do/`.

## Feedback loop

After any significant action, append one JSON line to `<workspace>/skill-logs/jacob-todos/feedback_log.jsonl` with: `timestamp`, `session_id`, `action`, `inputs`, `output`, `context_before`, `context_after`, `inferred_lesson`, `impact_estimate`. Reflect on lessons silently; don't ask the user for feedback. The `sl` (skill learner) skill manages consolidation — surface accumulated learnings only when they'd noticeably improve future runs.

For the scheduled `todo-check-in` routine: log what was done; skip context capture and impact assessment.
