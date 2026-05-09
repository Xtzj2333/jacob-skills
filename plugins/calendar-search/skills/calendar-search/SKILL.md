---
name: calendar-search
description: "General-purpose Google Calendar lookup for Jacob — answering 'is X on my calendar', 'do I have a Y', 'when is my Z', or 'find the event about W'. Use this whenever Jacob asks about ANY event on his calendar that isn't an active to-do task — flights, appointments, meetings, talks, classes, social plans, doctor visits, family events, recurring habits, plant-care reminders, or anything where Jacob expects 'it should be on my calendar somewhere'. The to-do skill (jacob-todos) excludes several calendars by design; this skill exists because those excluded calendars (Meeting, Classes, Office Hours, Tasks, etc.) are exactly where appointments, recurring habits, and fixed events live. Trigger on phrases like 'is X on my calendar', 'do I have', 'when is my', 'find my', 'search my calendar', 'check my cal', 'what time is', or any question about a specific event Jacob believes exists. Don't trigger for general to-do operations — that's jacob-todos."
---

# Calendar Search

Jacob's calendar holds events across roughly a dozen calendars in Google. The naive search — "default calendar + fullText filter" — misses most of what he asks about because (1) most events don't live on the default calendar and (2) the API's `fullText` filter doesn't reliably match Chinese or other non-Latin titles. This skill is the recipe for doing it right.

## The one rule that matters most

**Do not use the `fullText` parameter to filter `list_events` calls.** It silently misses CJK titles and only searches the calendar you specify, so you have to iterate calendars anyway. Filter in code instead, on the actual `summary` / `description` / `location` fields.

The second-most-important rule: **always query `list_calendars` first and iterate every result by `calendarId`.** Never trust the default primary calendar — most things Jacob asks about live elsewhere (Meeting holds his appointments; Tasks holds recurring habits like watering his cactus; Classes holds course meetings).

## The standard search recipe

```python
# 1. Get every calendar Jacob has
calendars = list_calendars()  # ~13 calendars

# 2. Expand the query into likely keyword variants BEFORE scanning
#    English ↔ Chinese synonyms, partial substrings, related terms
keywords = expand_keywords(jacob_question)  # see "Keyword expansion" below

# 3. For each calendar, fetch events in the date window WITHOUT fullText
matches = []
for cal in calendars:
    try:
        events = list_events(
            calendarId=cal["id"],
            startTime=window_start,
            endTime=window_end,
            orderBy="startTime",
        )  # NO fullText param — pull everything in the window
    except ResultTooLargeError:
        # Some calendars (notably "Tasks") have hundreds of recurring entries
        # like "check in workday" / "mindfulness" — split the window and retry
        events = fetch_in_chunks(cal["id"], window_start, window_end, chunk_days=14)

    # 4. Substring-match in CODE on summary, description, location
    for ev in events.get("events", []):
        blob = " ".join([
            ev.get("summary", "") or "",
            ev.get("description", "") or "",
            ev.get("location", "") or "",
        ]).lower()
        if any(k.lower() in blob for k in keywords):
            matches.append((cal["summary"], ev))
```

This pattern catches Chinese, mixed scripts, partial matches, and synonyms in one pass. It is non-negotiable. If you find yourself reaching for `fullText`, stop — you're about to silently miss the answer.

## Keyword expansion

Jacob's calendar is bilingual: many events have Chinese titles (e.g., `给仙人掌浇水`), some have English titles, some mix both. Whatever language Jacob asks in, **build a keyword list with both English and Chinese forms** before scanning.

| Jacob asks about | Expand to keywords |
|---|---|
| cactus / plant watering | `cactus`, `plant`, `water`, `仙人掌`, `浇水`, `植物` |
| visa appointment | `visa`, `consular`, `appointment`, `embassy`, `consulate`, `签证`, `领事`, `面签` |
| flight | `flight`, `depart`, `arrival`, `airport`, `航班`, `飞机`, `机票` |
| family call | `call`, `mom`, `dad`, `grandma`, `family`, `打电话`, `通话`, `妈`, `爸` |
| doctor / dentist | `doctor`, `dentist`, `medical`, `医生`, `牙医`, `看病` |
| lab meeting | `lab meeting`, `lab`, lab leader's name, `实验室` |

When unsure, over-include keywords. The cost of an extra match-and-discard is tiny; the cost of missing the event is high (Jacob loses trust in the lookup).

## Calendars with heavy recurring noise — chunk by default

The `Tasks` calendar has hundreds of recurring entries (`check in workday`, `mindfulness`, repeated daily) that almost always exceed the `list_events` token limit when you request a 90-day window in one call. The same is sometimes true of `Optional`, `Really Important Tasks`, and `Meeting`.

**Don't bet on the error-recovery path. Default to chunked windows for these four calendars from the start.** Skipping `Tasks` because of a too-large error is exactly how Jacob loses an answer like "when am I watering my cactus next?" — that recurring habit lives there.

The chunking loop:

```python
NOISY_CALENDARS = {"Tasks", "Optional", "Really Important Tasks", "Meeting"}

def fetch_events(cal, window_start, window_end):
    if cal["summary"] in NOISY_CALENDARS:
        # Walk forward in 14-day slices
        cursor = window_start
        all_events = []
        while cursor < window_end:
            chunk_end = min(cursor + timedelta(days=14), window_end)
            events = list_events(calendarId=cal["id"], startTime=cursor, endTime=chunk_end, orderBy="startTime")
            all_events.extend(events.get("events", []))
            cursor = chunk_end
        return all_events
    else:
        # Try one shot; if it fails, fall back to chunking
        try:
            return list_events(calendarId=cal["id"], startTime=window_start, endTime=window_end, orderBy="startTime").get("events", [])
        except ResultTooLargeError:
            return fetch_events_chunked(cal, window_start, window_end, days=14)
```

