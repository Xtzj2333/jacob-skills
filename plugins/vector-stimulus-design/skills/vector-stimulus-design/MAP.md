# MAP — vector-stimulus-design skill

## Status

Work-in-progress. Distilled from one project: Study 3 puzzle-star stimuli (May 2026, Complexity vs. Monotonous lab).

## Files in this folder

| File | Role |
|---|---|
| `SKILL.md` | Entry point. Frontmatter + when-to-use + decision flow + key principles + WIP note. Read first. |
| `references/techniques.md` | Concrete technical patterns: vector extraction, layer detection, Bézier math for shape editing, color permutation styles, rasterizer landscape, reproducibility hygiene. |
| `references/review-workflow.md` | Operational patterns: pre-rendered grid + slider HTML, drift-check against canonical, decision-form usage, bundling for share, anti-patterns. |
| `MAP.md` | This file. |

## Source materials (canonical, not duplicated)

The full worked example and lit-review materials stay in the originating project. Don't move or copy these into the skill folder — point to them, and trust the canonical location to evolve.

| Location | What's there |
|---|---|
| `~/Claude/Potentials Lab/Complexity vs. Monotonous/Study 3/graphic_design_lessons (claude).html` | 20-lesson rendered HTML report. The fully-walked-through worked example with code samples for every pattern. |
| `~/Claude/Potentials Lab/Complexity vs. Monotonous/Study 3/ai_stimulus_genai_litreview (claude).html` | Lit review on AI stimulus-generation tools (rasterizer comparison, vector tool survey). Now reference-only. |
| `~/Claude/Potentials Lab/Complexity vs. Monotonous/Study 3/code (claude)/` | Working Python implementation of the modulator + recolor + generator + explorer scripts. Read these for "how would I actually write this." |
| `~/Claude/Potentials Lab/Complexity vs. Monotonous/Study 3/MAP.md` | Project-level orientation. Links back to this skill. |

## Related memories

| Memory | What's there |
|---|---|
| `~/.claude/projects/-Users-jacobzhang-Claude-Potentials-Lab/memory/reference_shape_editing_for_stimuli.md` | Initial distillation, predecessor to `techniques.md`. |
| `~/.claude/projects/-Users-jacobzhang-Claude-Potentials-Lab/memory/feedback_compare_with_canonical_source.md` | The "always pixel-diff against canonical" rule that drives the drift-check ritual. |
| `~/.claude/projects/-Users-jacobzhang-Claude-Potentials-Lab/memory/reference_study3_ai_files_palette.md` | Specifically: where the Study 1 `.ai` files live + the canonical palette hex values. |

## What to update when this skill matures

- After a 2nd project uses this skill: prune any pattern that turned out to be Study-3-specific. Promote anything that recurred.
- After a 3rd project: remove the WIP marker if patterns are stable.
- Track unresolved questions in `SKILL.md` § "Origin and unresolved questions" — update as they resolve.
