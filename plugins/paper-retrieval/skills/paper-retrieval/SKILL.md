---
name: paper-retrieval
description: Use when the user asks to find or download the PDF of a specific named academic paper by title, author, or DOI. Triggers on "download paper X", "find/get the PDF of Y", "fetch this paper", "get the full text of Z", or upgrading an ABSTRACT-ONLY reference to FULL-PDF. Skip for general literature exploration (use paper-search MCP directly), for citation-metadata verification (use citation-checker), or for citation-rich research briefs (use research-27).
---

# Paper Retrieval

## Overview

Acquire and validate the actual paper while minimizing disruption to the user's work. Reuse legitimate institutional access; an anonymous HTTP failure is not evidence that the library lacks access.

**Verified 2026-11-01:** Berkeley access is active. UC Library Search → Download PDF → the existing CalNet-authenticated Chrome session retrieved Mallett (2004) and Scannell & Gifford (2017). UChicago access closed 2026-07-26; never use its old proxy or ILL. See `~/Claude/UChicago account backup/WHERE-THINGS-ARE.md` for archived material.

## Batch acquisition through Berkeley (verified 2026-11-14, ~100 papers in one session)

- **One URL per DOI:** `https://libkey.io/libraries/83/<DOI>` (library 83 = Berkeley) shows a "Download PDF" link that resolves through the proxy to the right host. These were observed: Elsevier → a signed `pdf.sciencedirectassets.com` PDF; APA journals → ProQuest (PsycNET itself hung at "Loading…" through the proxy); OUP → a silverchair PDF; AOM and Organization Science → an EBSCO viewer (its Download button opens a dialog with a second Download button). SAGE, T&F, Wiley and Springer PDFs can also be fetched in-page, same-origin, from a proxied article page (`/doi/pdf/<doi>?download=true`, `/doi/pdfdirect/<doi>`, `/content/pdf/<doi>.pdf`).
- **The trap:** Chrome lets a tab save only the first *script-triggered* download per host. Later `a.click()` saves on blob URLs fail **silently**: the script reports success, but nothing reaches ~/Downloads. This lost ~40 files before it was noticed. The fix is a real user gesture. Inject a fixed-position button whose onclick saves the prefetched blob, then click it with the computer tool. On ProQuest, pin its own "Download PDF" button to a fixed spot and real-click it. If a tab is already in the blocked state, open a fresh tab. Do not change Chrome's automatic-download permission. **Always `ls ~/Downloads` after each batch** rather than trusting the script's "saved".
- Move every file out of ~/Downloads immediately (rename by key), validate magic bytes, page count and title, and OCR image-only scans (`pdftoppm -r 300` + `tesseract`) so quotes can be verified.

## Minimize foreground interruptions

- Do not automatically open downloaded PDFs, activate Chrome, or switch the user's active tab to demonstrate success. Validate files locally; show a batch index or requested paper only when useful to the user.
- Prefer a verified public PDF download, existing local/Zotero attachment, or a documented browser download-to-file operation that reuses the authenticated session. Keep research in the user's requested window/group and reuse research tabs; do not navigate their unrelated working tabs.
- Publisher and library links may open foreground tabs (`target=_blank`), and native Save dialogs can take focus. When supported, read the observed link and navigate an existing background research tab instead of clicking a new-window link. Verify the current tool's behavior; do not assume a method stays in the background.
- In Codex's browser API, a locator's `downloadMedia` or `waitForEvent("download")` followed by its returned path may avoid the PDF viewer and Save dialog. Use only currently documented APIs. These are candidates, not a verified universal authenticated-download solution: a ScienceDirect `downloadMedia` attempt timed out on 2026-11-01. Inspect browser/files after a timeout before retrying; repeated attempts can open duplicate tabs or dialogs. Ensure the outer call timeout exceeds the bounded download timeout.
- If the authenticated PDF only saves through the viewer, use that fallback and complete Save yourself, then verify the file. On this Mac, Return did not complete one native Save dialog; clicking its explicit Save button did. Derive controls from fresh UI state. A necessary foreground step is acceptable; batch such steps and give a brief heads-up rather than repeatedly interrupting.
- Do not export cookies, change global download preferences, or weaken browser protections merely to avoid focus changes. Reuse the signed-in browser. A new CalNet/MFA prompt is a specific access step to hand off when required, not proof of missing coverage.
- Record the difference between public download, authenticated browser save, readable online full text, and unavailable full text. “Downloaded” and “read” are separate states. Never call a paper inaccessible solely because anonymous curl failed or a browser automation method timed out.

OA discovery APIs are conservative: continue to author sites and repositories after a “closed” verdict. Conversely, an OA license does not guarantee that an anonymous downloader can pass a publisher's bot protection.

## When to use

