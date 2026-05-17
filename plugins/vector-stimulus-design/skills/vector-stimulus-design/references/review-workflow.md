# Review workflow — vector stimulus design

How to surface stimulus choices to the researcher and iterate. Covers the interactive explorer pattern, the drift-check ritual, and how to bundle a finished explorer for sharing.

## The pre-rendered grid + slider HTML pattern

For continuous parameters, the iteration unit is "try a value, see the result." Doing this in chat is slow. The pattern:

1. **Pick a coarse grid** of candidate values along each axis. For sharpness: `t ∈ [0.00, 0.05, ..., 1.00]` (21 values, step 0.05) gave good resolution in Study 3.
2. **Pre-render every cell** to a PNG with a deterministic filename: `star_t{t:.2f}.png`, `star_p{i:02d}_t{t:.2f}.png` (for 2 axes), etc.
3. **Build an HTML** with sliders / buttons that compute the filename from current state and swap `<img src>`. The image loads instantly; the researcher feels like they're scrubbing a video.

For *n* axes, pre-render the full cross-product. Don't make separate per-axis grids that "snap" the other axis to a default — that forces compromises in the UI ("clicking shuffle resets sharpness") and masks bugs.

### Sizing the grid

- 1 axis × 21 values = 21 PNGs at 500px ≈ 1MB. Trivial.
- 2 axes × (21 × 10) = 210 PNGs ≈ 10MB. Cheap.
- 3 axes × (21 × 10 × 10) = 2,100 PNGs ≈ 100MB. Getting expensive.
- 4+ axes: probably time for live SVG rendering in the browser, or chunk the cross-product by latching one axis.

500px is the sweet spot for explorer PNGs — large enough to see detail, small enough to load instantly. Final shipping stimuli render at 1200px from the same SVG pipeline.

## Browser portability — fetch() vs `<img>`

When the prof opens the HTML by double-clicking (file://), browsers (Chrome / Safari) block `fetch()` for local files (CORS-like restriction). But they DO allow `<img src="local/path.png">` — image elements aren't subject to the same policy.

**Implication:** if your explorer needs a list of asset filenames (e.g., for a "shuffle" button to pick from), **inline the list as a JS array in the HTML**, don't fetch a `manifest.json`. Symptom of getting this wrong: "manifest fails to load" error on the prof's machine but works fine on yours via a local dev server.

Pattern:
```html
<script>
// Inlined from manifest.json — re-paste if regenerated.
const COLOR_FILES = ["star_color_000_...", ...];
</script>
```

## Drift-check against canonical (load-bearing)

Adapted from Jacob's standing rule, formalized after a 7.6% pixel AA drift almost shipped in Study 3:

**At the parameter setting where output is supposed to equal canonical, run a pixel diff and verify it's zero.**

```python
# Render canonical via the same pipeline:
canonical_png = rasterize(canonical_svg)
# Render the build at the preservation parameter:
build_png = rasterize(modulated_svg_at_t1)
# Diff:
diff = np.abs(canonical_arr - build_arr).sum(axis=2) > 0
print(f"{diff.sum()} / {diff.size} pixels differ")
```

If diff > 0, find out why before declaring the build done. In Study 3:
- 7.62% pixels differed at `t=1`, concentrated on outline strokes.
- Root cause: the modulator was splitting cubics at `t=1` losslessly (mathematically equivalent), but the rasterizer subdivides one-vs-two cubics differently for anti-aliasing.
- Fix: `preserve_canonical = (t == 1.0)` special case in modulator — skip modification entirely when `t=1`. After fix: 0 / 250,000 pixels differ.

Also surface the diff in the review HTML, not just chat — a side-by-side image makes drift obvious in a way prose can't.

## Decision-form pattern in the review HTML

When the explorer is also collecting the researcher's choice (rather than just demoing):

- `<fieldset>` with radio options + free-text comment box per question.
- Sticky toolbar with "Copy all responses" (Markdown), "Download JSON", "Clear all".
- localStorage persistence so they can come back across sittings.
- Demote answered questions on re-render — show a slim "your answer" block, not the full form.

Implementation: lift `~/.claude/skills/decision-forms-html/references/form-pattern.js`. Don't re-implement; the persistence + cleanup edge cases are non-trivial.

Skip the decision form when the explorer is purely for show (e.g., showing the prof what the build looks like) — forms become noise when there's no ask back.

## Iteration cycles

For non-trivial parameterized stimuli, plan 2–3 iteration cycles with the researcher:
- **Cycle 1**: catches obvious bugs (wrong colors, missing layers, white slivers around shapes).
- **Cycle 2**: catches things you didn't know to look for (AA drift, subtle pointiness mismatch).
- **Cycle 3**: locks final parameter values.

Each cycle: regenerate explorer → reopen → researcher feedback → propagate to generator → regenerate. Keep the URL stable across cycles so reopening always goes to the latest.

## Bundling for share

When the researcher wants to show the explorer to a third party (advisor, collaborator):

1. **Standalone copy** of the HTML — rename to something clean (e.g., `<project>_designer.html`), drop the `(claude)` suffix.
2. **One image folder** alongside — rename internal directory names if they have `(claude)` or version suffixes. Update the HTML's path constants to match.
3. **No CDN dependencies, no fetch()**. The HTML must be fully self-contained: inline CSS, inline JS, inline asset lists.
4. **Zip the bundle** with the HTML and the image folder at the same level. Recipient unzips and double-clicks the HTML.
5. **Test it** — unzip the bundle to `/tmp/`, open the HTML, verify all controls work. Don't ship without this check.

Study 3 final bundle: `ambiguous_star_designer.zip` with `ambiguous_star_designer.html` + `stars/` (210 PNGs at 500px). 6MB total. Standalone, no setup, works on any modern browser.

## Anti-patterns

- **Don't fetch() local files in shared bundles.** Inline the list. (Covered above; emphasized because the failure is silent — works on dev machine, breaks on recipient's.)
- **Don't bundle the explorer with the lit review or design-decision docs.** Different audiences. The lit review is for you; the explorer is for the researcher.
- **Don't add a README to the bundle** unless the researcher asked. The HTML title + an email from the researcher is enough context.
- **Don't make the explorer depend on the researcher's filesystem layout.** All paths in the shared bundle are relative.
- **Don't use emoji on demo buttons** ("🎲 Shuffle"). Looks AI-generated. Plain text ("Shuffle") reads cleaner.
- **Don't add summary boxes that recap what the user just clicked.** Information overload. The visual change is the feedback.
