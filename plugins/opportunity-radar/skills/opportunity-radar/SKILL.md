---
name: opportunity-radar
description: Use when someone wants a recurring automated sweep that finds opportunities for them — funding, fellowships, training programmes, internships, jobs, application deadlines — and delivers a digest to Slack or email on a schedule. Also when they say their radar missed something, want to change what it looks for, want to know whether it is still running, or want it paused. Triggers on "set up an opportunity radar", "weekly digest of funding/internships", "it missed X", "why didn't it find", "is my radar still working".
---

# Opportunity radar

Build someone a weekly scout: a scheduled Claude session in the cloud that sweeps their mail and a named list of sites, then posts them one digest and pings them.

**It is not this skill running weekly.** A skill is a recipe read inside a live session. The engine is a **cloud routine** on the user's own account, created through `RemoteTrigger`, which fires on a cron whether or not their laptop is open. This skill's job is to *interview them, write that routine's prompt, create it, and keep editing it as they give feedback.*

Three pieces get built. Say so early, because the second one surprises people:

| Piece | What it is | Who owns it |
|---|---|---|
| The scout | A cloud routine — scheduled, isolated, runs with nobody watching | Their claude.ai account |
| The notification | A Slack app they create, which posts as a bot and then DMs them | Their Slack workspace |
| The knowledge | Standing instructions inside the routine's prompt, edited every time they give feedback | The prompt itself, and their profile. `references/standing-lessons.md` is read-only reference |

The notification is a separate app because **Slack never notifies anyone about a message posted under their own name.** A digest posted as the user sits unread with no badge. Only a bot-authored post, plus a bot DM, actually rings a phone. Email works too and needs no app.

## Before any mode: load the tool

`RemoteTrigger` is a **deferred tool**. It is not callable until its schema is loaded, so every
mode's first tool call fails without this:

```
ToolSearch  query: "select:RemoteTrigger"
```

It needs a claude.ai login. If it refuses with "API accounts are not supported", the fix is
`/login`, not the local fallback.

## Modes

Route on what they asked for. When it is ambiguous, ask which one.

| They say | Mode |
|---|---|
| "set one up", "I want this", nothing exists yet | **setup** |
| "it missed X", "stop showing me Y", "I care about Z now" | **tune** |
| "is it working?", "I got nothing last week" | **check** |
| "turn it off for a while", "turn it back on" | **pause / resume** |

---

## setup

1. **Check they do not already have one.** `RemoteTrigger {action:"list"}` and look for a radar
   already on the account. If one exists, this is almost certainly `tune`, not `setup` — a second
   radar means two digests, two sets of feedback, and neither one improving. Say what you found and
   ask before creating anything.

2. **Confirm whose account this is.** The routine has to live on the account whose mail connector
   reaches *their* mailbox and whose environment holds *their* token. **You cannot create one for
   somebody else**, and a radar built on the wrong account reports a quiet week, cheerfully,
   forever. If the person in front of you is not the account holder, stop here and hand them the
   skill instead.

3. **Interview them.** Follow `references/interview.md` — one question at a time, push back on
   vague answers. Do not skip to writing a prompt because you can guess; the guesses are what makes
   a digest useless. Ten answered questions beat forty assumed ones.

4. **Verify every source URL live** as it comes up, and **read the body, not the status code**. A
   guessed institutional link is the commonest defect in a generated prompt, and a 404 inside a
   routine prompt is invisible until the digest quietly stops covering that source. Some hosts
   return 200 for pages that do not exist, so confirm the page actually contains what you want
   before keeping it. Say plainly which ones failed, and record any that are blocked in a way the
   prompt has to work around.

5. **Set up delivery** per `references/delivery.md` — their Slack app and token, or email. **This
   comes before rendering**, because the delivery block needs a channel ID, a member ID and a bot
   name that do not exist until it is done.

6. **Write their profile and open a changelog.** `<their project folder>/radar/profile.md` and
   `radar/CHANGELOG.md`, in their own workspace, never inside this skill. The changelog starts with
   one dated line saying the radar was created and what it was told to watch; every later `tune`
   appends to it.

