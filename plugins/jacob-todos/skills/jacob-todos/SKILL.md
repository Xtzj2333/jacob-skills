---
name: jacob-todos
description: Manage Jacob's personal to-do system built on Google Calendar + an HTML check-in surface. Use this skill whenever Jacob mentions tasks, to-dos, weekly consolidation, calendar cleanup, adding or merging tasks, acting on docx comments, bracket tags, inbox.md, checking what's on his plate, the morning check-in, the recommendations doc, or anything related to his task management workflow. Triggers on "my tasks", "consolidate", "rank my tasks", "add a task", "docx comments", "stack it", "what should I work on", "update the to-do doc", "commit today", "quick wins", "deadline radar", "check-in", "morning review", "regenerate check-in", "pickup actions".
---

# Jacob's To-Do Management System (v3, HTML-first)

Jacob manages personal tasks through a **Google Calendar + HTML check-in pipeline** with companion Word docs for printable views.

The shape of the system as of 2026-05-13:

- **`tasks_v3.json`** (in `to do/scripts/`) is the single source of truth. It holds the full task array with v3 fields (`status`, `commitToday`, `scheduledDate`, `solution_*`, `rollover_count`, `last_status_change`, `snooze_until`, `review_cadence_days`, `entry_2min`, `cancel_reason`).
- **`state_v3.json`** (top of `to do/`) holds system state: `stacking_day`, `thresholds`, `pruning_rules`, `landmarks`, `recent_notes`, last-run timestamps.
- **`check_in.html`** is where Jacob actually makes decisions — built by `scripts/build_check_in.js`. This is the v3 primary surface.
- **`scripts/pickup_actions.js`** picks up the Downloads-style action JSONs that the HTML form emits, applies them to `tasks_v3.json` and `state_v3.json`, and parks the source in `scripts/processed_actions/`.
- **`to do.docx`** (printable ranked list) and **`recommendations.docx`** (per-task suggested plans) are companion Word docs generated from `tasks_v3.json` by `create_calendar_doc.js` and `create_recommendations_doc.js`. They are read-only outputs — Jacob doesn't make decisions in them; they're for printing / margin annotation.
- **`done.docx`** is the closed-tasks archive (`create_done_doc.js`).
- **`inbox.md`** is the open-questions queue. **`someday_list.docx`** is the low-priority parking lot.

## Before doing anything

The canonical instructions — quirks, calendar gestures, approval rules, suggested-plan acceptance criteria — live in:

```
to do/cowork_instructions.md
```

**Read this file first** for any non-trivial operation. It's the source of truth for skill behavior; this SKILL.md is only the trigger surface.

For calendar query rules specifically: `to do/gcal_todo_instructions.md`.

The legacy `references/` files in this skill folder (`calendar.md`, `docx_workflow.md`, `preferences.md`) describe the pre-v3 docx-only workflow and may conflict with the v3 system. Treat `cowork_instructions.md` as authoritative when they disagree.

## Calendar gestures (peculiar — read before any closure)

Quoting `cowork_instructions.md` for emphasis — these gestures are how Jacob signals task state and misreading them is the most likely way to lose his work:

- **Stacking instead of deleting.** Retired/merged events get moved to `state_v3.json.stacking_day` at a common time slot. "Delete" in conversation = "stack."
- **4+ overlap on a stacking day = closure intent.** Threshold lives in `state_v3.json.thresholds.stacked_closure_threshold`. Recurring events don't count.
- **Black-colored events = decided not to do.** Inactive/ignored.

## Wording preciseness + approval workflow

Jacob is particular about exact text of calendar event titles. **Never rephrase a calendar title without explicit approval.** Same rule for descriptions and merges. Pure time-slot moves don't need approval.

Approval flow: present a table (current → proposed + one-line reason), wait for approval per row, then execute.

## Core operations

