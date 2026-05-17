---
name: jacob-todos
description: Manage Jacob's personal to-do system built on Google Calendar + an HTML check-in surface. Use this skill whenever Jacob mentions tasks, to-dos, weekly consolidation, calendar cleanup, adding or merging tasks, acting on docx comments, bracket tags, inbox.md, checking what's on his plate, the morning check-in, the recommendations doc, or anything related to his task management workflow. Triggers on "my tasks", "consolidate", "rank my tasks", "add a task", "docx comments", "stack it", "what should I work on", "update the to-do doc", "commit today", "quick wins", "deadline radar", "check-in", "morning review", "regenerate check-in", "pickup actions".
---

# Jacob's To-Do Management System (v3, HTML-first)

Jacob runs a personal to-do system on top of Google Calendar with an HTML decision surface. Everything lives in `<workspace>/to do/`:

- `scripts/tasks_v3.json` is the single source of truth for tasks (v3 schema).
- `state_v3.json` (root) holds system state — `stacking_day`, `thresholds`, `pruning_rules`, `landmarks`, `recent_notes`, last-run timestamps. **Always read live values from here; do not hard-code or assume.**
- `check_in.html` is the primary decision surface (built by `scripts/build_check_in.js`).
- `recs/rec_<task_id>.html` are per-task recommendation pages, linked from check-in via "View suggested plan →" (built by `scripts/build_per_task_recs.js`). Replaces the retired `recommendations.html`.
- `inbox.md` is the open-questions queue; `someday_list.md` is the low-urgency parking lot; `done.md` is the closed-task archive.

## Read first — these are the operating manual

This SKILL.md is the trigger surface only. For any non-trivial operation, read these:

- **`to do/cowork_instructions.md`** — calendar gestures (stacking, 4+ overlap, black-events), wording/approval workflow, merging, logical subtasks, ranking philosophy, suggested-plan quality criteria, file conventions. Source of truth for skill behavior.
- **`to do/gcal_todo_instructions.md`** — calendar query rules.
- **`to do/MAP.md`** — folder layout, what's canonical vs. retired.

If memory and the canonical files disagree, the canonical files win.

## Pipeline cheat sheet

| Situation | Run |
|---|---|
| `check_in.html` is older than `tasks_v3.json` | `node scripts/build_check_in.js` |
| `recs/` is stale, or any `solution` field changed | `node scripts/build_per_task_recs.js` |
| Jacob downloaded a check-in action JSON | `node scripts/pickup_actions.js` |
| Jacob annotated `to do.docx` with Word comments (legacy path) | `python scripts/parse_comments.py [docx]` — use span-based attribution (never naive text-order matching) |

The current channel for "Claude, do X to this task" is the form in `check_in.html`, not docx comments. Old docx-comment files in `archive/` are historical record, not instructions.

All deliverables land in `<workspace>/to do/`.

## Feedback loop

After any significant action, append one JSON line to `<workspace>/skill-logs/jacob-todos/feedback_log.jsonl` with: `timestamp`, `session_id`, `action`, `inputs`, `output`, `context_before`, `context_after`, `inferred_lesson`, `impact_estimate`. Reflect on lessons silently; don't ask Jacob for feedback. The `sl` (skill learner) skill manages consolidation — surface accumulated learnings only when they'd noticeably improve future runs.

For the scheduled `todo-check-in` routine: log what was done; skip context capture and impact assessment.
