# Techniques — vector stimulus design

Concrete technical patterns. Each section answers "how do I do X cleanly, having seen what breaks in Study 3."

## Extraction from Adobe Illustrator

- `.ai` files are PDF 1.6 documents under the hood. Extract losslessly with:
  ```
  pdftocairo -svg input.ai output.svg
  ```
  No Illustrator app needed, no re-export ask, no fidelity loss.
- The resulting SVG has every path as a literal `<path>` with `fill="rgb(...)"` or `stroke="..."`. Designer's intent is preserved exactly.
- **Don't pixel-sample colors from PNG exports.** Sub-sampling + JPEG round-trips desaturate. Study 3 v9 used pixel-sampled palette `#71BFD5...` (~10–15% desaturated); v10 corrected by pulling from the vector source: `#64C3DD #8BC79C #F6A34F #EE726A`.

## Locking the canonical

- Before any automated edits, immutability-flag the canonical extract:
  ```
  chflags uchg canonical.svg
  ```
  System-level immutability on macOS — even `rm -f` fails. Removes with `chflags nouchg`.
- Pattern: **copy + lock + point pipelines at the copy**. The canonical extract lives in `stimuli_v10/canonical_p1.svg` (locked); modulators read from it and write to derivative directories.

## Layer structure of Illustrator SVG exports

- Illustrator exports a star (or any filled-shape-with-outline) as **two distinct layers**:
  - **Fill paths**: `fill="rgb(...)" stroke="none"` — colored regions.
  - **Outline path**: `fill="none" stroke="..."` — the dark outline drawn on top.
- Modifying only fill paths → outline misalignment artifacts (visible as white slivers between fills and outline).
- Identify the outline path before editing. Heuristic that works:
  - `fill="none"` AND has a `stroke` AND its transformed bbox matches the overall shape bbox.

## Transforms

- Some paths carry `transform="matrix(1, 0, 0, -1, e, f)"` — that's a Y-flip + translate. Local path coordinates look unrelated to where it actually renders.
- When matching features across paths (e.g., "this fill's tip aligns with this outline's tip"), compute effective bbox **after** applying the transform. Don't compare raw coordinates.

## Bézier math for tip / corner shaping

The trick for making a tip "sharper" or "rounder" without changing path topology:

1. **De Casteljau split** at `t=0.5` turns one cubic into two cubics that together reproduce the original exactly.
2. **A cubic with inner controls equal to its endpoints `[A, A, B, B]` is a straight line.** Combine with the split: now each half can have a straight-line portion meeting at a cusp.
3. **Apex extension** for spiky cusps beyond the canonical's natural bulge:
   ```
   M_far = chord_mid + K · (M_canon − chord_mid)
   ```
   `K=1` reproduces the original. `K=3` is visibly pointy. `K=5` is needle-sharp.
4. **CRITICAL — special-case the canonical endpoint.** Even when the split is mathematically lossless, rasterizers subdivide two cubics differently than one for anti-aliasing. At the parameter value where output should equal canonical (e.g., `t=1`), emit the original cubic UNCHANGED. Otherwise you get sub-pixel AA drift. (See `review-workflow.md` for the comparison test that catches this.)

## Sub-pixel mismatch between layers

- Outline and fill anchors at the same visual feature can differ by 0.05–7pt (designer hand-snapping during authoring).
- Each layer modulating independently → drift accumulates → visible slivers.
- Fix: **first-pass scan to compute shared geometric anchors in PAGE coords**, then second-pass apply with each layer matching by proximity. One source of truth per feature, multiple layers converge.

## Color permutation styles

Distinct constraints with different combinatorics — clarify which the researcher means **before** implementing:

- **Palette-permutation**: globally remap each color (`blue → green`, etc.) for all pieces of that color simultaneously. Count distribution preserved, but which colors hold which counts changes. 4 colors → 4! = 24 variants.
- **Piece-permutation**: per-piece independent color assignment, constrained to preserve **global counts**. Every stimulus has exactly the same color tally. 9 pieces with counts (3,2,2,2) → 9! / (3!·2!·2!·2!) = 7,560 variants.
- For psychophysics: piece-permutation is almost always what's wanted (variation in spatial arrangement, identical color statistics).
- Study 3 implementation: hardcode `CANONICAL_PIECE_COLORS = [...]` (one color per piece slot), then `random.shuffle()` for permutations.

## Rasterization landscape

For SVG → PNG:

- **`resvg_py`** (Rust binding): fastest, modern, recommended default. `pip install resvg-py`. Used in Study 3.
- **`rsvg-convert`** (librsvg CLI): `brew install librsvg`. Reliable, ~3× slower than resvg.
- **`cairosvg`**: often blocked on Anaconda Python because libcairo isn't shipped. `brew install cairo` is a system-wide install requiring permission. Avoid for research repos that need to run on a colleague's machine.
- For research-grade exactness: **render the same SVG through two engines** and pixel-diff. Divergence ≠ engine bug; usually it means your SVG has a path-spec ambiguity (overlapping fills, undefined fill-rule, etc.) that engines resolve differently.

## Reproducibility

- **Seed every RNG with an integer you record.** Date-as-int (`20260516`) is fine and self-documenting.
- **Write a `manifest.json` per stimulus set.** Record: timestamp, seed, source file SHA, generator version, per-stimulus parameters, output filenames. Enables OSF preregistration, replication, and "what did I actually build" debugging when you come back in 6 months.
- Naming convention that lets the consumer compute paths without a manifest: `star_p{i:02d}_t{t:.2f}.png` — deterministic structure means JS or downstream code can index without a lookup table.

## Code organization

Pattern that scaled cleanly across Study 3 iterations — small composable scripts, one per stage:

- `inspect_canonical.py` — orientation; print layer structure, color counts, bbox info
- `<feature>_modulator.py` — geometric edit (e.g., `round_star_tips.py`)
- `recolor.py` — color assigner (`recolor_pieces`, `random_piece_assignments`)
- `generate.py` — driver combining modulators with seed + manifest
- `rasterize_compare.py` — cross-engine sanity check
- `explorer_gen.py` — pre-render single-axis grid
- `explorer_composed_gen.py` — pre-render cross-product grid for two-axis explorers

Each script does one thing. Each is importable. Each iteration = one Python run + one HTML reopen. When something breaks, you change one file.

## Project layout

What worked for Study 3:

```
Study 3/
├── canonical/(source)/          # locked original .ai + extracted .svg
├── stimuli_v10 (claude)/        # final shipping stimuli
├── stimuli_v10_explorer (claude)/    # single-axis (shape) grid for explorer
├── stimuli_v10_composed (claude)/    # cross-product grid (shape × color)
├── code (claude)/               # all generator scripts
├── study3_tip_explorer (claude).html # interactive review HTML
├── graphic_design_lessons (claude).html # 20-lesson distillation
└── MAP.md                       # project orientation
```

The `(claude)` suffix flags AI-generated content for human review (per Jacob's filesystem convention). The `(source)` suffix flags read-only canonical assets.
