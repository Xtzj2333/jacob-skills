---
name: calendar-search
description: "Search Jacob's Google Calendar for any event that isn't an active to-do — flights, appointments, doctor visits, classes, office hours, talks, social plans, recurring habits. Use whenever he asks 'is X on my calendar', 'do I have a…', 'when is my…', 'find my…', 'check my cal', 'what time is…', or names any event he believes exists somewhere. His events span ~13 calendars and are often titled in Chinese, so the naive one-calendar keyword search silently misses them — use this recipe instead. Not for to-do operations: that's jacob-todos."
---

# Calendar Search

Jacob's calendar is bCal — his Berkeley Google account — spread across ~13 calendars. The ten named `UChicago — <name>` are static imports made before his UChicago account closed on 2026-07-26 — they are his and writable; the prefix is a label, not a location. Anything created since lands on the primary.

Two things make the obvious search fail, and this skill exists because of them: most events aren't on the primary calendar, and the API's `fullText` filter doesn't reliably match Chinese titles. Get those two right and the rest is bookkeeping.

## The two rules

**Never pass `fullText` to `list_events`.** It silently misses CJK titles, and it only searches the one calendar you name — so you have to iterate calendars regardless. Pull the window and match in code against `summary` / `description` / `location`. If you catch yourself reaching for `fullText`, you're about to miss the answer.

**Always start from `list_calendars` and iterate every result.** Appointments are on `UChicago — Meeting`, recurring habits on `UChicago — Tasks`, courses on `UChicago — Classes`. Reporting "not found" after searching only the primary is the single most common way this lookup fails him.

## The recipe

```python
calendars = list_calendars()
keywords  = expand(question)          # bilingual — see below
matches   = []

for cal in calendars:
    if cal["summary"] in NOISY:       # marked "chunk" in the table below
        events = walk_in_chunks(cal["id"], start, end, days=14)
    else:
        try:
            events = list_events(calendarId=cal["id"], startTime=start,
                                 endTime=end, orderBy="startTime")["events"]
        except ResultTooLargeError:
            events = walk_in_chunks(cal["id"], start, end, days=14)

    for ev in events:                 # match in CODE, never via fullText
        blob = " ".join(filter(None, [ev.get("summary"), ev.get("description"),
                                      ev.get("location")])).lower()
        if any(k.lower() in blob for k in keywords):
            matches.append((cal["summary"], ev))
```

**Completion criterion:** every calendar's full window has actually been scanned. A calendar that threw "result too large" and wasn't retried in chunks means the search isn't finished — that's exactly how "when am I next watering the cactus?" comes back empty when the answer was sitting in `UChicago — Tasks`.

## Keyword expansion

The calendar is bilingual — some titles Chinese (`给仙人掌浇水`), some English, some mixed. Whatever language he asks in, search both. Over-including costs one discarded match; under-including costs the answer.

| He asks about | Also search |
|---|---|
| cactus / plant watering | `仙人掌`, `浇水`, `植物`, `water`, `plant` |
| visa appointment | `签证`, `领事`, `面签`, `consular`, `embassy`, `consulate` |
| flight | `航班`, `飞机`, `机票`, `depart`, `arrival`, `airport` |
| family call | `打电话`, `通话`, `妈`, `爸`, `mom`, `dad`, `grandma` |
| doctor / dentist | `医生`, `牙医`, `看病`, `medical`, `appointment` |
| lab meeting | `实验室`, `lab`, the lab leader's name |

## The calendars

Re-fetch with `list_calendars` every time — IDs can rotate. Canonical IDs live in `~/Claude/to do/gcal_todo_instructions.md` and are deliberately not duplicated here, so there's only one copy to keep true.

| Calendar | Holds | |
|---|---|---|
| the primary (his bCal account) | everything created after July 2026 | |
| `UChicago — Events` | old primary: personal to-dos, reminders, fixed events | |
| `UChicago — Really Important Tasks` | high-priority one-offs; deadlines, payments, renewals | chunk |
| `UChicago — Optional` | recurring family calls, low-priority items | chunk |
| `UChicago — Tasks` | daily structure and recurring habits (`给仙人掌浇水`, mindfulness) | chunk |
| `UChicago — Meeting` | lab meetings, talks, **appointments — visa, doctor, dentist** | chunk · excluded |
| `UChicago — Classes` | course meetings | excluded |
| `UChicago — Office Hours` | TA hours | excluded |
| `UChicago — Potentials Lab`, `— SONA Schedule`, `— FE 3` | research schedules | |
| `Holidays in United States` | auto | |

**chunk** — hundreds of recurring entries; walk these in 14-day slices from the start rather than betting on the error-recovery path.

**excluded** — `jacob-todos` skips these during to-do consolidation. That exclusion is the reason this skill exists: those four calendars are where most lookup questions actually land. Scan them.

The `UChicago — *` calendars are frozen copies (~9,120 events, colours preserved): recurring series still project forward, but no live invites arrive and nothing new is added. The shared `RAs Schedule` didn't survive the migration — it wasn't Jacob's to export. Raw `.ics` backups: `~/Claude/UChicago account backup/uchicago-calendar-backup (claude)/`.

## Date window

| He says | Window |
|---|---|
| "in June", "next month", "this week" | that period |
| a specific date | that date ±2 days, in case he misremembered |
| nothing | next 90 days; if empty, extend 30 days back |

For anything recurring, the window only needs to reach the next instance — don't sweep a year.

## Timestamps — the one that's easy to get backwards

The API returns `dateTime` in *your* calendar's offset, not the event's. `timeZone` is what the human cares about.

```
"start": {
  "dateTime": "2027-03-15T21:15:00-05:00",   ← requestor-side offset
  "timeZone": "Asia/Tokyo"                   ← the zone the event lives in
}
```

Reading that as "9:15 PM Tokyo" is wrong. The `-05:00` puts the moment at `2027-03-16T02:15Z`, which in Tokyo (UTC+9) is **March 16, 11:15 AM**. Easiest fix: pass `timeZone="Asia/Tokyo"` to `list_events` and let the API convert.

An event stored in a non-local zone is stored that way on purpose — it's the real time at the venue, and converting it away strips that signal. Report the source zone first and add his current device-local time as a parenthetical if it helps. Never substitute a hardcoded city; he relocates.

## Reporting back

**Found it** — say *which calendar* (so he learns where to look next time), the time in the event's own zone, and location / recurrence where relevant.

**Can't find it** — don't stop at "no". First: did you actually search the other language? Then show the closest 2–3 near-misses with their dates and calendars, because what Jacob remembers an event being called often isn't its stored title. Only after both should you say it isn't there — and then name what you searched: the calendars, the window, the keyword variants you tried. Offer Gmail, Notes, or a phone reminder as the next place to look.
