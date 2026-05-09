---
name: citation-deepening
description: |
  Use when the user asks to "deepen" / "verify" / "build a further-details doc for"
  citations in a manuscript, or says any of: "for every citation make a more
  detailed citation", "build the citation backup", "fact-check citations",
  "verify what each cited paper actually says". Produces a Word-readable doc
  with verbatim source quotes, claim-vs-source verdicts, and surfaces
  citation-metadata errors as TODOs.

  Anti-triggers: bare "research" / "literature review" / "find papers about X" —
  those are forward-looking literature search, not backward-looking verification
  of an existing manuscript's citations.
---

# citation-deepening

Mechanics for building a "further-details" (deepening) document for citations in a manuscript the user has already drafted. The deepening doc lets the user see exactly what each cited paper says, in context, and catches three kinds of citation problems at the same time:

1. **Hallucinated content** — claims attributed to a paper that the paper doesn't actually make.
2. **Citation-metadata errors** — wrong title, year, volume, pages, or DOI in the bibliography.
3. **Claim-source mismatch** — the cited paper exists and is real but doesn't directly support the manuscript's claim at the cite point.

## When to Use

- the user says: "for every citation, build me a further-details doc with verbatim quotes" / "make a citation backup doc" / "verify citations" / "deepen citations" / similar.
- Late-stage manuscript work where the user wants to audit what each citation actually says before submission.
- Reviewer-response prep: a reviewer asks about a specific cite and the user wants the verbatim source pulled.

## When NOT to Use

- Forward-looking literature search ("find me papers about X") — that's `research-27`.
- Bibliography-formatting cleanup ("convert to PNAS NLM style") — that's a separate formatting pass, not a content-verification pass.
- Brand-new manuscript without any citations yet.
- the user says "just check the abstracts" — that's a lighter pass; you can still use this skill but skip Step 3 (verbatim quoting) and produce only the verdict table.

## Procedure

### Step 1 — Scope the run (don't try all citations at once)

Default scope: **8–12 citations per pass** unless the user says otherwise. The full bibliography may have 40+ refs; quality drops sharply if you try to deepen all of them in one pass.

If the user doesn't specify which citations:
- Start with the citations in whichever section he just pointed at (often introduced via screenshot).
- Otherwise, pick the first 8–10 in citation-order — those are usually the framing/literature-review cites where claim-source mismatch matters most.

If the scope is "the citations on this page/in this paragraph," let the user's pointer drive the selection.

### Step 2 — Inventory PDFs already in the project

```bash
find . -maxdepth 5 -type f -iname "*.pdf" 2>/dev/null | grep -iE "ref|cit|bib|src"
```

Most projects do *not* have a dedicated references folder. If none exists, create one at the **bundle root, not inside the git-tracked manuscript repo** (PDFs bloat git):

```
references_deepening (claude)/
├── pdfs/
└── notes/
```

