# The setup interview

Eleven questions, asked **one at a time**, in this order. Wait for each answer. Do not batch them into
a wall of bullets — people answer a wall by skimming it, and a skimmed answer produces a digest
full of things they do not want.

**Push back once on any vague answer.** "Anything relevant", "the usual academic stuff", "whatever
comes up" are not scopes; they produce forty padded items a week and get muted by the third one.
One concrete follow-up, then take what you get and move on. You are not interrogating them, you
are writing down the things only they know.

Verify every URL they give you, and every URL you propose, **live, as it comes up**, reading the
body rather than trusting the status code. A guessed link inside a routine prompt fails silently
forever. A page that is simply wrong gets dropped and you say so; a page that loads for a human but
refuses a fetch stays in as a named hurdle. Either way they hear about it.

---

**1. Who are you, and where in your career?**
Name, institution, department or lab, role, when it started, how long it runs, and what comes next.

The last two matter most. A two-year appointment ending in June 2028 means the application cycle
that matters is the one opening a year before that, and the digest should be counting down to it.

Then, in the same breath: **what do you actually do — methods, software, languages, subject
matter?** The digest has to judge whether a posting fits, and "fits" is unanswerable without this.
Two or three concrete sentences. If they will not give them, say in the prompt that skills were not
captured and that no item may be dropped for a skill the routine cannot verify.

**2. What is the next step you are trying to reach?**
The thing this radar is ultimately in service of — a PhD place, a faculty job, an industry move, a
grant, staying put with better funding. Everything the digest ranks, it ranks against this.

**3. What counts as an opportunity for you, ranked?**
Make them rank. The ranking is the whole digest.

Offer the categories rather than asking them to invent the list, and make it stage-appropriate — a
predoc's ranking looks nothing like an enrolled PhD student's:

- Graduate-programme deadlines, application fee waivers, open houses
- Nationally competitive fellowships (in the US, the NSF GRFP is the one people miss; eligibility
  is narrow and a predoc year is often the last one that qualifies — **ask, do not assume**)
- Summer institutes and methods training (SICSS, ICPSR, IPUMS and their equivalents)
- Grants, small awards, prize competitions, conference travel funding
- Internal institutional funding, certificates, designated emphases, institute affiliations
- Research-assistant and analyst roles, and pipelines from one into a programme
- Industry roles and internships
- Calls for papers and conference deadlines

Then: **what do you never want to see?** A muted radar is a dead radar, and the fastest way to get
muted is one recurring category they do not care about.

**4. Which companies, labs, programmes or people are already on your list?**
Ask this outright. Named targets are the highest-yield thing in the whole prompt: the routine can
check each one's own careers or admissions page by name every run, which is far more reliable than
hoping a search surfaces it. Get the URL for each. Anything with no URL, find it now or drop it.

**5. What is your citizenship and work-authorization situation?**
Ask. Never infer it from a name, an institution, or anything else.

You need enough to write the lane rules: which opportunities need no authorization at all, which
their status already permits, and which it does not. If they are on a visa, ask which one and
whether any current policy affects it — that becomes a thing the routine re-checks every run,
because a change there unblocks a whole lane at once.

If they would rather not say, write the lanes generically and have the digest quote every
citizenship gate verbatim without judging it. That still beats silence.

**6. Which mailing lists and newsletters reach you, and in which mailbox?**
Departmental lists, graduate-school news, institute announcements, scholarly societies, job
digests. Get sender addresses or list names where they can.

Get the **address itself**, not just "my Gmail" — the delivery block's email fallback needs it.

Then the question people forget, and the highest-consequence one in this interview: **is the mail
connector on your claude.ai account attached to *that* account?** A routine reading the wrong
mailbox reports a quiet week, every week, forever, and looks healthy doing it.

If they already have a routine, read `mcp_connections` off it (`RemoteTrigger {action:"list"}`).
If this is their first, there is nothing to read, so the check moves to the **first live run's
log** — which is why setup fires the routine once and reads the log rather than trusting the
create response.

**7. Which of your institution's own pages should it watch?**
Their department, graduate school, and the institutes and centres they could plausibly affiliate
with — the ones that run fellowships, certificates, working groups and training programmes.

Do not ship a list you guessed. Search for each one, open it, and **read the body** — some hosts
return 200 for pages that do not exist, so a status code proves nothing. Keep the ones that
actually carry announcements; a centre's news or events page is usually a better source than its
front page.

Record in the profile *why* each URL was chosen over the obvious alternative. A later tune that
sees a bare link cannot tell whether the front page was rejected on purpose or never tried.

Two outcomes, and they are different: a page that **404s or is simply wrong** gets dropped, and you
say so. A page that **loads for a human but refuses a fetch** — a bot-block, a login wall, a
JavaScript-only page — stays in the prompt as a named hurdle with the workaround, because the
digest should keep reporting that it cannot see it.

**8. Where should the digest arrive, and when?**
Slack workspace and channel, or email. Their timezone. A weekday and hour.

Weekly is the norm. The cron minimum is one hour, and expressions are UTC — convert their local
time yourself, state both, and remember the offset shifts under daylight saving, which can push a
notification into the small hours six months later.

Get their **IANA timezone**, not just a city — the cloud session runs in UTC, and without the zone
written into the prompt every window it computes is quietly wrong.

Ask about quiet hours, and then use the answer: pick a fire time with an hour of room on either
side of their do-not-disturb window, so the daylight-saving shift cannot push the ping into it. A
notification that arrives inside a do-not-disturb window is not a notification.

**9. Describe a week where this earned its place.**
What was in it? This answer becomes the shape of the digest's lead section.

**10. What would make you mute it?**
The honest answer is usually volume, or one irrelevant category repeating. Whatever they say,
write it into the prompt as an explicit prohibition — it is the most load-bearing sentence in the
whole thing.

**11. Three numbers, offered rather than asked.**
Propose them, say why, and let them push back: how far ahead to look (60 days minimum for dated
deadlines, a year for annual cycles, six weeks for anything ticketed), what counts as urgent (30
days is usual), and the cap on items per digest (their answer to question 10 usually sets it).

They are defaults, not discoveries. Record them in the profile as chosen rather than asked, so a
later session changes them deliberately instead of re-deriving them from scratch.

---

## After the interview

Write `<their project folder>/radar/profile.md` — their workspace, never inside this skill and
never inside anyone else's tree. Every later `tune` starts by reading it, so it has to say more
than what they answered. Four sections earn their place beyond the answers themselves:

- **Sources verified**, with the date — which loaded, which failed and why, and which are blocked
  in a way the prompt now works around.
- **Sources you added that they did not name**, flagged for approval. You will usually find good
  ones during verification. They are still yours, not theirs, until they say so.
- **Parameters chosen rather than asked** — the item cap, the mail window, the look-ahead. Say what
  you picked and why, so a later session changes it deliberately instead of re-deriving it.
- **Blockers** — every `<<FILL:` marker left in the prompt, and what it needs. The routine cannot
  be created while any remain.

Then work through the placeholder key at the end of `prompt-template.md` and fill every row. Most
transcribe from an answer. A few you construct, and the key marks them:

- `{{ELIGIBILITY_LADDER}}` — three tiers from answers 1 and 3, named in their own terms. The one
  worth real thought; lesson 3 in `standing-lessons.md` says why.
- `{{AMBER_DEFINITION}}` and `{{RED_DEFINITION}}` — from answer 5, collapsing any lane that cannot
  apply to this person rather than shipping an empty heading.
- The three numbers from question 11.

Anything you cannot fill from an answer becomes a `<<FILL:>>` marker and a blocker, never a guess.
