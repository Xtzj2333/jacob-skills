---
name: zoom-scheduling
description: Use when the user asks to schedule, set up, or add a Zoom meeting or Zoom call with someone ("zoom with Iris tomorrow 2pm", "put a zoom link on my meeting with X", "cancel that zoom"), from the terminal or a Slack bridge, or when a calendar event needs a Zoom link rather than Google Meet.
---

# Zoom scheduling

Make a real Zoom meeting on a university Zoom account that has no API, then put its link on a Google Calendar event, and let the person approve before anyone else sees anything.

**Why the browser and not an API:** university accounts routinely forbid third-party Zoom apps (UC Berkeley: "we are not approving third-party apps", KB0013608), a personal API app needs a "Zoom for developers" role students rarely have, Zoom's Claude connector cannot create meetings, and the Zoom desktop app has no scripting at all. So the meeting is made in the user's own signed-in Zoom portal through Claude-in-Chrome. It lands in the same account their desktop app shows.

## First: read the config

`~/.config/zoom-scheduling/config.json` holds everything account-specific:

```json
{ "zoom_domain": "yourschool.zoom.us", "calendar": "Meetings", "default_minutes": 60,
  "title_pattern": "{first} & {me}", "me": "Sam",
  "private_notes": "~/notes/zoom-scheduling.md",
  "people": { "<their email>": { "title": "Robin & Sam", "minutes": 60 } } }
```

No config? Ask for the Zoom domain and the calendar, write the file, then carry on.

**Defaults are per person, and you do not invent them.** Someone in `people` gets exactly those values. For anyone else, use what the user said in the request; if they did not say a title or a length, **ask one short question** instead of assuming (their words: "I will clarify, or maybe if I don't clarify, you should ask me"). The location is always the Zoom join link, and the description stays **empty** unless they ask for one — this overrides calendar-search's source-line rule.

## Flow

1. **Resolve** who (their email, from Gmail or earlier invites; ask if two people match), when, how long, and the title per the rule above. Times are the user's local zone unless they say otherwise.
2. **Search before writing.** REQUIRED SUB-SKILL: calendar-search (every calendar, date ±2 days).
   - Same person at the same time: **enrich** that event, often an instance of a recurring series.
   - Same person at a different time: ask.
   - Nothing: a new event.
   - Name any clash with their other events.
3. **Create the Zoom meeting.**
   `python3 ~/.claude/skills/zoom-scheduling/scripts/zoom_js.py create --topic "Robin & Sam" --start "2026-09-19 15:15" --minutes 60 --tz America/Los_Angeles`
   Then `tabs_context_mcp {createIfEmpty:true}`, navigate to `https://<zoom_domain>/meeting/schedule`, wait 3 s, and check where you actually landed before running anything. **A first load that bounces to the SSO login page usually means the redirect is still in flight, not that they are signed out — navigate to the same URL a second time and wait again.** Only if the second load is still a login page is the session really gone. Once the page is `/meeting/schedule` and a `Save` button exists, run the printed JS in `javascript_tool`, byte for byte. It returns `{ok, meetingNumber, joinLink, manageUrl}`.
   Always pass `--tz`: a profile time zone left on the wrong continent silently shifts the meeting (one real account's still says Jakarta months after the trip).
4. **Verify.** Open `https://<zoom_domain>/meeting/<meetingNumber>`. Its Time line must start with the output of `zoom_js.py expect --start "<same>"` and name the zone you meant. If it doesn't, delete the meeting and stop.
5. **Draft it all, show it, and leave the other person untouched.** Until the user approves, nobody else sees anything: no invite email, no new event on their calendar, no edit to an event they are on.
   - **New event:** `create_event` on the configured calendar with the title, time and `location` = joinLink. **No attendees**, `notificationLevel: NONE`.
   - **Existing event that already has the guest:** change nothing yet.
   - **If the user is at the machine:** show the drafts in the real pages, because that is how they check them — the Zoom meeting page, and the calendar event. For a new event open its **edit** page (`https://calendar.google.com/calendar/u/0/r/eventedit/<base64 eid>`) and type the guest into "Add guests" **without saving**, so approving is one click. Tell them exactly which buttons: **Save**, then **Send** (and "This event" first, for one instance of a recurring series). If typing the guest doesn't take, say so and offer the "send" route instead.
   - **From Slack or headless:** reply with title, time and zone, calendar, meeting ID and link, the event link, the guest, and *reply **send** to invite <name> (an email goes out)*.
6. **On approval.** If they clicked Save themselves, re-read the event and confirm what it now says. If they reply **send**: for a new event, `update_event` with `addedAttendees` and `notificationLevel: ALL`; for an existing event, `update_event` that event (for a recurring series, the instance id only) with the new title and location, `notificationLevel: ALL`. If they say "quietly" or "no notifications", use `NONE` instead. If the request already said to invite, steps 5 and 6 happen in one turn.
7. **Close your Zoom tab.** Report: created or enriched, which calendar, the sweep you ran, the meeting ID, the link, and whether an email went out. You can verify that last one: Google's invitations land in the sender's own Gmail **Sent** as "Invitation: <title>" or "Updated invitation: <title>" (`in:sent newer_than:1d "<title>"`).

**Cancel or undo:** `zoom_js.py delete --id <meetingNumber>`, run its JS on any page of that Zoom domain; then `delete_event` with `notificationLevel: NONE` (`ALL` if the guest had already been invited). Zoom emails the host a "meeting deleted" notice; deleted meetings stay recoverable for 7 days.

## When it fails

| Symptom | Meaning | Do |
|---|---|---|
| No `mcp__claude-in-chrome__*` tools | The session has no browser (a headless run started without `--chrome`) | Say so; the meeting can't be made here. Offer a standing personal link from `private_notes` only if they agree. |
| `not on the schedule page`, or a login page | Mid-SSO redirect, or really signed out | **Load the schedule URL once more first** — a live CalNet session often bounces on the first hit and goes straight through on the second (seen 2026-09-19). Still a login page after the retry: ask them to sign in (SSO and 2FA are theirs to do). Nothing was created either way. |
| `no Save button yet` | The form was still loading | Wait 3 s and rerun the same JS once. |
| `Zoom changed its schedule form…`, or any other error | The portal changed | Nothing was created. Tell them. Capture one real Save click with `read_network_requests` and update `create.js`. |

**Don't** click through the schedule form: its dropdowns snap back in a background tab. Don't substitute Google Meet, and don't change their Zoom profile or account settings.

Account-specific details (personal meeting link, regular guests, history) live in the `private_notes` file, never here: this file is published.