(The `(claude)` suffix follows the user's project convention; drop it once he signs off.)

### Step 3 — Acquire missing PDFs (best-effort, honestly labeled)

For each cite in scope, try in this order:

| Source type | Strategy |
|---|---|
| **arXiv preprint** (any DOI starting with `10.48550/arXiv.` or arXiv ID present in cite) | `curl -sL https://arxiv.org/pdf/<arxiv_id>v<n>.pdf -o pdfs/refNN_*.pdf` — almost always works |
| **JOSS / open-access journal** | `curl https://joss.theoj.org/papers/<doi>.pdf` — works |
| **PMC-deposited (NIH-funded)** | `curl https://pmc.ncbi.nlm.nih.gov/articles/PMC<id>/pdf/` — sometimes works depending on PMC's gating |
| **Author preprint** | WebSearch the author's name + paper title; many psych authors host preprints on personal academic sites (`erinwestgate.com`, etc.) |
| **SSRN preprint** | Often returns HTML, not PDF; usually not worth the time |
| **Wiley / Elsevier / Springer / Nature** journal landing | Almost always paywalled. **Don't waste time.** Mark as ABSTRACT-ONLY and use the abstract page metadata. |

After each `curl`, verify with `file pdfs/refNN_*.pdf`. If it returns "HTML document text" instead of "PDF document," the download failed — delete and label the cite as ABSTRACT-ONLY.

**Do not download paywalled PDFs through unofficial channels** (Sci-Hub, etc.). Honestly labeling cites as ABSTRACT-ONLY is better than the appearance of full verification.

### Step 4 — Extract text from acquired PDFs

```bash
for f in pdfs/ref*.pdf; do
  pdftotext -layout "$f" "${f%.pdf}.txt"
done
```

`-layout` preserves columns, which matters for two-column conference papers (BERT, SBERT) but doesn't hurt for single-column papers.

### Step 5 — Pull manuscript-claim contexts

For each cite in scope, grep the manuscript for the bracket-citation pattern:

```bash
for n in 1 2 3 4 5 6 7 8 9 10; do
  echo "===== [$n] ====="
  grep -nE "\[($n|[0-9]+, ?$n|$n,)" path/to/manuscript.md | head -5
done
```

Record the **manuscript line number, the verbatim sentence, and the section** where each cite appears. A single cite may appear multiple times (intro framing + methods detail + discussion); record all of them — claim-source mismatches often show up only at one of the appearance sites.

### Step 6 — Draft the deepening doc

Use this structure (one section per cite):

```markdown
# Ref [N] — <author> <year>, <venue>

## Manuscript claim (line LLL, section)
> <verbatim sentence(s) citing this ref>

## Reference as cited
> N. <verbatim from References list>

## What the source says
**Source confidence:** FULL-PDF | ABSTRACT-ONLY | THIRD-PARTY-METADATA | NONE

**Verbatim from <abstract / §1 / §2.3>:**
> <verbatim source quote, ideally with page #>

(repeat for each relevant excerpt — typically 2-4 quotes per cite)

## Verdict
✅ SUPPORTS | 🟡 PARTIAL | ⚠️ CITATION-METADATA-ERROR | ❌ CONTRADICTS

<one paragraph: does the source back the claim? Where it doesn't, exactly which clause fails?>

## Recommended action
<None / softening suggestion / TODO N to surface for the user's decision>
```

The doc opens with a **Summary table** (one row per cite, columns: Verdict, Confidence, PDF-in-folder?) for fast scan.

### Step 7 — Spawn validation agent

This is non-negotiable, even if the deepening doc was drafted carefully:

```
Agent: general-purpose
Subject: "Validate citation deepening doc against PDFs"

For each verbatim quote in the deepening doc attributed to a FULL-PDF source:
1. Find the same passage in the corresponding .txt file (use grep).
2. Confirm verbatim match. Whitespace and line-wrap differences are OK; word-level differences are NOT OK.
3. If a quote is misattributed or hallucinated, flag with line number + diff.

For ABSTRACT-ONLY refs: confirm the doc clearly labels them as such.

Output: notes/validation_run_YYYY-MM-DD.md

PASS / FAIL / PASS-WITH-NOTES headline.
```

The agent runs in a clean context window so it can't unconsciously rationalize a mismatch as a near-match. **No-hallucination is the user's standard. Don't skip this.**

If the validator returns FAIL, fix the offending quotes before delivering the doc.

### Step 8 — Surface citation-metadata errors as TODOs

For any cite the deepening doc verdict-tagged as `CITATION-METADATA-ERROR` or where the source clearly doesn't support the manuscript claim:

- Add a TODO to `revisions/<USER>_todos.md` (via revision-queue conventions).
- Heading should mention severity: **HIGH** for wrong DOI / wrong paper entirely; **medium** for title-only mismatch or wording softening; **low** for missing bibliographic fields.
- Body: include the artifact (verbatim citation), the finding (what's actually at the DOI / what the source actually says), 2-3 options for the user, and your recommendation.
- Do **not** auto-edit the manuscript or References list to "fix" the cite. Substantive bibliographic changes require the user's sign-off.

The bare bibliographic-formatting fix (missing page range, etc.) can be marked **READY TO APPLY** since it's mechanical.

### Step 9 — Render to .docx and open

Per the user's docx-only rule:

```bash
pandoc "references_deepening (claude)/citation_deepening_refs<range> (claude).md" \
       -o "references_deepening (claude)/citation_deepening_refs<range> (claude).docx"
open "references_deepening (claude)/citation_deepening_refs<range> (claude).docx"
```

No PDF render. Don't ask whether to render PDF.

## How to think about the work

The deepening doc is *not* a literature review or a research note. It is a **claim-by-claim audit**. The skill of writing a good one is staying close to the source, quoting verbatim, and resisting the urge to summarize-then-paraphrase. Verbatim quotes plus page numbers force the reader (the user) to confront exactly what the cited paper said vs. what the manuscript says.

For each cite, the audit question is narrowly: **"Does the source say what the manuscript says it says?"** Three outcomes:

- **Yes, exactly.** Mark ✅ SUPPORTS, no action.
- **Yes, but the manuscript wording is slightly stronger or differently scoped than the source.** Mark 🟡 PARTIAL, recommend a softening.
- **No.** Mark ⚠️ or ❌, flag as a substantive change needing the user's call. **Do not auto-fix substantive changes** — the user's standing rule is "Claude is a faithful formatter, not a co-author."

If the source PDF is unobtainable, *say so* — don't paper over it with confident-sounding paraphrases of the abstract. The skill is honest scoping, not exhaustive coverage.

## Failure Modes (avoid these)

| Mode | What goes wrong | Fix |
|---|---|---|
| Trying to deepen 40+ citations in one pass | Quality collapses by cite #15; wrong attributions creep in | Cap at 8–12 per pass; let the user queue more |
| Skipping the validation agent | Hallucinated quotes slip through; the user's "no hallucination" standard violated | Always run a separate-context validator (see Step 7) |
| Auto-editing citation metadata when you find an error | Substantive changes happen without the user's sign-off; "faithful formatter" rule violated | Surface as TODO; let the user decide |
| Treating the *abstract* of a paper as if it's been fully read | Specific in-paper claims (figures, tables, robustness checks) get attributed wrongly | Label confidence FULL-PDF vs ABSTRACT-ONLY explicitly per cite; never quote from a paper you only have the abstract of |
| Downloading paywalled PDFs through unofficial channels | License/ethics issue; also wastes time when the paywall path doesn't work | If paywalled, mark ABSTRACT-ONLY and move on |
| Not pulling **all** appearance sites of a cite | Mismatch shows up only on one occurrence (e.g., methods context fine, intro framing wrong); you mark ✅ when you should have marked 🟡 | grep for `\[N\]` everywhere it appears, not just the first hit |
| Rendering PDF in addition to docx | Wastes time; the user explicitly turned off PDF rendering | docx only |

## Origin

Built 2026-04-30 from a real deepening run on the bottom-up wellbeing manuscript v5, refs [1]–[10]. The validation-agent step caught zero hallucinations but flagged three minor page-attribution slips, and the run itself caught a HIGH-severity citation-metadata error in [2] (DOI resolves to a different paper than the bibliography entry shows). See `references_deepening (claude)/` for the worked example.
