---
name: decision-forms-html
description: Use when an HTML page for Jacob needs answers back from him — decisions to pick between, options to choose, comments to leave in place, or sections for him to dismiss. Applies to chat-substitutes, literature reviews with inline "which paper?" picks, mockups with variant choices, and any page where Claude has drafted options. Skip when the page is purely informational with no asks back — then forms are noise, not navigation.
---

# decision-forms-html

The standardized mechanics for collecting Jacob's answers in an HTML page: lift `references/form-pattern.js` verbatim into a `<script>` at the end of `<body>` and use the markup contracts below. Answers, comments, and archive marks persist in localStorage across sittings until Jacob hits **Copy all** — one paste captures everything. Only these contracts are fixed (so recording works reliably); the page design around them is free.

## Decision fieldset

```html
<fieldset class="decision-form" data-decision-id="some-decision">
  <legend>Plain-English question?</legend>
  <p class="question-prompt">Brief context + Claude's recommendation.</p>
  <div class="options">
    <label><input type="radio" name="some-decision" value="a"> A — option label</label>
    <label><input type="radio" name="some-decision" value="b"> B — option label</label>
  </div>
  <button type="button" class="clear-q" data-clears="some-decision">Clear this question</button>
  <textarea placeholder="Comments…" data-comment="some-decision"></textarea>
</fieldset>
```

And the toolbar, once per page (radios are click-to-uncheck; the per-question Clear is the discoverable fallback):

```html
<div class="form-toolbar">
  <button type="button" data-form-action="copy-all">Copy all responses</button>
  <button type="button" data-form-action="download-json">Download JSON</button>
  <button type="button" data-form-action="clear-all">Clear all</button>
</div>
```

## Archive chip + paired comment box (chat-substitute pages)

The chip never appears alone — these three elements are one unit, emitted together per section:

```html
<button type="button" class="archive-chip" data-archive-target="section-id">Archive this?</button>
<button type="button" class="chip-comment-toggle" data-comment-toggle="section-id">💬 Comment</button>
<textarea class="chip-comment" data-chip-comment="section-id" placeholder="Comment on this card…" hidden></textarea>
```

**Chip:** click toggles "✓ marked to archive"; marks persist in the same storage entry, ride Copy-all as a final `## Archive marks` block (and the JSON download), and the next render moves marked sections to the archive and clears the marks.

**Comment pair:** the toggle sits beside the chip and expands/collapses the textarea (collapsed by default so cards stay compact; expanding focuses it). Typed text persists in the same storage entry, rides Copy-all as a `## Card comments` block keyed by section id (JSON: `card_comments`), and follows correctness rule 3's PROCESSED auto-clear lifecycle like any other free-text box. A saved comment must never be invisible: on load the box reopens expanded and the toggle shows "✓ comment saved" (the reference JS does this). The section id becomes the heading Jacob pastes back, so keep it recognizable out of context.

Style both buttons obviously clickable — they must not read as static tags. Pair every chip with a detail fold: a `<details>` beside it (obviously-clickable summary, e.g. "More detail") holding enough context — where the item came from, when, what archiving it means — for Jacob to judge it cold; a chip he can't place is a chip he can't click. When to use the chip lives in `chat-substitute-html`.

## Correctness rules

1. **STORAGE_KEY namespaces by page.** Edit the top of the JS to `html_form_responses_<page-slug>` — otherwise answers bleed between reports.
2. **Ids and legends are what Jacob pastes back.** `data-decision-id` and `<legend>` become the headings of the copied Markdown, so make them recognizable out of context (semantic id, plain-English question).
3. **Applied comments must auto-clear.** Jacob's typed comments live in browser localStorage, not the HTML — applying a round doesn't clear the boxes, and his next Copy-all re-sends them. Any page with free-text comment boxes embeds a `PROCESSED` registry (`{comment-key: {text, round}}`, appended verbatim each round); on open, a box whose saved text matches its registry entry (whitespace/smart-quote/case-normalized) auto-clears into `STORAGE_KEY + '_cleared'` with an undo note. An edited box never auto-clears — that's the safety valve for added follow-up thoughts. Reference implementations: FE3's `prereg/process_build_comment_copy.py` and the inline version in `prereg/FE3_variable_hypothesis_map.html`.
4. **Don't swap to Alpine.js** — `$persist` has a load-order trap where `x-model` silently fails to bind. The reference JS is intentionally framework-free.
