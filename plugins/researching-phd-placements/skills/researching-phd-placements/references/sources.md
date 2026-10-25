# Sources: what to pull, in what order, and how to get past each wall

Tested on Princeton English (Oct 2026, 110 graduates) and Berkeley social-personality (Oct 2026, 41).
Institution-specific notes are examples of what to look for at the next school, not a checklist.

## 1. The denominator (who graduated)

Classify every program page before using it:

| Page type | Looks like | Use it for | Never use it for |
|---|---|---|---|
| **Roster / register** | "Degrees awarded", "PhD graduates", dissertation lists by year, often with titles and committees | the denominator; degree year; committee | primary adviser (committees are often alphabetical); jobs |
| **Outcomes / placement** | "Placement", "Doctoral outcomes", one job per person | leads for jobs | the denominator (selective, drops people); first jobs (it is overwritten with later jobs); current jobs (stale) |
| **Lab alumni / adviser CV advisee lists** | curated by the lab | adviser leads, area membership | the denominator (survivorship) |

- **Find who the roster misses.** Defense / "final public oral" announcements and department emails list people who
  defended after the roster was last updated. Register years can lag the real conferral year by up to a year (Berkeley:
  2015 dissertations listed under 2016); keep both and use the dissertation/CV year.
- **Area- or lab-level scopes** (e.g. "the social area", "one professor's students"): the department register covers every area.
  Classify each name with evidence codes, as Codex did for Berkeley: I (explicit in-area evidence), I? (inferred),
  E (explicit other area), E? (inferred other), U (unresolved). Keep E/U rows visible in the report.
- **No roster page at all:** build one from the dissertation repository (department + year), ProQuest, the library
  catalog, or commencement programs; cross-check against every outcomes-page snapshot.
- **Count check:** federal completions data (IPEDS Completions by CIP code, e.g. 54.0101 History or 23.0101 English,
  "doctor's degree – research/scholarship"; NSF's Survey of Earned Doctorates) gives doctorates per year with no names.
  A per-year roster count far off it means a missing source or a program-boundary question (separate programs, joint
  degrees) — settle that before fanning out. (Suggested by a test run; not yet used in a real run.)

## 2. Primary adviser (official record first)

1. Institutional repository advisor field: DSpace `dc.contributor.advisor` (item page `?mode=full`), eScholarship/ProQuest
   "Advisor". Princeton: DataSpace JSPUI `simple-search?query=author:"Surname" AND English`, then `?mode=full`; it
   sits behind an automatic ALTCHA proof-of-work page that passes on its own in Chrome (never solve an interactive one).
2. Library catalog notes ("Advisor: X"). Princeton: `catalog.princeton.edu/catalog.json?q=...` then
   `/catalog/<id>.json`, field `notes_display`; only ~2019+ records carry it.
3. Dissertation front matter / acknowledgments (PDF), the person's CV ("chair"), the adviser's CV advisee list.
4. Lab pages last.

Rule used in both docs: the first-listed adviser (or the chair) is primary; every other listed adviser is secondary and
gets the highlighted duplicate. Not deposited yet → "主导师尚未公开" section with the committee.

## 3. Attrition / completion (the "do they fail PhDs" question)

- **Graduate-school program metrics.** Princeton: Graduate School "Ph.D. Completion and Cohort Analysis" Tableau dashboard
  (`tableaupublic.princeton.edu/t/GraduateSchool/views/Ph_D_CompletionandCohortAnalysis/...`), per-department
  completed / attrited / continuing by entering cohort, plus a Humanities and all-school benchmark. Cornell (graduate field
  metrics), Indiana ("Ph.D. Metrics"), and the UC system (UCOP doctoral persistence & completion dashboards) publish
  similar data; AAU's PhD Education Initiative pushes members to. Look for "program metrics", "completion and attrition",
  "time to degree" on the graduate school's site.
- **Department cohort sheets** ("PhD Outcomes by Cohort" PDFs; Princeton's were public Drive files linked from the
  outcomes page, later removed — Wayback has them).
- **APA-accredited clinical programs** publish "Student Admissions, Outcomes, and Other Data" with attrition; other
  psychology areas usually don't.
- Report the source's own definition (Princeton's "attrited" lumps voluntary withdrawal with termination) and the
  denominator. Absent data, say so; "no job found" is never attrition.

## 4. First jobs the outcomes page overwrote

- **Wayback history of the outcomes page**, roughly one snapshot per year, including older URLs from site redesigns
  (find them with the CDX API: `web.archive.org/cdx/search/cdx?url=<domain>/<path>*&output=json&fl=timestamp,original&collapse=digest`).
  Raw snapshots: `https://web.archive.org/web/<YYYYMMDD>id_/<url>` with `curl -L --compressed`, paced (429s otherwise).
  Diff every snapshot against the current page: Princeton's Sept 2025 copy showed first jobs (e.g. Princeton postdocs)
  that the 2026 page had replaced.
- **Department newsletters and annual reports** often list each year's placements by name (Princeton: Fall 2015–18
  newsletters, annual reports' "Graduate Outcomes"); "graduate outcomes" news posts.
- **Department emails** Jacob forwards: date them from their content (the jobs' start years), not from a guess.

## 5. Careers (agents; order in references/agent-brief.md)

CVs > faculty/staff pages and university news > dated author bios > ORCID API > search-engine LinkedIn snippets >
RocketReach/TheOrg/ZoomInfo (secondary) > Wayback for dating. Notes:
- **LinkedIn:** never opened except through Jacob's reading account after verifying its name in the feed (memory
  `feedback-linkedin-reading-account-only`); Chrome is normally signed in to his own account. Snippets on a results page
  are fine. A LinkedIn read is the gold standard for alt-ac/industry careers — list what it would settle.
- **Search engines under parallel load:** Google CAPTCHAs every agent tab within minutes; DuckDuckGo/Brave/Mojeek bot-wall.
  Bing and Yahoo results pages in Chrome keep working. Bing's AI summaries were wrong 3 times in one run (leads only).
  Never solve a CAPTCHA. A single slow tab can use Google again ~2 h later.
- **WebSearch** accepts personal names most of the time (52 of 55 agent queries in one run) but strips the name on a
  few; it has a 200-call cap per session shared with subagents — budget ~15–20 per agent.
- **RocketReach** profiles render in Chrome (WebFetch 403s); one JS call collecting `li` text containing "(Month YYYY"
  returns the dated job list. Secondary source; label it.
- **ORCID:** `pub.orcid.org/v3.0/search/?q=family-name:X+AND+given-names:Y`, then `/v3.0/<id>/employments`,
  header `Accept: application/json`.

## 6. Walls and workarounds

| Wall | Workaround |
|---|---|
| Cloudflare on university sites (curl gets a challenge) | read in Chrome (`get_page_text`, in-page `fetch` loops), or Wayback `id_` copies |
| Wayback 429 / connection resets | https, `-L`, sleep 2–5 s between calls, retry later |
| Claude-in-Chrome JS output blocked when it contains query strings / URLs with params | return only IDs or strip the query part |
| JS output truncates near 1,000 chars | write results into `document.body` and `get_page_text`, or return in chunks |
| Claude-in-Chrome can't open `file://` | headless Chrome screenshot with `--use-mock-keychain --password-store=basic` |