### 1. Morning check-in / "what should I work on"
1. If `check_in.html` is older than `tasks_v3.json`, regenerate: `node scripts/build_check_in.js`.
2. Open the HTML for Jacob.
3. After he downloads action JSONs, run `node scripts/pickup_actions.js` to apply.

### 2. Acting on docx comments (legacy but still supported)
Jacob may still annotate `to do.docx` with Word comments — these are instructions for Claude. Use `python scripts/parse_comments.py [docx]` for span-based attribution (per Rule 12 — never naive text-order matching). Present the summary table for approval before acting.

### 3. Adding new tasks
1. Add to **both** Google Calendar AND `tasks_v3.json`.
2. **Small / simple tasks → title only.** No padded descriptions Jacob didn't ask for.
3. **Complex tasks with sub-items, links, instructions → title + description.**
4. Free to rephrase titles for new tasks (never alter existing calendar titles without approval).
5. For procrastination-prone deadlines, set the calendar date with buffer days before the real deadline.
6. Regenerate `check_in.html` (and the docx companions if Jacob wants printable updates).

### 4. Stacking ("deleting") events
1. Stacking day lives in `state_v3.json.stacking_day` (currently "Saturday May 9" in the latest snapshot).
2. Move the event to the stacking slot (~10:00–10:30).
3. For recurring events: only update the single instance (use the `_TIMESTAMP` suffixed event ID). Never modify the recurring series.
4. Update `tasks_v3.json` (set `status: 'done'` or `'cancelled'`) and regenerate the surfaces Jacob cares about.

### 5. Merging related tasks
Survivor = the one with more information. Stack the absorbed event. Always present the merge for approval before editing. Update `tasks_v3.json` and regenerate.

### 6. Suggested-plan quality (load-bearing — see `cowork_instructions.md` §Suggested-plan quality)
The `solution` field is the make-or-break feature. Acceptance criteria:
- Researched, not made up (real sources, deep web search, live URL/price checks).
- Search Jacob's own data when relevant (Gmail, Drive, Calendar via MCP).
- Length matches usefulness — default to the smallest piece that unblocks the next action.
- Linkable "deep dive" companion HTML is fine.
- Cite what you used.

A plan that doesn't meet these is "needs review," not "done."

### 7. Scheduled check-in (routine, every 3 days)
Scan for tasks approaching deadlines, flag stale calendar events, check for new events that need ranking, produce a brief status summary. Append to the feedback log silently — skip context capture and impact assessment for the routine.

## Output location

All deliverables go to: the `to do/` folder in Jacob's selected workspace directory.

## Feedback Loop (Continuous Improvement)

This skill learns from usage through silent observation. After completing any significant action:

1. **Log what you did.** Append a JSON line to `<workspace>/skill-logs/jacob-todos/feedback_log.jsonl`. Each line:
   ```json
   {"timestamp": "<ISO 8601>", "session_id": "<date or short id>", "action": "<what you did, 1-2 sentences>", "inputs": "<what Jacob asked for>", "output": "<what was produced>", "context_before": "<brief summary of the 2 prompts before this skill was invoked>", "context_after": "<brief summary of Jacob's reaction / next 2 prompts>", "inferred_lesson": "<what this means for future runs — be specific>", "impact_estimate": "<would acting on accumulated learnings make this skill noticeably better?>"}
   ```

2. **Reflect on what could be better.** Infer lessons from context — what Jacob said before, what the skill did, how Jacob reacted. Do NOT ask Jacob for feedback. Be specific.

3. **Assess accumulated impact.** Judge whether accumulated learnings would make the skill noticeably smoother. If yes — present proposed changes in a table for approval. If not — log silently.

For the scheduled todo-check-in routine: just log what it did. Skip context capture and impact assessment.

## Ranking philosophy

> urgency (hard deadlines, blocking others) > time-decay (professional emails go stale) > importance for active projects > logistics with deadlines > health > professional comms > personal/admin > leisure
