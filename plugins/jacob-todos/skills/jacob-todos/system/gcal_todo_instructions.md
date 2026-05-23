# Google Calendar To-Do Extraction — Instructions for Claude

## Goal
Given a time range, identify the user's personal **to-dos** from Google Calendar and compile them. To-dos are personal tasks, reminders, and self-assigned actions — NOT meetings, lectures, or events the user attends passively.

---

## Calendar configuration lives in `state_v3.json`

The list of which Google Calendars to query (and which to exclude) is **not hard-coded here**. It lives in `state_v3.json → calendar_config`, so a new user fills it in once instead of editing this doc.

Before the first run, populate:

- `calendar_config.user_email` — the primary Google account that owns the calendars
- `calendar_config.todo_calendars[]` — calendars that DO contain to-dos (each with `name`, `id`, optional `color`, `role`, `notes`)
- `calendar_config.excluded_calendars[]` — calendars that NEVER contain to-dos (meetings, lectures, etc.)

`role` on a to-do calendar is a hint to humans (`main`, `priority`, `optional`, `recurring`); the code doesn't branch on it.

---

## Querying rule

Only query calendars listed under `calendar_config.todo_calendars`. **Always query all of them explicitly by `calendarId`** — do not rely on the default primary calendar alone. The most common bug is missing a high-priority calendar because it has a different `calendarId` from the primary email.

Never query anything in `calendar_config.excluded_calendars` when looking for to-dos.

---

## Important nuance: the main calendar can contain both

Not every event on the main calendar is a personal to-do — some entries are lectures or talks the user is attending (e.g. "Latin America Lecture"). Treat those as meetings and exclude.

**Rule of thumb:** If the event is something the user *does themselves* (email someone, book something, research something), it's a to-do. If the user *goes to* or *attends* it, it's a meeting.

---

## Procedure

1. Ask for the **time range** (e.g. "this week", "April 10–17").
2. Fetch events from **all calendars in `calendar_config.todo_calendars`** using explicit `calendarId` calls.
3. Filter out anything that looks like a passive attendance event (lectures, talks, etc.) even if it appears on the main to-do calendar.
4. Compile the remaining items into the desired format (Word doc, list, etc.).
5. **Watch for non-ASCII encoding issues** — always verify Unicode code points manually and check the rendered output with `pandoc` before saving.

## Notes on moving tasks to other days

When checking what's already on a given day before re-scheduling, query **all calendars in `calendar_config.todo_calendars`** for that date. Missing one calendar (e.g. a high-priority side calendar) is the canonical way to mis-detect a date as empty when it isn't.

Non-to-do events that may appear on a target day and cause visual overlaps (don't move or modify these):

- Calendars in `excluded_calendars` (meetings, courses) — leave alone
- Recurring daily-structure events (e.g. "check in workday", "mindfulness") — daily routine, not movable
- Recurring family / personal calls — same
