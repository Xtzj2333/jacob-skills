---
name: source-quality-check
description: |
  Use when the user asks to "check the quality of citations" / "rate the
  references" / "are these papers any good" / "are we citing master's theses
  or top journals" / "is this the right kind of source for this claim" /
  similar. Produces a Word-readable doc rating each cited reference on
  venue tier, peer-review status, recency-sensitivity, and author credibility.

  Anti-triggers: bare "research" / "find papers" — those are forward-looking
  literature search. "Verify what this paper says" — that's `citation-deepening`,
  not this skill.
---

# source-quality-check

Mechanics for rating the *quality* of cited sources in a manuscript — separate from whether they actually support the claim (which is `citation-deepening`'s job).

The four axes:

1. **Venue tier** — top journal vs. mid-tier vs. unranked vs. preprint vs. tech report vs. conference vs. book chapter.
2. **Peer-review status** — was this work peer-reviewed, conference-reviewed, editor-screened, or self-published?
3. **Recency-sensitivity** — does the field's pace of change make this paper's vintage relevant? (AI/ML: 2-3 years stale fast. Anthropology: decades fine. Foundational mathematics: timeless.)
4. **Author credibility** — established researcher with prior productivity in the area, or a one-off paper from a less-tracked group?

## When to Use

- the user says: "rate the citations" / "are these top-tier sources" / "I want a quality check on the bib" / "are any of these preprints we should worry about" / similar.
- Pre-submission: the user wants to spot-check that he's not relying on sources reviewers will discount.
- After any citation-deepening pass that includes new cites — quality check is the natural follow-up.

## When NOT to Use

- For papers the user themselves authored or co-authored — quality-rating own work is awkward and unnecessary.
- For the methodological-correctness question ("does this paper support the claim") — that's `citation-deepening`.
- For citation-formatting questions (PNAS NLM-style etc.) — that's a separate format pass.

## Procedure

### Step 1 — Scope (default 8–12 cites per pass)

Same scoping logic as `citation-deepening`. Quality-check ideally pairs with deepening on the same set of cites, in the same pass, so the two .docx files can be reviewed side-by-side.

### Step 2 — Build the assessment columns

For each cite, fill four columns:

#### a) Venue tier

Use this discrete scale:

| Tier | Meaning |
|---|---|
| **A\*** | Top of field. *Nature*, *Science*, *PNAS*, *Cell*, *Nature Human Behaviour*; top-of-field discipline journals (*Psychological Science*, *Psychological Review*, *American Economic Review*); top conferences (NeurIPS, ICML, ICLR, ACL/EMNLP/NAACL with best-paper or strong acceptance) |
| **A** | High-quality field journal. Top-3 in subfield. (*J Personality*, *Cognition*, *Noûs* in philosophy, *J Mach Learn Res*, *IEEE TPAMI*) |
| **B** | Mid-tier peer-reviewed. Solid but not flagship. |
| **C** | Lower-tier peer-reviewed. May be regional, narrowly-scoped, or with rapid-acceptance reputation. |
| **Conf-A\*** | Top conference (NeurIPS/ICML/ACL/EMNLP/NAACL/CVPR/etc.) |
| **Conf-A** | Strong second-tier conference |
| **Conf-B** | Workshop or smaller venue |
| **Preprint** | arXiv / SSRN / PsyArXiv / OSF only — not peer-reviewed |
| **Tech-report** | Industry-lab technical report (often arXiv-deposited but explicitly marked tech-report). Treat similarly to Preprint for PR status, but author institutional credibility may be high. |
| **Software-paper** | JOSS, SoftwareX — peer-reviewed but software-focused; light on theoretical content |
| **Book/Chapter** | Book or handbook chapter. Editor-screened, not blind PR. |
| **Thesis** | Master's or PhD thesis. May be high-quality but not peer-reviewed in the journal sense. |

#### b) Peer-review status

`Peer-reviewed` / `Conference-reviewed` / `Editorial-screened` / `Preprint-only` / `Tech-report` / `Self-published`.

#### c) Recency-sensitivity

Determine the *field*'s recency-sensitivity first:

- `HIGH` — AI/ML/NLP architectures, software libraries, very-recent industry trends. 2-3 years can stale a paper.
- `MEDIUM` — most empirical psychology, sociology, applied econ. ~10 years can stale.
- `LOW` — foundational mathematics, classical philosophy, historical anthropology, well-established theory. Decades fine.

Then judge: is the cited paper appropriately recent for that sensitivity?

- `✅` — appropriate vintage
- `🟡` — borderline (e.g., 2018 paper for a HIGH-sensitivity claim)
- `🟠` — outdated (e.g., 2015 paper for a HIGH-sensitivity claim about LLMs)

#### d) Author credibility

Look up the lead author(s):
- Affiliation (institution and lab/group)
- Are they an established researcher in the cited area? Multiple prior peer-reviewed pubs in this subfield?
- Approximate h-index or signature papers if recognizable
- For industry-lab papers: is the lab itself credible (Google Brain, MSR, Anthropic, FAIR, OpenAI, Tongyi, DeepMind)?

Don't quote precise h-index numbers unless certain. Use qualitative signals: "established", "early-career but in solid lab", "unknown to me."

#### e) Composite signal

Combine into one of:

| Symbol | Meaning |
|---|---|
| ✅ | Strong cite — top-tier venue, peer-reviewed, appropriate vintage, credible authors. No action needed. |
| 🟢 | Acceptable cite — minor caveat (e.g., software paper for an algorithm citation). No action needed. |
| 🟡 | Acceptable-with-caveat — flag in the doc but leave to the user whether to act. |
| 🟠 | Marginal — meaningful concern (e.g., bibliographic error, wrong-paper cite, very-stale paper for fast-moving field). Flag prominently. |
| 🔴 | Weak — fail at least one axis materially (e.g., self-published, master's thesis used as authority, preprint cited as if peer-reviewed when stronger source exists). |

### Step 3 — Doc structure

Use this layout:

```markdown
# Source Quality Check — <project> (Refs [N]-[M])

## Summary table
| Ref | Authors | Venue | Year | Tier | PR | Recency | Composite |
|---|---|---|---|---|---|---|---|
| [1] | … | … | … | A | Peer | ✅ | ✅ |

## Per-reference notes

### [N] <author> (<year>)
- **Venue tier — <X>.** <one-paragraph justification>
- **Peer-review status:** <…>
- **Recency.** <field sensitivity + judgment>
- **Author credibility.** <one-paragraph notes>
- **Composite: <symbol>.** <one-sentence summary; mention any action item>

## Bottom line
- Strong cites needing no action: <list>
- Cites with minor caveats: <list>
- Cites needing fix or replacement: <list with action items>
```

### Step 4 — Don't fabricate impact factors or h-indices

Stating "*Noûs* IF ~3" is fine if you're confident; stating "*Noûs* 2024 IF 3.847" is over-claiming unless you actually have the figure. Use approximate / qualitative phrasings ("among the top philosophy journals", "Wiley/Blackwell, Leiter top-5 in analytic philosophy") rather than fabricated precision.

When uncertain, write "*X is widely regarded as a top-tier journal in <subfield>*" rather than inventing numbers.

### Step 5 — Cross-link to citation-deepening when relevant

If `citation-deepening` already ran on the same cite range and surfaced specific issues (metadata errors, claim mismatches), reference them in the quality-check doc rather than re-stating. Example: in the per-reference notes for [2], say "Composite: 🟠 marginal — bibliographic metadata error documented in `citation_deepening_refs01-10 (claude).docx` § Ref [2]; otherwise A-tier venue."

### Step 6 — Render to .docx and open

```bash
pandoc "references_deepening (claude)/source_quality_check_refs<range> (claude).md" \
       -o "references_deepening (claude)/source_quality_check_refs<range> (claude).docx"
open "references_deepening (claude)/source_quality_check_refs<range> (claude).docx"
```

No PDF.

## How to think about the work

Quality-check is **separate from claim-verification**. A cite can be a perfect-tier source (A* journal, gold-standard authors, peer-reviewed) and still not actually support the manuscript's claim. Vice-versa: a tech-report from Tongyi (Qwen) is a *perfect* cite for "we used Qwen3-Embedding-4B" even though it's not peer-reviewed, because it's the canonical industry standard for citing the model.

The goal is to flag cases where:
- A reviewer is likely to push back on the source (preprint cited as authority where a peer-reviewed alternative exists; thesis cited where a journal article would be stronger; very-stale paper for a fast-moving field).
- The bibliography has a reproducibility gap (missing page range, missing publisher, ambiguous author lineup).
- The author lineup is unknown / hard to verify (consider whether this is a substance issue or just a recognition gap on Claude's end).

It is *not* the goal to flag every preprint or every tech-report. Industry-lab tech reports and arXiv preprints are first-class citations in the NLP/ML world. The standard is "is this an appropriate kind of source for this claim, given the field's conventions" — not "is this peer-reviewed yes or no."

## Failure Modes (avoid these)

| Mode | What goes wrong | Fix |
|---|---|---|
| Inventing impact factors / h-indices | False precision; reviewer or the user spot-checks and finds the number wrong | Use qualitative language. State numbers only when verified. |
| Treating "preprint" as automatic 🔴 | Misjudges canonical NLP/ML citation practice (BERT, Sentence-BERT, Qwen, GPT-4 all cited from arXiv/tech-reports as standard) | Field-conditioned: in NLP, preprint of a foundational system is fine. In clinical psych, less so. |
| Quality-check without context for what claim is being supported | "A-tier venue" doesn't actually answer "is this the right cite for *this* claim" — that's deepening's job | Reference the deepening doc; don't try to do both jobs in one doc |
| Rating papers by lab brand alone | "It's from MSR/FAIR/etc." can short-circuit independent assessment | Lab-credibility is one signal among four; don't let it dominate |
| Quality-checking 30+ cites in one pass | Quality assessments become formulaic by cite #20 | Cap at 8–12 per pass, same as deepening |

## Origin

Built 2026-04-30 from a real quality-check run on the bottom-up wellbeing manuscript v5, refs [1]–[10]. Outcome of that run: 5 strong cites (✅), 4 acceptable-with-caveat (🟡 / 🟢), and 1 marginal (🟠 — the [2] bibliographic-error case caught by `citation-deepening`). See `references_deepening (claude)/source_quality_check_refs01-10 (claude).docx` for the worked example.