- User names a specific paper to acquire (title + author or DOI)
- A previous `paper-search` MCP attempt returned "closed" / "abstract-only"
- A reference list shows ABSTRACT-ONLY for a paper to upgrade to FULL-PDF

**When NOT to use:**
- General literature search → use `paper-search` MCP directly
- Verifying citation metadata → use `citation-checker`
- Composing a literature review → use `research-27`

## Operating modes

Use the least disruptive working route, whether the user is present or absent. Existing authenticated library access can be used autonomously; ask the user only for a concrete sign-in/MFA step the agent cannot complete. Public routes remain useful for background acquisition.

## Decision tree

A valid PDF has PDF magic bytes, opens in a PDF parser, and matches the requested title, authors, and article/version. File size alone is not decisive; short legitimate papers may be below 50 KB. A success HTTP status alone is insufficient.

### Tier 0 — Existing local copy / Berkeley library

Search relevant local reference folders or Zotero first. Identify the attachment by bibliographic identity rather than taking the newest PDF in storage.

For library acquisition, use https://www.lib.berkeley.edu/ → UC Library Search → title/author search → the matching record's **Download PDF** or publisher full-text link. Follow the actual observed link (often LibKey) rather than inventing proxy URL variants. Reuse the existing signed-in Chrome session; a separate command-line request does not inherit it. Verify institutional full-text access on the publisher page, save the actual article, and validate it locally. If Zotero Connector is available, it is an alternative acquisition route; verify the specific item's PDF attachment before copying it into the project.

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
If `is_oa: true`, follow `best_oa_location.url_for_pdf`. **DO NOT stop on `is_oa: false`** — keep going. Also: a `true` from Unpaywall doesn't guarantee anonymous fetch — Wiley OA URLs return Cloudflare 403 to `curl`. If anonymous retrieval fails, try the existing authenticated browser or continue through legitimate author/repository routes.

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

If public routes fail, try the authenticated Berkeley route before requesting help. Report the exact remaining obstacle (sign-in, coverage, bot challenge, failed download operation, or missing full text) and the exact title/DOI. Offer a direct PDF link when verified, plus the library record when needed. Berkeley ILL or an author request are fallbacks; do not send requests to others without user authorization.

**Never** use Sci-Hub, Library Genesis, or other unauthorized mirrors. Recommend legitimate routes only.

## Save conventions

**Bottom-Up Wellbeing project** (path `Bottom-up*/`):
- Folder: `references_deepening (claude)/pdfs/`
- Filename: `refNN_FirstauthorLastnameYYYY_VenueOrSource.pdf` (e.g., `ref04_KneerHaybron2024_Nous_HappinessWellBeing.pdf`)
- After download, run `pdftotext -layout "<dest>" "<dest>.txt"` for downstream grep
- Validate silently; do not open each downloaded PDF. Provide a readable index with local PDF links when reporting results.

**Other projects:** infer from existing reference-PDF folders; if none, ask the user.

## Validation and reading audit

Check PDF magic/parseability, then extract text (`pdftotext -layout`) and verify the title, authors, DOI where present, page count, and version. Inspect scanned pages visually if text extraction fails. Do not treat an author surname match alone as sufficient. Semantic Scholar and author-site links can return a different paper or an annual report.

Keep failed responses classified separately rather than deleting research records or leaving HTML wrappers labeled as valid PDFs. Record source URL, saved path, version, acquisition status, and reading status. Full-text XML/HTML or publisher view-only access can support reading but must not be counted as a downloaded PDF. Incomplete manuscripts, missing tables/supplements, and selected chapters must be labeled explicitly.

For a literature review, read the actual main text, methods, results, tables, limitations, and relevant references before marking a paper read. Record page/section support for claims and distinguish reused datasets from independent replications.

## Pilot results (2026-04-30, refs 1–10 + 38, 45 — UChicago era, before the account closed)

12 of 13 papers retrievable via Tier 0 (Zotero+UChicago) when user clicks once:

| Tier route | Count | Examples |
|---|---|---|
| Tier 0 — Zotero+UChicago | 12 | Wiley OA, Nature, IEEE, Springer Nat Hum Behav, Wiley J Pers (PMC), arXiv (also Tier 0 via institutional access) |
| Tier 6 — OSF preprint | 1 | Kennedy 2022 Guilford handbook chapter (book chapters not in journal catalogs) |
| Bot-detection failures w/o Tier 0 | 3 | Wiley OA papers — Cloudflare 403 blocks curl; Tier 0 bypasses cleanly |

**Headline lesson:** Tier 0 is the default for SYNC mode *when institutional access is live*. Public routes and existing authenticated library access can both be autonomous; Tier 4 (Google filetype:pdf) and Tier 6 (OSF preprint) cover the cases Zotero can't.
