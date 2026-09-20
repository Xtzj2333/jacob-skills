# tune — turning feedback into a better radar

This is the mode that decides whether the radar survives its first month. Every digest is a chance
for the person to say what was wrong with it, and each of those sentences is worth more than
anything you could have guessed at setup.

## The move

**Fix the class of miss, not the instance.**

> "It missed the Kellogg postdoc call."

The wrong edit adds a line about that call. It is already past; the routine will now carry a dead
sentence forever and still miss the next one.

The right edit asks *why the sweep could not have found it*, and repairs that:

| Why it was missed | The edit |
|---|---|
| The source was never listed | Add the page to the named targets or institutional sources — verified live |
| The source was listed but would not load | It is already in Method as a hurdle. Find another route to the same information, or tell them what would unblock it |
| It arrived by email and the sweep read mail only for confirmations | Strengthen the mail item; add the list by name |
| It was outside the look-ahead window | Widen `{{LOOKAHEAD}}` |
| It was found but dropped as ineligible | The eligibility ladder or the lane rules are wrong. This is the most valuable kind of miss — fix the ladder |
| It was found and cut for length | Raise `{{ITEM_CAP}}`, or re-rank the categories |
| It is a whole category nobody listed | Add it to the ranked categories, and ask what it displaces |

"Stop showing me X" is the same move in reverse: put X in `{{EXCLUSIONS}}` as a named prohibition,
not as a softened preference. A category that keeps appearing after they asked twice is how a radar
gets muted.

## The loop

1. **Read their profile file first** (`<project>/radar/profile.md`). It says what the routine was
   told, which URLs were verified, and what was already tried. Tuning without it re-opens settled
   questions.
2. **Get the live prompt.** Load the tool first (`ToolSearch query:"select:RemoteTrigger"` — it is
   deferred), then `RemoteTrigger {action:"get", trigger_id}` → `derived_state.prompt`. Work from
   that, never from a local copy you have not checked: someone may have edited it in the web UI.
   **Save the response to a file as you receive it** — the checksum check in step 6 needs it.
3. **Make the smallest edit that would have caught it.** Resist rewriting the prompt because you
   can see other things you would do differently. A prompt that changes wholesale every week cannot
   be debugged.
4. **Verify any new URL live** before it goes in.
5. **Push** with `RemoteTrigger {action:"update", trigger_id, body}`, where the new text goes at
   `body.job_config.ccr.events[0].data.message.content`. The full body shape, including the
   required `role` and the fresh v4 `uuid`, is in `routine-mechanics.md` — an update sends
   `job_config` whole rather than patching one field.
6. **Verify.** Before pushing: `check_routine_prompt.py --scan <prompt.txt>` (blocks on any `{{` or
   `<<FILL:`) and `--strip` to remove the trailing newline the API discards. After pushing:
   `check_routine_prompt.py <saved-response> <trigger_id> <prompt.txt>`, which must print MATCH.
7. **Append one dated line** to `<project>/radar/CHANGELOG.md`, which setup created. One line per
   change, newest last:

   ```
   2026-09-20 — "it missed the Kellogg postdoc call" → added Kellogg doctoral hub to named
                targets (verified live). Lesson 7. Next run will check it by name.
   ```

   Date, what they said in their words, what changed, which lesson, and what will be different.
   Six months on this is the only record of why the prompt looks the way it does.
8. **Say what will be different next run**, in one sentence, so the claim is falsifiable.

## When the complaint is "it found nothing"

Before editing anything, check whether it *ran*: `list_runs`, then `get_run_log`. A silent radar is
usually broken, not empty. The four common causes, in the order they occur:

- Network access on the environment is Trusted, not Full, so every page fetch was blocked.
- The mail connector is attached to a different account from the one the mailing lists reach.
- The bot is not in the channel, so a "successful" run delivered nothing.
- It genuinely was a quiet week — in which case the digest should have said so in three lines, and
  the Method line should show a real tally. If the tally is missing, lesson 1 is not landing.

## When they stop responding to digests

Ask once. The usual answers are volume, a repeating irrelevant category, or arrival time. All three
are one-line edits. A radar nobody reads should be paused rather than left running.
