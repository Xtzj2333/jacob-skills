---
name: paper-retrieval
description: Use when the user asks to find or download the PDF of a specific named academic paper by title, author, or DOI. Triggers on "download paper X", "find/get the PDF of Y", "fetch this paper", "get the full text of Z", or upgrading an ABSTRACT-ONLY reference to FULL-PDF. Skip for general literature exploration (use paper-search MCP directly), for citation-metadata verification (use citation-checker), or for citation-rich research briefs (use research-27).
---

# Paper Retrieval

## Overview

Layered fallback for acquiring a specific known paper as a PDF. Two operating modes — **synchronous** (user is at their computer and can click once) vs. **asynchronous** (Claude is fetching while user is away). The right tier depends on which mode you're in.

Core insights:
- **Zotero + institutional library is the dominant solution.** The community has converged on Zotero's translator + EZproxy auto-detection ecosystem. For UChicago, `Wiley Online Library + UChicago Library` co-branded pages route through institutional access in one click and bypass Cloudflare bot-detection that defeats anonymous `curl`.
- **OA-API "closed" verdicts are conservative.** Author-archived PDFs on Squarespace/personal sites, Springer SharedIt links, PsyArXiv preprints, and direct `filetype:pdf` Google hits routinely surface papers Unpaywall reports as having no OA copy.
- **"Open Access" doesn't mean "anonymously fetchable."** Wiley OA papers (e.g. CC-BY-NC) are gated behind Cloudflare even when the license is open. A real browser session — institutional or not — passes the challenge; `curl` does not.

## When to use

- User names a specific paper to acquire (title + author or DOI)
- A previous `paper-search` MCP attempt returned "closed" / "abstract-only"
- A reference list shows ABSTRACT-ONLY for a paper to upgrade to FULL-PDF

**When NOT to use:**
- General literature search → use `paper-search` MCP directly
- Verifying citation metadata → use `citation-checker`
- Composing a literature review → use `research-27`

## Operating modes

**SYNC (user present):** Use Tier 0 (Zotero + institutional library) first. One click; ~90% success rate; bypasses bot-detection. Fallback to Tier 1+ only when the paper isn't in the institution's licensed catalog.

**ASYNC (user absent):** Skip Tier 0 — it requires user click. Start at Tier 1 (paper-search MCP), proceed through Tiers 2-6. If all fail, surface a user-action recommendation pointing the user at the Tier 0 URL for when they next sit down.

## Decision tree

A "valid PDF" means: HTTP 200, `file <path>` reports `PDF document`, magic bytes start with `%PDF-`, size ≥50 KB, title/author grep matches.

### Tier 0 — Zotero + institutional library (SYNC mode only)

For UChicago, the canonical SFX endpoint is:
```
https://sfx.lib.uchicago.edu/sfx_local?atitle=<URL-encoded title>&anlast=<lastname>&date=<year>
```
Or simply: `https://www.lib.uchicago.edu` + library search by DOI / title.

User click flow:
1. UChicago Find It! page → click the publisher link (Wiley / Springer / Elsevier / etc.).
2. Lands on co-branded publisher page (e.g. "Wiley Online Library + UChicago Library").
3. Click the Zotero Connector "Z" icon → choose the publisher-specific translator (e.g. "Save to Zotero (Wiley Online Library)").
4. Zotero saves citation + Snapshot + Full Text PDF to the chosen collection.

Verification (Claude side, autonomous): Zotero exposes a local API at `http://localhost:23119/api/` (must be enabled in Settings → Advanced → "Allow other applications to communicate with Zotero"). The `zotero-mcp` server (`github.com/54yyyu/zotero-mcp`) wraps this. Use it to confirm an item appears in the user's library after a save.

After Zotero save, copy the PDF into the project's reference folder:
```bash
# Find newest PDF in Zotero storage
NEW_PDF=$(find "$HOME/Zotero/storage" -mtime -1 -name "*.pdf" -type f | head -1)
cp "$NEW_PDF" "<project>/references_deepening (claude)/pdfs/refNN_<canonical_name>.pdf"
```

### Tier 1 — paper-search MCP (ASYNC default starting point)

Covers arXiv, biorXiv, PsyArXiv, JOSS, SSRN, EuropePMC, PMC.
```bash
uv run --directory /Users/jacobzhang/paper-search-mcp paper-search search "<title>" -n 3 -s arxiv,semantic,crossref,openalex,europepmc,biorxiv,pmc
uv run --directory /Users/jacobzhang/paper-search-mcp paper-search download <source> <id> -o "<dest_dir>"
```

### Tier 2 — Unpaywall / OpenAlex API

```bash
curl https://api.unpaywall.org/v2/<DOI>?email=jacobqqqzxt@gmail.com
```
If `is_oa: true`, follow `best_oa_location.url_for_pdf`. **DO NOT stop on `is_oa: false`** — keep going. Also: a `true` from Unpaywall doesn't guarantee anonymous fetch — Wiley OA URLs return Cloudflare 403 to `curl`. If the URL is `*.onlinelibrary.wiley.com/doi/pdfdirect/...` and you're in ASYNC mode, surface to user (or skip to Tier 3+).

### Tier 3 — PMC / EuropePMC direct

If the metadata has a `PMC<id>`, try in order:
```
https://europepmc.org/articles/<PMCID>?pdf=render        # 302s to /api/getPdf — usually works
https://www.ncbi.nlm.nih.gov/pmc/articles/<PMCID>/pdf/   # often returns HTML wrapper; check magic bytes
```

### Tier 4 — Google `filetype:pdf` web search