**Completion criterion: the search is not done until every calendar's full date window has been actually scanned in code.** If a calendar returned a too-large error and you didn't retry with chunks, you have not finished — go back and chunk it before reporting "not found."

## Picking the date window

| Jacob says... | Use window |
|---|---|
| "in June" / "next month" / "this week" | That bounded period |
| Specific date ("the 9th", "Monday") | The date ±2 days (in case he mis-recalled) |
| No date hint | Next 90 days from today; if nothing turns up, expand backward 30 days |

When the event might be recurring (cactus watering, family calls, lab meetings), the date window only needs to capture the next instance — don't expand to a year.

## Hint: keyword-to-calendar associations

These are *hints*, not shortcuts. Always scan every calendar — but if you have to triage which one to look at first when results are partial, this is roughly where things live:

| Keyword cluster | Most likely calendar |
|---|---|
| "appointment", "consular", "embassy", "doctor", "dentist" | Meeting |
| Recurring habit (watering, mindfulness, family call) | Tasks, Optional |
| Lab meeting, talk, seminar, lecture Jacob attends | Meeting, Classes |
| Office hours / TA work | Office Hours |
| Flight, departure, arrival, trip | Events, Really Important Tasks |
| Deadline, payment, renewal, submit | Really Important Tasks, Tasks |

Never report "not found" without having scanned **every** calendar from `list_calendars` — including the bold/excluded ones in the to-do skill.

## When you don't find an exact match

Don't conclude the event doesn't exist. Two things to do:

1. **Broaden the keyword set.** If Jacob asked in English ("cactus"), did you actually search for the Chinese variant (`仙人掌`)? If he asked in Chinese, did you search for the English form? Run the scan again with the broader list.
2. **Surface near-misses.** Show the closest 2–3 candidate events you found, with their dates and calendars. The to-do skill has a documented pattern: docx and calendar titles diverge, so what Jacob remembers an event being called isn't always its actual title. Let him pick.

Only after both of those should you report "I couldn't find this on any calendar, in either language. Want me to check Gmail, your Notes, or a phone reminder?"

## Reading Google Calendar timestamps correctly

Google's API returns `dateTime` in the requestor's calendar offset by default, **not** in the event's source timezone. The `timeZone` field is the source-of-truth for what the human cares about.

For example, an event stored in `Asia/Tokyo` may come back from the API as:
```
"start": {
  "dateTime": "2027-03-15T21:15:00-05:00",   # Chicago offset
  "timeZone": "Asia/Tokyo"                   # actual zone the event is set in
}
```

The naive read — "21:15 in Asia/Tokyo → 9:15 PM Tokyo" — is wrong. The correct read:
- The `-05:00` offset means UTC moment is `2027-03-16T02:15:00Z`
- In `Asia/Tokyo` (UTC+9), that's **2027-03-16 11:15 AM Tokyo time**
- So when reporting, show **March 16, 11:15 AM Tokyo time**, not "March 15 21:15 Tokyo"

When in doubt, pass `timeZone="Asia/Tokyo"` (or whatever zone is in the event) to `list_events` so the API returns the dateTime in that zone directly.

## Reporting back

When you find the event, give Jacob:
- **Which calendar** it's on (so he learns where to look next time)
- **The date and time in the event's source timezone** (the `timeZone` field — see above for how to convert correctly). For events in non-local zones, optionally also show Chicago time as a parenthetical, but never replace the source-zone time silently. If an event is stored in a non-local zone, that's intentional — it's the actual time at the venue; converting it away strips that signal.
- **Location, description, recurrence** if any of those is relevant

When you can't find it, tell Jacob:
- The full list of calendars you searched (name them)
- The date window you used
- The keyword variants you tried (especially the CJK ones)
- Any near-miss candidates

## Calendar reference

Always re-fetch via `list_calendars` — IDs can rotate. As of last review, Jacob has roughly:

| Calendar | Holds |
|---|---|
| Events | Primary calendar — personal to-dos, reminders, occasional fixed events |
| Really Important Tasks | High-priority one-offs |
| Optional | Recurring family calls, low-priority items |
| Tasks | Daily structure (workday check-in, mindfulness), recurring habits like 给仙人掌浇水 |
| **Meeting** | Lab meetings, talks, **appointments (visa, doctor, etc.)** |
| **Classes** | Course meetings |
| **Office Hours** | TA hours |
| **Potentials Lab**, **SONA Schedule**, **FE 3**, **RAs Schedule** | Research-related schedules |
| Holidays | UK holidays (auto) |

Bold = the to-do skill (`jacob-todos`) excludes these from to-do consolidation, but they hold real events Jacob will ask about. **Scan them anyway.**

## Anti-patterns (the failure modes)

- ❌ Calling `list_events` without a `calendarId` and reporting "not found" — that only searches the default Events calendar.
- ❌ Calling `list_events(calendarId=..., fullText="仙人掌")` and trusting the empty result — `fullText` does not reliably match CJK substrings, even when the event title contains the exact characters.
- ❌ Searching only in the language Jacob asked the question in, when his calendar is bilingual.
- ❌ Skipping a calendar because `list_events` returned a "result too large" error — split the window into 14-day chunks and retry. The recurring habits and noise events live there. **For Tasks/Optional/Really Important Tasks/Meeting, default to chunked windows from the start; don't bet on the recovery path.**
- ❌ Reporting "not found" before scanning Meeting, Classes, Office Hours, and Tasks — the four calendars the to-do skill excludes are exactly where most lookup queries land.
- ❌ Silently converting the event's stored timezone — if it's stored in `Asia/Tokyo` (or any non-local zone), that's intentional; preserve it in your report.
