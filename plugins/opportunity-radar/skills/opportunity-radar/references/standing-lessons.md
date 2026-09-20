# The ten standing lessons

Every generated routine prompt carries all ten. They are not style preferences — each one is a
repair for a specific way an automated digest wasted somebody's time or quietly lied to them.

**The template owns the wording; this file owns the reasons.** `prompt-template.md` carries the
operative sentences in the right structural place, and the column below says where. When the two
disagree, the template is right and this file is stale — fix it here rather than editing a digest's
instructions from memory. Use this file when **rendering** (to check all ten survived, by reading
what the template actually says at each location, not by confirming the section still exists) and
when **tuning** (to work out which lesson a complaint belongs to before writing a new rule).

This file is never edited per person. Everything specific to someone lives in their rendered prompt
and their profile.

| # | Lesson | Lives in the template |
|---|---|---|
| 1 | Keep a tally, disclose it | `## Sweep` preamble + `How this was made` line |
| 2 | End with the hurdles | `Method` section of the digest |
| 3 | Calibrate to career stage | `## Where {{NAME}} is` + eligibility labels on every item |
| 4 | Lane-label work authorization | `## Work authorization` |
| 5 | Look ahead as far as booking opens | `## Sweep` item on horizon |
| 6 | Read their mail as a source | `## Sweep` item 1 |
| 7 | A standing programmes item | `## Sweep` item on programmes |
| 8 | Never invent anything | `Rules` under the digest structure |
| 9 | Specific beats comprehensive | `Rules` |
| 10 | Delivery discipline | `## Delivery` |

---

**1. Keep a tally from the first tool call, and open the digest with it.**
Pages opened, searches run, mail threads read, hosts that refused, clock time start to finish. One
italic line under the title: *Swept your mail (6 threads) and 14 pages in 9 min · 12 searches · 2
hosts would not load.*
*Why:* without it the reader cannot tell a thorough quiet week from a lazy one, and so cannot tell
the radar what to change. *An honest small number is worth more than a flattering one* — the prompt
must say to leave a number out rather than estimate it.
*Working when:* the numbers differ run to run and sometimes look bad.

**2. End with a hurdles list.**
Every host that would not load, with the reason — 429 bot-block, JavaScript-only, timeout, 404,
login wall — and what the user could do to unblock it.
*Why:* a page that silently fails looks exactly like a page with nothing on it. A user who learns
that one source 403s every week can hand over a cookie, pick another source, or check it by hand.
*Working when:* the digest names hosts, not "some sites were unavailable".

**3. Calibrate to career stage, and quote the eligibility line verbatim.**
Label every item with a stage tier from `{{ELIGIBILITY_LADDER}}` — open to them now, or gated, and
on what. Quote the posting's own sentence rather than summarising it.
*Why:* **this is the commonest way a digest of this kind wastes someone's time** — listing
prestigious things they cannot apply to for three years. The tiers are not universal: a predoc's
ladder (open to anyone with a bachelor's / needs current graduate enrolment / needs the degree in
hand) is a different ladder from a first-year PhD student's. Build it in the interview.
*Working when:* a reader can skip to "open now" and find real items there.

**4. Lane-label work authorization, quote every citizenship gate, hunt the unfunded track.**
Three lanes: no authorization needed (grants, fellowships, awards, training); employment their
status already permits; employment it does not. Report all three — application timelines run a year
ahead — and say plainly when authorization is unresolved.
*Why:* eligibility gates hide. The worked example: an NIH T32 stipend is citizen-only, but the same
programme's *trainee scholar* track takes non-citizens and is never on the front page. So the rule
is quote the gate verbatim **and then go looking for the track underneath it**.
*Never transplant one person's immigration facts into another person's prompt.* Ask.

**5. Look ahead as far as booking or application opens.**
Sixty days minimum for deadlines; a year for programme cycles; six weeks for anything ticketed.
*Why:* a one-week window is why a radar misses the things a friend catches. The friend heard about
it in September for an event in October.

**6. Read their mail as a source, not only as a cross-check.**
Named lists and newsletters, every run, for the whole window — not just to confirm or cancel what
the web already said.
*Why:* in academia the real announcements arrive by email weeks before they are on any page, and
some never reach a page at all.

**7. Carry a standing "programmes, certificates, designated emphases, institute fellowships" item.**
Check the named institutional sources every run for new calls, even when nothing prompts it.
*Why:* this is the class of thing people hear about from a friend rather than find by searching.
It has no job board and no feed. If the sweep does not go and look, it never appears.

**8. Never invent a programme, an amount, or a date.**
"Deadline unverified" is the correct output when it cannot be confirmed. Every item needs a real
link and a real date.
*Why:* a fabricated deadline is worse than no digest. The reader acts on it.

**9. Specific beats comprehensive.**
Ten real items beat forty padded ones. **A genuinely quiet week is a three-line digest, not
manufactured activity.** The prompt must say this outright, or the model will pad.

**10. Delivery discipline.**
Post as a bot, then send a one-line DM ping; retry once; fall back to a DM carrying the whole
digest; email last. Never post twice.
*Why:* a post authored as the user notifies nobody. And a fallback that reports its own failure
*through the silent channel* is not a report — two digests once sat unseen for a fortnight because
the "delivery failed" notice was inside the undelivered message. Whatever announces a failure must
travel by a path that actually rings.
*Also:* if a Claude bridge answers messages in the destination channel, a post authored as the user
would make the bridge answer its own digest.
