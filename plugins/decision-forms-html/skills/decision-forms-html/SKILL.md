---
name: decision-forms-html
description: Use when building any HTML page that needs to collect answers from Jacob — radio choices with optional comments, per-question clear, sticky toolbar with Copy-all-as-Markdown / Download-JSON / Clear-all, localStorage persistence across sittings. Composable: drops into chat-substitute HTMLs (via chat-substitute-html), into literature reviews with inline "which paper?" picks, into mockups with variant choices, into any HTML where Claude has drafted options for Jacob to pick from. Skip when the page is purely informational with no asks back — then forms are noise, not navigation.
---

# decision-forms-html

> Interactive decision-form pattern for HTML pages. Self-contained: lift `references/form-pattern.js` verbatim into a `<script>` at the end of `<body>`, mark fieldsets with the conventional class, and Jacob's answers persist across sittings until he hits Copy.

## What you get

- Click-to-uncheck radios (deselect by clicking the same option twice).
- `localStorage` persistence so reopen-after-days restores draft answers.
- Sticky toolbar at the bottom: **Copy all responses** (Markdown), **Download JSON**, **Clear all**.
- Per-question Clear button as a discoverable fallback.
- Absorbed-content cleanup hook for when a re-render relocates user-supplied text out of a fieldset.

The one-paste-captures-all design is load-bearing: Jacob fills out across however many sittings he wants, then submits everything in one paste-back to chat.

## Markup pattern

```html
<fieldset class="decision-form" data-decision-id="some-decision">
  <legend>Plain-English question Jacob would naturally ask?</legend>
  <p class="question-prompt">Brief context + Claude's recommendation.</p>
  <div class="options">
    <label><input type="radio" name="some-decision" value="a"> A — option label</label>
    <label><input type="radio" name="some-decision" value="b"> B — option label</label>
  </div>
  <button type="button" class="clear-q" data-clears="some-decision">Clear this question</button>
  <textarea placeholder="Comments…" data-comment="some-decision"></textarea>
</fieldset>
```

And the toolbar, once per page:

```html
<div class="form-toolbar">
  <button type="button" data-form-action="copy-all">Copy all responses</button>
  <button type="button" data-form-action="download-json">Download JSON</button>
  <button type="button" data-form-action="clear-all">Clear all</button>
</div>
```

Then drop `references/form-pattern.js` at the end of `<body>` in a `<script>` tag (inline is fine; the file is ~190 lines).

## Conventions

- **Decision-id is semantic.** `migration-strategy`, `naming-convention` — names Jacob will scan in the copied Markdown.
- **Legend is a plain-English question Jacob would write himself coming back cold.** "Act on the fired trigger" fails this; "Should I update the sync tool so it can also make HTML?" passes.
- **STORAGE_KEY namespaces by report.** Edit the top of the JS to `html_form_responses_<page-slug>` so multiple form-bearing HTMLs don't collide in localStorage. Symptom of skipping this: answers appear in unrelated pages.

## What this skill does NOT carry

- No opinions about page structure, "what's new" pins, status banners, or locked-decision demotion — those are `chat-substitute-html`'s job. This skill is just the form mechanics.
- Don't swap to Alpine.js — `$persist` has a load-order trap where `x-model` silently fails if `alpine-persist.js` hasn't loaded yet. The reference JS is intentionally framework-free.
