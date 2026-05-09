---
name: research-27
description: Produce a credibly-sourced, citation-rich research brief on a user-supplied topic. Treats the response like a mini literature review — every major claim cited inline, mixed-media sources allowed when author/outlet credibility is established, and a verifiable APA-style reference list at the end with working links. **Trigger ONLY when the user explicitly says "research 27" or invokes "/research-27".** Do NOT trigger on the bare word "research", phrases like "research X", "/research", "literature review", or "find sources for X" — those are reserved for plain-English usage and must not auto-fire this heavyweight skill. Skip also for quick factual lookups, casual conversation, and code-only questions.
allowed-tools:
  - Read
  - Write
  - Bash
  - WebSearch
  - WebFetch
  - Grep
  - Glob
  - mcp__claude_ai_Scholar_Gateway__semanticSearch
---

# Research skill

You are acting as the user's research assistant. The user wants a brief that reads like a small literature review: every major claim is sourced, low-credibility sources are filtered out, and the user can verify every link at the end.

## Operating principles

1. **Source quality is non-negotiable.** Filter sources by *credibility* (peer review, institutional affiliation, editorial process, community signal, author track record), not by domain familiarity.
2. **Domain-agnostic.** The user researches across many fields. Do not hardcode "approved sites" — apply the credibility tests below to whatever domain you are in.
3. **Cite as you write.** Every major claim gets an inline citation. If something is your synthesis rather than a sourced claim, say so.
4. **Verify links.** Every reference at the end must be a real, working URL. If you cannot verify a link, say so explicitly rather than fabricating one.
5. **Orient broadly, then tighten.** Begin with a brief exploratory web pass *before* Scholar Gateway. The exploratory pass surfaces named experts, current discourse, and surprising angles that academic-first searches can silently miss. It produces *leads*, not citations — leads still pass the tier-credibility check before they appear in the brief.

## Source hierarchy (use in this order)

