---
name: vector-stimulus-design
description: Use when generating parameterized research stimuli from designer vector source files (Adobe Illustrator .ai, .svg). Covers lossless extraction, shape editing, color permutation, rasterization, reproducibility, and the review workflow for collaborating with a researcher on stimulus choice.
---

# Vector stimulus design

> **Status: work-in-progress.** Distilled from one project — Study 3 puzzle-star stimuli, May 2026 (Complexity vs. Monotonous, Jacob Zhang). Patterns are tested in that build but haven't yet been re-validated across multiple projects. Update as you find what generalizes.

## When to use this skill

Invoke when the task involves all three of:
1. A **designer-authored vector asset** as the starting point (Adobe `.ai`, hand-drawn `.svg`, etc.) — not Claude-generated art.
2. **Parameterized variants** along one or more axes (shape, color, scale, orientation) — not a single rendering.
3. **A researcher in the loop** who will choose final parameter values from candidates — not a fire-and-forget render.

Concrete triggers:
- "Generate N stimuli from this .ai file"
- "I have an Illustrator file, I need variants that vary along X"
- "Pre-render a parameter grid so we can pick values together"
- "Build research stimuli with consistent quality, derived from this canonical art"

If the task is just "render an SVG" or "make a chart", that's not this skill. The defining shape here is *canonical-derived parameterization for research stimuli*, with a human picking the final settings.

## Decision flow

1. **Extract.** `pdftocairo -svg input.ai output.svg` — `.ai` is PDF-1.6, lossless SVG comes out. No Illustrator needed.
2. **Lock the canonical.** `chflags uchg canonical.svg` on macOS so no pipeline step can mutate it. Copy + lock, then point everything at the copies.
3. **Inspect layer structure.** Illustrator exports have separate **fill** and **outline** paths. Identify both before editing — modifying only fills produces visible misalignment artifacts. Some paths have `matrix(1, 0, 0, -1, e, f)` Y-flip transforms; compute effective bbox post-transform when searching.
4. **Sample canonical features from the vector.** Colors: pull the literal `fill="rgb(...)"` from every path. Geometry: parse the Bézier anchors. Never pixel-sample from a rasterized PNG — sub-sampling desaturates.
5. **Decide axes of variation.** Shape (sharpness, scale)? Color (palette swap, piece permutation)? Both? Each axis needs a modulator and a grid.
6. **Pre-render the grid.** For *N* axes, pre-render the cross-product, not each axis in isolation. Disk is cheap; live SVG-to-PNG in the browser is not.
7. **Build the interactive review HTML.** Sliders + buttons swap `<img src>` against the pre-rendered grid. See `references/review-workflow.md`.
8. **Drift-check against canonical.** Render the canonical via the same pipeline and pixel-diff at the parameter setting that's supposed to preserve it. AA artifacts are invisible at a glance but lethal for replication.
9. **Surface for researcher choice.** Decision-form pattern (radios + free text + Copy all). Iterate on their feedback.
10. **Lock + manifest.** Record seed, source SHA, generator version, per-stimulus parameters in `manifest.json`. Enables preregistration and "what did I actually build" debugging.

## Key principles

1. **Vector source is gold.** Sample features from the vector file, never from a rasterized export.
2. **Lock the canonical before automated edits.** `chflags uchg`. Copy + lock + point pipelines at copies.
3. **Always compare against canonical at the preservation endpoint.** AA drift hides in plain sight. The Study 3 build almost shipped with a 7.6% pixel diff at `t=1` because the modulator was splitting cubics losslessly but the rasterizer subdivides one-vs-two cubics differently. Caught by the drift-check, fixed with a special case.
4. **Pre-render, don't compute live.** Browser-side SVG generation is slow and bug-prone; pre-rendered PNGs are fast and reproducible.
5. **Compose axes by cross-product.** If a stimulus varies along (shape × color), pre-render all (perm × t) combinations so axes work independently. Isolated single-axis grids force the UI to "snap" one axis when the other changes — bad UX, masks bugs.
6. **Default to keeping.** Discarded variants are research record, not garbage. Classify (canonical / current / prior-gen archive / scratch); never delete without explicit researcher OK.
7. **One driver script per stage.** Small composable scripts beat one monolith. Typical layout: `inspect_canonical.py`, `<feature>_modulator.py`, `recolor.py`, `generate.py`, `rasterize_compare.py`, `explorer_gen.py`, `explorer_composed_gen.py`.

## References

- `references/techniques.md` — concrete technical patterns: extraction, layer detection, Bézier math, color permutation styles, rasterizer landscape, reproducibility.
- `references/review-workflow.md` — collaboration patterns: HTML explorer with pre-rendered grid, drift-check, decision-form, bundling for share.

## Origin and unresolved questions

Distilled from Study 3 puzzle-star build (Complexity vs. Monotonous lab project). Full worked example at `~/Claude/Potentials Lab/Complexity vs. Monotonous/Study 3/graphic_design_lessons (claude).html` and accompanying code at `Study 3/code (claude)/`.

Still unproven across projects:
- Does the de Casteljau-split approach for sharp cusps generalize to non-tip features (curved edges, holes, internal cutouts)?
- Cross-product pre-rendering was fine for 2 axes × ~10 values each (~210 PNGs). At 3+ axes, the cube explodes — at what point does on-the-fly browser SVG generation become necessary?
- The drift-check rule caught one issue in one build. Validate it fires usefully in non-tip-shape tasks.
- Piece-permutation vs palette-permutation framing assumed discrete pieces; what's the analog for continuous-tone art?

Update this skill when these get answered, and prune anything that turns out to be Study-3-specific rather than generalizable.