Highest-value gray-route step.
- `"<Full Title>" filetype:pdf`
- `"<First-author Lastname>" "<Year>" filetype:pdf`

Look for hits on `static1.squarespace.com`, `*.[univ].edu`, `sites.google.com`, `*.wixsite.com`, `escholarship.org`, `figshare.com`, `osf.io`, `psyarxiv.com`, university course handout pages.

### Tier 5 — Author lab/personal website

Google `"<Lastname> lab homepage"` or `"<Lastname> <University> publications"`. Look for `/publications`, `/cv`, `/papers`. Many academics post Springer/Nature SharedIt view-only links on these pages — those are publisher-sanctioned full-text access and count as a valid acquisition.

### Tier 6 — Book-chapter / preprint server lookup

For book chapters not in journal catalogs, look for the corresponding **PsyArXiv / OSF preprint**. Many handbook chapters are deposited there. Check author's site for the OSF DOI, then:
```
https://osf.io/<id>/download
```
Note the file may be the preprint version with minor textual differences from the published chapter.

### Tier 7 — Surface to user (do NOT bypass auth)

If Tiers 1-6 miss, do not attempt to bypass authentication. Recommend:
- UChicago library proxy: `https://proxy.uchicago.edu/login?url=<publisher-url>`
- LibKey Nomad browser extension at the publisher page
- ILL request via UChicago library
- Polite email to the corresponding author

**Never** use Sci-Hub, Library Genesis, or other unauthorized mirrors. Recommend legitimate routes only.

## Save conventions

**Bottom-Up Wellbeing project** (path `Bottom-up*/`):
- Folder: `references_deepening (claude)/pdfs/`
- Filename: `refNN_FirstauthorLastnameYYYY_VenueOrSource.pdf` (e.g., `ref04_KneerHaybron2024_Nous_HappinessWellBeing.pdf`)
- After download, run `pdftotext -layout "<dest>" "<dest>.txt"` for downstream grep
- After download, `open "<dest>"` so the user can verify visually

**Other projects:** infer from existing reference-PDF folders; if none, ask the user.

## Validation snippet

Three checks, in order. Any failure → delete the file and proceed to the next tier.

```bash
DEST="<path>"
EXPECTED_TITLE="<distinctive phrase from the actual paper title>"
EXPECTED_AUTHOR="<first-author lastname>"

file "$DEST" | grep -q "PDF document" || { echo "NOT A PDF — discard"; rm "$DEST"; exit 1; }

SIZE=$(stat -f%z "$DEST")
[ "$SIZE" -gt 50000 ] || { echo "Suspiciously small (<50KB)"; rm "$DEST"; exit 1; }

pdftotext -layout "$DEST" "${DEST%.pdf}.txt" 2>/dev/null
grep -q -i "$EXPECTED_TITLE\|$EXPECTED_AUTHOR" "${DEST%.pdf}.txt" || {
  echo "CONTENT MISMATCH — file is a different paper than requested"; exit 1; }
```

The third check is critical. **Semantic Scholar's `pdfs.semanticscholar.org` URLs occasionally serve a different paper than the one whose abstract page links to them** — observed 2026-04-30 when a Kennedy 2022 chapter request returned a Rathje 2024 PNAS paper. Always grep before declaring success.

## Common mistakes

| Mistake | Fix |
|---|---|
| In SYNC mode, going to Tier 1 first instead of Tier 0 | If user is present, Zotero+UChicago is one click. Don't waste 5 tiers of API calls. |
| Trusting Unpaywall's `is_oa: false` and stopping | "Closed" ≠ "unfindable." Run Tier 4 next. |
| Trusting Unpaywall's `is_oa: true` and assuming `curl` will work | Wiley OA → Cloudflare 403 to anonymous curl. Need real browser or institutional route. |
| Saving an HTML paywall wrapper as `.pdf` | `file <path>` and size-check after every download. |
| Saving to wrong folder | Bottom-Up canonical path is `references_deepening (claude)/pdfs/`, not `manuscript_repo_tony/`. |
| Using Sci-Hub / LibGen | Don't. Recommend Tier 7 routes. |
| Auto-renaming files marked `(source)` | The `(source)` rule applies — request "extract here" permission first. |

## Red flags

- "I'll just trust the API verdict" — go to Tier 4.
- "The publisher page returned 200, must be the PDF" — check `file` output and magic bytes.
- "Wiley says it's OA, I'll just curl it" — Cloudflare blocks anonymous curl. Use Tier 0 or surface to user.
- "I'll grab it from Sci-Hub real quick" — no. Recommend a legitimate route.

## Pilot results (2026-04-30, refs 1–10 + 38, 45)

12 of 13 papers retrievable via Tier 0 (Zotero+UChicago) when user clicks once:

| Tier route | Count | Examples |
|---|---|---|
| Tier 0 — Zotero+UChicago | 12 | Wiley OA, Nature, IEEE, Springer Nat Hum Behav, Wiley J Pers (PMC), arXiv (also Tier 0 via institutional access) |
| Tier 6 — OSF preprint | 1 | Kennedy 2022 Guilford handbook chapter (book chapters not in journal catalogs) |
| Bot-detection failures w/o Tier 0 | 3 | Wiley OA papers — Cloudflare 403 blocks curl; Tier 0 bypasses cleanly |

**Headline lesson:** Tier 0 is now the default for SYNC mode. Tiers 1-6 remain the autonomous (ASYNC) path; Tier 4 (Google filetype:pdf) and Tier 6 (OSF preprint) cover the cases Zotero can't.