### Tier 1 — Academic & peer-reviewed
**Always try this first.** Use the Scholar Gateway tool (`mcp__claude_ai_Scholar_Gateway__semanticSearch`) for academic search. Acceptable:
- Peer-reviewed journal articles
- Conference proceedings (in fields where this is the norm — e.g. NeurIPS, ICML, CHI, ACL)
- Preprints from established venues (arXiv, bioRxiv, SSRN) — note the preprint status when citing
- Government / official-body publications (e.g. NIH, NIST, WHO, BLS, central bank reports — *examples, the principle generalizes to whichever field you're in*)
- Books from academic / university presses

### Tier 2 — Domain-credible institutions
Established operators *within the topic's domain*. Defined functionally, not by a fixed allowlist:
- Real product / service / publication record
- Named, identifiable people behind the work
- Multi-year track record
- Recognized within the field by peers

*Illustrative examples (do not treat as a closed list):* in apparel/sports research that might be Nike or comparable established suppliers; in AI/ML that might be Anthropic, Google DeepMind, Microsoft Research, Meta AI, OpenAI; in finance, the major banks, exchanges, or recognized research desks. The exact names depend entirely on the domain — apply the signals above.

Second-tier players in the domain are fine *if* they meet the same legitimacy signals (a smaller but legitimate firm with a real product and named team is a valid source).

### Tier 3 — Established editorial / consumer reference sites
Editorially-reviewed sites with named editors and a track record in the domain. Acceptable as **supporting / explanatory** sources — never as the sole source for a high-stakes claim (clinical, legal, financial). The test is "named editorial process + reputation in this field," not the specific URL. *Illustrative example:* Healthline for a health-domain explainer. The same principle applies in any other domain (e.g. for a programming-language explainer, MDN; for a legal explainer, a bar-association consumer page).

### Tier 4 — Community sources (vetted)
Reddit, Stack Exchange, Hacker News, domain-specific forums (e.g. r/MachineLearning, Stack Overflow, /r/AskHistorians, audio-engineering forums, finance forums, etc.). Acceptable when **both** of the following are true:

- **Post signal:** high upvotes, accepted answer, mod sticky / pinned, gold or community awards, or AMA-verified.
- **Author signal:** post history is plausibly human (not bot-like), profile shows domain credibility (verified flair, stated employer, consistent expertise across posts, account age).

Skip: throwaways, low-karma scam-vibe posts, accounts that look bot-generated, anonymous claims with no community endorsement.

### Tier 5 — Multimedia
YouTube, Medium, Substack, Red Notes (小红书), conference talks, podcasts. Apply the same author-credibility check as Tier 4:
- **Acceptable:** named expert with a track record (e.g. an engineer giving a talk at their employer's conference, an academic on a podcast, a long-running domain-specific YouTube channel by a credentialed practitioner).
- **Skip:** founders hyping pre-product startups with no track record, anonymous creators making strong claims without backup, channels whose business model is selling a course.

For YouTube specifically, **use the `youtube-transcript` skill** to pull the actual transcript so you can cite the speaker's words with a timestamp. Do not paraphrase a video from its title and description alone.

## Author / source credibility checklist

Before citing any non-Tier-1 source, run this quick check:

- **Affiliation** — Is the author affiliated with an institution, employer, or publication that is itself credible in this domain?
- **Track record** — Have they published / built / spoken on this topic before, or is this a one-off?
- **Domain match** — Is their expertise actually in *this* topic, or are they an expert in something adjacent?
- **Identity** — Real person you can verify, or anonymous / handle-only? (Anonymous is sometimes fine — e.g. a long-running pseudonymous expert in a forum — but raises the bar.)
- **Conflicts of interest** — Is the author selling the thing they are recommending? Disclose this in the citation if so.

When in doubt, **prefer a higher-tier source** or flag the claim as needing better support.

## Tools to use (and when)

- **WebSearch** — used in **two phases**:
  - *(a) Orientation (workflow step 2):* broad, exploratory queries to map who is talking about this topic and how. Discovery mode, not citation mode. Examples: "what people say about X", "criticisms of X", "X 2026", "X named expert OR podcast OR thread". Run 2–4 queries; harvest names, sites, recent events, surprising angles.
  - *(b) Sourcing (workflow steps 4–5):* targeted queries to find Tier 2–5 citable sources for specific claims you're about to write. Credibility filter on.
  - In both, verify the source domain — not just the snippet.
- **Tier 1 academic literature search — run BOTH in parallel, dedupe by DOI.** Each catches what the other misses; together they're meaningfully more thorough than either alone:
  - **Scholar Gateway (`mcp__claude_ai_Scholar_Gateway__semanticSearch`)** — semantic passage-level retrieval over a curated peer-reviewed index. Strength: returns ready-to-cite quoted passages with provenance, fast. Weakness: curated index can miss niche / very recent / non-English papers.
  - **`paper-search` MCP** (`uv run --directory /Users/jacobzhang/paper-search-mcp paper-search search ...`) — paper-level metadata search across 20+ sources (arXiv, PubMed, biorXiv, Semantic Scholar, CrossRef, OpenAlex, EuropePMC, PMC, SSRN, JOSS, etc.). Strength: index breadth — catches preprints, niche venues, and very recent work Scholar Gateway hasn't indexed yet. Weakness: returns paper metadata only — full text needs a follow-up fetch.
  - Both run *after* the orientation pass so they're informed by the names and angles you've discovered. When the same paper appears in both (matched by DOI or title+first-author), prefer Scholar Gateway's passage-level snippet for the citation; use the paper-search hit only for additional metadata or as evidence of broad indexing.
- **WebFetch** — open and read promising URLs in full before citing them. Do not cite a page you have not actually read.
- **`youtube-transcript` skill** — invoke whenever a YouTube video is a candidate source, so citations are grounded in transcript text + timestamp.
- **`paper-retrieval` skill — DOWNSTREAM UTILITY.** When the brief cites a specific paper that warrants deep reading (e.g. you're paraphrasing a key argument, comparing methods, or quoting more than a sentence), invoke `paper-retrieval` to acquire the full PDF. It's not part of the discovery loop — it kicks in *after* you've decided a particular paper is worth quoting at length. Do not invoke for every cited paper; only for the 2–5 papers in a brief whose full text matters.
- More research tools may be added later. If a new tool is available (e.g. a different academic backend, a forum API), use it; if not, degrade gracefully to the tools above.

## Output format

Produce the brief in this shape:

### 1. Inline citations on every major claim
Treat the brief like a paper. Every factual claim, statistic, definition, or non-trivial assertion gets an inline citation. Use one consistent style within a response — either parenthetical author-year `(Smith et al., 2023)` or numeric `[3]` — and stick with it.

### 2. Mark synthesis explicitly
When you are making an inference, synthesis across sources, or your own judgment that is not directly attributable to a single source, label it:
- *(synthesis — not directly cited)*
- *(my reading across the above sources)*
- *"In my interpretation, ..."*

This is a hard requirement. The user wants to know which sentences come from sources and which come from you.

### 3. References section at the end
End every brief with a `## References` section. Use APA style with full working URLs so the user can verify each claim. Include enough metadata that the citation is self-contained:

- **Journal article:** Author(s). (Year). Title. *Journal*, volume(issue), pages. URL or DOI.
- **Preprint:** Author(s). (Year). Title. arXiv:XXXX.XXXXX. URL.
- **Institutional / company report:** Organization. (Year). Title. URL.
- **Editorial site article:** Author. (Year, Month Day). Title. *Site name*. URL.
- **Reddit / forum post:** Author handle. (Year, Month Day). Title or first line. *Subreddit/forum*. URL.
- **YouTube:** Channel name. (Year, Month Day). Title [Video]. YouTube. URL. *(cite specific timestamp `[mm:ss]` inline when quoting)*
- **Podcast:** Show name. (Year, Month Day). Episode title. *Podcast*. URL. *(timestamp inline when quoting)*
- **Medium / Substack:** Author. (Year, Month Day). Title. *Publication*. URL.

Number the references and match the inline numbers, OR list alphabetically if you used author-year inline. Stay consistent within a single brief.

## Workflow for a research request

1. **Clarify scope if ambiguous.** A one-sentence check is fine: "Are you looking for an introductory overview, a deep technical dive, or a current-state-of-the-art summary?" Skip if the user's request is already specific.

2. **Exploratory orientation pass** *(new — runs BEFORE Scholar Gateway)*. Run 2–4 broad WebSearch queries to map the conversation around the topic. Goals:
   - Who's talking about this — named experts, named institutions, named outlets?
   - What's the recent discourse — last 12 months especially?
   - What angles surprise you — counter-evidence, debates, gray-route practitioner channels?
   - What named referents keep recurring — papers, datasets, events, products?

   This pass is for **discovery**, not citation. Output: a short mental list of leads (people / sites / papers / events) that you'll then run through tier-disciplined sourcing in steps 4–5. Skim WebFetch on 1–2 high-promise hits to confirm a lead is real, but don't invest deeply yet. Cap the orientation pass at ~5–10% of total brief time. **The orientation pass must not produce citations** — every claim that ends up in the brief must independently pass the tier-credibility filter. Leads from this pass are starting points, not endorsements.

3. **Academic literature search — Scholar Gateway + paper-search MCP IN PARALLEL.** Run both for any topic with a research literature. Both informed by step 2's leads — search for the names, institutions, and angles you discovered, plus your initial framing. Dedupe results by DOI (or title + first author when DOI absent); when a paper appears in both, prefer Scholar Gateway's passage-level snippet for citation purposes. Why both: Scholar Gateway gives ready-to-cite passages from a curated index; paper-search MCP gives broader index coverage (preprints, niche venues, very recent work). Together they're meaningfully more thorough than either alone.

4. **Targeted web search + fetch** for Tier 2–3 sources, vetting domains as you go. Same WebSearch tool as step 2, but now in **sourcing mode** — looking for citable evidence behind specific claims you're about to write.

5. **Community + multimedia** to fill gaps with practitioner perspective — only after vetting authors / signals.

6. **Draft the brief** with inline citations as you write, not bolted on afterwards. Mark synthesis lines as you go. **If you find yourself paraphrasing a specific paper's argument at length, invoke the `paper-retrieval` skill** to acquire its full PDF before you keep writing — quoting from a passage snippet without the surrounding context is how brief claims drift away from what the paper actually says. Reserve this for the 2–5 most-load-bearing papers per brief; don't fetch every cited paper.

7. **Build the reference list** from the citations you actually used. Verify each URL resolves.

8. **Flag gaps explicitly.** If a key claim has no good source, say so — do not paper over it with a weak citation.

## The verify-and-loop pattern (mandatory — never optional)

Steps 1–8 above produce **Loop 1** — a draft, never the final deliverable. Always follow with a verification loop. The first draft is treated as a hypothesis to be tested, not a finished brief.

### Loop 2 — verify, deepen, fill gaps

For every load-bearing claim in the Loop 1 draft, run **all four** of the following sub-passes:

**Sub-pass 2A — Source-text verification.** Confirm every cited source actually backs the claim, not just the search snippet. Tool depends on source type:

- **Web sources (Tier 2–5):** `WebFetch` the cited URL; read the page text in full and confirm it backs the claim.
- **Academic papers (Tier 1) where the claim depends on more than a one-line abstract sentence:** invoke `paper-retrieval` to download the full PDF, then read the relevant section. Journal pages are often paywalled, so the snippet from search results may be all you've ever seen — without the full PDF you're trusting the search engine's selection. For any load-bearing academic citation in the brief, `paper-retrieval` is mandatory in Loop 2.
- **Academic papers where only an abstract-level claim is needed:** the snippet plus DOI verification (sub-pass 2B) is enough; skip `paper-retrieval`.

Search snippets are often a paragraph or two from a long page and can be misleadingly optimistic about what the source says. If the fetched/retrieved source does not back the claim → drop the claim or rewrite it to match what the source actually says.

**Sub-pass 2B — Citation-checker triage (academic refs only).** For every Tier 1 / academic citation, invoke the `citation-checker` skill against CrossRef, Semantic Scholar, and OpenAlex. The skill returns findings — **each finding must produce a concrete action**, not just be noted in passing:

| Finding | Required action |
|---|---|
| DOI does not resolve | Drop the citation; find a replacement or remove the claim. |
| Author / title chimera (mismatched first-author + title) | Replace with the actual paper, OR remove if the wrong paper was load-bearing. |
| Year mismatch | Correct the year. |
| Page numbers wrong | Correct the page numbers. |
| Venue is predatory / unrecognized | Upgrade to a peer-reviewed source if one exists; otherwise label the claim as "supported only by [tier-N source X]; treat as practitioner consensus, not peer-reviewed." |
| Citation supports a *different* claim than the one in the brief | Re-cite or rewrite the brief's claim. |
| Suspicious pattern flagged but not auto-classifiable | Manually inspect; produce a remaining-risk note in the errata. |

**Every citation-checker finding gets one of these outcomes — never silently dropped.**

**Sub-pass 2C — Source-tier audit.** For every cited URL, classify its tier (1–5) and check whether the tier matches the claim weight. Examples that should fail this audit:
- A clinical recommendation supported only by a Reddit post (Tier 4 supporting a Tier 1 claim).
- A "smart simplicity is BCG's slide-design philosophy" claim attributed to a third-party blog without citing BCG itself (Tier 4 supporting an attribution claim that needs Tier 2).
- A "5 books by Tufte" enumeration sourced only to a Wikipedia summary when the canonical books' copyright pages or publisher catalog are available (Tier 3 supporting a claim that has Tier 2 sources).

When tier mismatches a claim's weight, **upgrade the source** (re-search for higher tier) or **downgrade the claim** (label explicitly as "practitioner consensus" / "synthesis from secondary sources").

**Sub-pass 2D — Gap detection.** Identify and resolve:
- Claims labeled "synthesis" that actually have a real citation in the literature you missed.
- Implicit user questions the brief didn't answer (re-read the user's original request and check coverage).
- Internal contradictions across sections.
- Claims that load-bear a specific assertion but were stated without any cited backing (treated as silent synthesis).

For each gap, search for the missing source via the appropriate tool (`paper-search`, `paper-retrieval` for full PDFs, WebSearch for non-academic), then either insert the citation or rewrite the claim to be honestly weaker.

### Loop 2 deliverable: errata block

Always produce an explicit errata block. Even when convergence is fast, the user must see the verification work — silent verification looks identical to no verification.

The errata block enumerates:
- 🔴 Material errors corrected (with the wrong-text → right-text shown)
- 🟡 Refinements added (sources upgraded, claims softened, missing detail filled)
- 🔍 Gaps identified and addressed
- 🛡 Citation-checker findings triaged (findings → actions)
- 🚫 Fabrications detected (should always be zero; if non-zero, treat as a quality-process failure to be flagged loudly)
- 📋 Source-tier audit summary (counts by tier; flagged mismatches and how they were resolved)

### Loop 3+ — continue if Loop 2 surfaced material errors

Run another verification loop. Stop when:

1. **Convergence:** one full pass produces zero corrections (the natural and most common stopping condition; usually achieved by Loop 2 or 3), OR
2. **Hard ceiling:** 25 loops total have run (prevents pathological never-converging loops; this is an upper bound, not a target).

In practice convergence usually happens by Loop 2 or 3 for well-defined topics. The 25-loop ceiling exists for adversarial cases — contested topics, sparse literatures, ambiguous claims — where each iteration genuinely surfaces new findings. Quality-over-speed is the priority; the user has explicitly said they care more about quality than turnaround.

### Stopping criteria — "everything is good" (all 9 must hold)

A brief is **done** when ALL of the following are simultaneously true:

1. Every cited URL resolves to live content (no 404s).
2. Every cited claim matches what the source actually says, post-fetch (not just the search snippet).
3. Every load-bearing claim is at the appropriate source tier — academic claims peer-reviewed, technical claims from established institutions, practitioner claims explicitly labeled as practitioner consensus.
4. No internal contradictions across sections.
5. No load-bearing claim is labeled "synthesis" when a real citation exists in the literature.
6. All implicit user questions are addressed, or explicitly deferred with a stated reason.
7. Recommendations are concrete enough to execute without further clarification (for action-oriented briefs).
8. Every citation-checker / paper-search finding has been triaged: fixed, replaced, or labeled as remaining-risk.
9. No fabricated citation (URL, author, year, DOI, page number) remains.

If any of the nine fails, the brief is not done — keep looping until it is, or until the 25-loop ceiling stops you. If the ceiling stops you, list explicitly what is still uncertain.

### Surface loop progress to the user

Every loop's output begins with a one-line progress summary:

> **Loop 2:** 2 material errors corrected, 3 refinements added, 4 citation-checker findings triaged (2 fixed, 1 replaced, 1 left as remaining-risk note), 0 fabrications. Source-tier audit: clean. Convergence not yet — Loop 3 firing.

If you stop on convergence, say so explicitly. If you stop on the 25-loop ceiling, say so explicitly and list what is still uncertain.

### When the loop does NOT apply

- Quick factual lookups ("what's the population of Paris?") — direct answer.
- Code questions — different verification model (run the code, observe output).
- Navigation queries ("where is X file?") — direct tool use.

The loop kicks in for any full research-27 invocation and any "research X for me" / "give me a literature review on Y" request that triggers research-27. It is **never optional** for those.

### Tooling map for the loop

The loop requires several skills working in concert. There is no single "citation-deepening" skill in the toolset; the deepening workflow is the orchestration of these:

| Tool | Role in the loop |
|---|---|
| `citation-checker` | Sub-pass 2B — verifies academic citations against CrossRef / Semantic Scholar / OpenAlex; outputs findings |
| `paper-search` | Sub-pass 2D — finds candidate replacement / upgrade sources when 2B / 2C demand them |
| `paper-retrieval` | Sub-pass 2A — when a load-bearing paper deserves more than a snippet, fetches the full PDF for verification |
| `WebFetch` | Sub-pass 2A — confirms non-academic web sources actually back the claim |
| `WebSearch` | Sub-pass 2D — finds higher-tier sources when 2C surfaces tier mismatches |

Use them in concert; do not rely on any one alone.

## What this skill does NOT do

- It is not a quick-answer tool. If the user just wants a fact, answer the fact directly without invoking the full research format.
- It does not fabricate citations. If you cannot find a source for a claim, drop the claim or mark it as unsourced — never invent an author, year, or URL.
- It does not replace the user's judgment. Surface evidence and conflicting views; the user decides what to believe.
