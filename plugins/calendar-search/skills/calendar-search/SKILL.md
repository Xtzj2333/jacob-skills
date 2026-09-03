---
name: calendar-search
description: "Search Jacob's Google Calendar, and make every change to it — flights, appointments, doctor visits, classes, office hours, talks, social plans, recurring habits. Use whenever he asks 'is X on my calendar', 'do I have a…', 'when is my…', 'find my…', 'check my cal', 'what time is…', AND whenever he asks to add, schedule, book, move, reschedule or update anything, says he'll miss / skip / isn't going to something (that is a recolour to graphite, never a delete), or simply pastes an announcement or email subject and expects it handled. His events span ~13 calendars (renamed 2026-07-31 — no more 'UChicago' prefix) and are often titled in Chinese, so the naive one-calendar keyword search silently misses them — which is also how a second copy of an event he already has gets created. Search before every write. Not for to-do operations: that's jacob-todos."
---

# Calendar Search

Jacob's calendar is bCal — his Berkeley Google account — spread across ~13 calendars. Ten of them are static imports made before his UChicago account closed on 2026-07-26 — they are his and writable. They carried a `UChicago — ` prefix until 2026-07-31, when it was dropped; only the two genuinely finished ones still say so, as `SONA Schedule (UChicago, archived)` and `Potentials Lab (UChicago, archived)`. Renaming did not change their IDs. Anything created since lands on the primary.

Two things make the obvious search fail, and this skill exists because of them: most events aren't on the primary calendar, and the API's `fullText` filter doesn't reliably match Chinese titles. Get those two right and the rest is bookkeeping.

## The three rules

**Never pass `fullText` to `list_events`.** It silently misses CJK titles, and it only searches the one calendar you name — so you have to iterate calendars regardless. Pull the window and match in code against `summary` / `description` / `location`. If you catch yourself reaching for `fullText`, you're about to miss the answer. `search_events` is worse: it covers the primary only, and returns `{}` for events that plainly exist. Don't trust it for anything.

**Always start from `list_calendars` and iterate every result.** Appointments are on `Meeting`, recurring habits on `Tasks`, courses on `Classes`. Reporting "not found" after searching only the primary is the single most common way this lookup fails him.

**Never create before you search.** A write is a search with a decision on the end — see [Writing to the calendar](#writing-to-the-calendar). Skipping the sweep doesn't just risk a wrong answer, it puts a duplicate on his calendar that he then has to find and delete.

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

**Completion criterion:** every calendar's full window has actually been scanned. A calendar that threw "result too large" and wasn't retried in chunks means the search isn't finished — that's exactly how "when am I next watering the cactus?" comes back empty when the answer was sitting in `Tasks`.

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
| `Events` | old primary: personal to-dos, reminders, fixed events | |
| `Really Important Tasks` | high-priority one-offs; deadlines, payments, renewals | chunk |
| `Optional` | recurring family calls, low-priority items | chunk |
| `Tasks` | daily structure and recurring habits (`给仙人掌浇水`, mindfulness) | chunk |
| `Meeting` | lab meetings, talks, **appointments — visa, doctor, dentist** | chunk · excluded |
| `Classes` | course meetings | excluded |
| `Office Hours` | TA hours | excluded |
| `FE 3` | research schedules — live work, will refill | |
| `SONA Schedule (UChicago, archived)`, `Potentials Lab (UChicago, archived)` | finished UChicago infrastructure; empty | |
| `Holidays in United States` | auto | |

**chunk** — hundreds of recurring entries; walk these in 14-day slices from the start rather than betting on the error-recovery path.

**excluded** — `jacob-todos` skips these during to-do consolidation. That exclusion is the reason this skill exists: those four calendars are where most lookup questions actually land. Scan them.

The ten imported calendars are frozen copies (~9,120 events, colours preserved): recurring series still project forward, but no live invites arrive and nothing new is added. The shared `RAs Schedule` didn't survive the migration — it wasn't Jacob's to export. Raw `.ics` backups: `~/Claude/UChicago account backup/uchicago-calendar-backup (claude)/`.

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

## Colour semantics — graphite means "not going, keep the record"

Jacob does not delete events he decides to miss. He recolours them **graphite** (`colorId: "8"`, Google's dark-grey swatch — he calls it "black") so the entry survives as a record that he was interested. Read and write it accordingly:

- **"I'll miss X" / "can't make X" / "not attending X" is a recolour instruction, not a delete.** `update_event` with `colorId: "8"` and nothing else changed (`notificationLevel: NONE`). Never delete, and never stack, an event over a decision not to attend.
- **A graphite event is not a commitment.** When reporting it or checking for clashes, label it "on record, not attending" and don't count it against his availability. Don't nudge him about it either.
- **Leave graphite alone when enriching.** The keep-his-`colorId` rule below applies: a later abstract or room change goes into the description without touching the colour, and a graphite event is never re-coloured back on your own initiative.
- Any other colour is his own scheme and carries no such meaning; an event with no `colorId` simply inherits its calendar's colour.

The to-do side has the same convention under the name "black-coloured events" (`to do/cowork_instructions.md`, calendar gestures). Same colour, same meaning.

## Writing to the calendar

Every write starts as a search. Run the recipe above over the target date ±2 days across **every** calendar before calling `create_event`. Then pick one of three moves:

**Enrich — the default.** Information about one occasion reaches Jacob in layers: the series schedule drops in August, the abstract arrives by newsletter three weeks later, the room gets confirmed the day before. Each layer belongs in the description of the event that's already there. Patch it with `update_event`. A bare email subject plus "updated abstract" / "final schedule" / "new time" is an **edit** instruction, not a create instruction — he is handing you detail for an event he believes he already has, and he is usually right.

**Create** — only after a full sweep found nothing. Say which calendars and window you swept when you report back.

**Ask** — something close exists but you can't tell if it's the same occasion (same speaker, different date; same series, unclear instance). One crisp question beats a duplicate or a wrong overwrite.

### Mechanics

- Keep his title format, `colorId`, and calendar. Append information; don't replace what's there. Offer to move an event rather than moving it yourself.
- Send `description` as **raw HTML** (`<b>`, `<br>`, `<a href>`). Pre-escaped `&lt;b&gt;` is stored literally and renders as visible markup.
- Pass `notificationLevel: NONE` unless he asked to notify guests, and don't add other people as attendees off your own bat — most of these are his copy of someone else's event, and editing it shouldn't email anyone.
- End the description with the source: the email subject and its date. When a revised version arrives, that line is how the next session knows what it's superseding.

### Gaps in the announcement

Sources routinely omit an end time, list a room as TBA, or carry a stale semester or a typo'd date — check the weekday of every date you're given against the day of week the series actually meets. Fill the gap with the most plausible value, write the assumption into the event description, and flag it in your reply. Don't block on it, and don't silently guess.

## Reporting back

**Found it** — say *which calendar* (so he learns where to look next time), the time in the event's own zone, and location / recurrence where relevant. If it's graphite, say so: it's on record, not a commitment.

**Wrote it** — say whether you *enriched* an existing event or *created* a new one, and which calendar it's on. If you created, name the sweep that justified it ("nothing on any of the 12 calendars for Sep 1–5"), so he can catch you if you missed the copy he knows about. List every assumption you filled a gap with.

**Can't find it** — don't stop at "no". First: did you actually search the other language? Then show the closest 2–3 near-misses with their dates and calendars, because what Jacob remembers an event being called often isn't its stored title. Only after both should you say it isn't there — and then name what you searched: the calendars, the window, the keyword variants you tried. Offer Gmail, Notes, or a phone reminder as the next place to look.