7. **Render the prompt** from `references/prompt-template.md`, expanding every `{{PLACEHOLDER}}`.
   Then read it once as if you were the cloud session: it has **no memory, no files, and no context
   but these words**. Anything it needs must be on the page.

8. **Stop on anything unfilled.** `scripts/check_routine_prompt.py --scan <prompt.txt>` fails on any
   `{{` or `<<FILL:` left in the text. A `<<FILL:` marker is a fact only they can supply — a channel
   ID, a member ID, an email — so ask for it now. A radar created with one unfilled fires weekly,
   delivers nothing, and reports success.

9. **Create the routine.** Use the bundled `schedule` skill, or `RemoteTrigger` directly.
   Requirements in `references/routine-mechanics.md`: a **Full network** environment, `allowed_tools`
   covering everything the prompt uses, the right connectors, and a UTC cron.

10. **Fire it once, now** — `RemoteTrigger {action:"run", trigger_id}` — so they see a real digest in
    minutes rather than trusting a promise. Then read the run log and tell them what actually
    happened, including anything that failed.

11. **Save the prompt locally** next to their profile and check it against the live copy with
    `scripts/check_routine_prompt.py`. Report the routine's URL and its next fire time in both UTC
    and their zone.

## tune

This is the mode that makes the radar worth keeping. Expect it often.

Read `references/tuning.md`. **If there is no profile file** — an older radar, or one somebody
else set up — do not stop and do not start over. Reconstruct one from the live prompt
(`RemoteTrigger {action:"get"}` → `derived_state.prompt`), write it to
`<their project folder>/radar/profile.md`, open a changelog beside it, and say that you did.

The shape: **fix the class of miss, not the instance.** "It missed the Kellogg postdoc call" becomes a standing source or a standing question, never a one-off line about that call. Make the smallest edit that would have caught it, push with `RemoteTrigger update`, re-verify the checksum, and append a dated line to their changelog.

## check

1. `RemoteTrigger {action:"list"}` if you do not already have the trigger id — this is also how you
   answer "which routine is mine?".
2. `RemoteTrigger {action:"list_runs", trigger_id}` for the runs.
3. `RemoteTrigger {action:"get_run_log", session_id}` — note the parameter is the **session id**
   from `list_runs`, not the trigger id.

Report: did it fire, did it finish, did the **delivery step** succeed, and what refused to load. A
run whose status is SUCCEEDED can still have delivered nothing — read the delivery step, not the
status. If there are no runs at all, `get` the routine and check `enabled` and `next_run_at`; a
fire refused before a session existed leaves no row, so an empty list is not proof it never fired.

**Never paste a run log through to the person verbatim.** The routine's delivery step is a curl
carrying their bot token, and a verbose failure can put `xoxb-…` in the log. Summarise, and check
for `xoxb-` before quoting any line of it.

## pause / resume

`RemoteTrigger update` with `{"enabled": false}` or `true`. **Deletion is not possible through the API** — it is done at <https://claude.ai/code/routines>, and that page hides switched-off routines, so open the routine by its direct URL and use the dropdown beside its name.

---

## Rules that hold in every mode

- **Never invent a source, a programme, an amount or a deadline.** Not in the prompt, not in a digest, not when answering "is there anything for me this week". "Deadline unverified" is a correct answer; a plausible guess is not.
- **Ask about citizenship and work authorization; never infer it.** It decides which half of the results are real for them. Getting it wrong by assumption is worse than not knowing.
- **Nothing about the person goes inside this skill's own folder.** A skill directory is published
  verbatim to a public marketplace repository, so anything written there becomes public. Their
  profile, their rendered prompt and their changelog live in their own workspace. That file holds a
  legal name, a citizenship status and Slack identifiers, so it also stays out of any report, any
  public repository, and any paste into a shared channel.
- **A token never passes through you.** They create their own Slack app and save their own token. You never read it, print it, or put it in a file.
- **The cloud session has no context.** Every fact the digest depends on must be written into the prompt.
- **Their timezone, their cron in UTC.** Convert, then state both, and check `date -u` before computing anything rather than trusting an assumption about today.
