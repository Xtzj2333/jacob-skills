# <PROJECT> — Actions to Execute

**Audience:** a fresh Claude Code session that the user will hand this file to.
**Status:** queue of executable items the user has explicitly approved. Anything outside this file is **not** approved.

## Lifecycle

1. Items are first discussed in `the project's todos file` (with screenshots, options, recommendations).
2. When the user picks a resolution, the item is **promoted** here as an ACTION block (file path, exact find-text, exact replace-text, verification command, recompile note).
3. A fresh Claude session executes the ACTION blocks via `execute_action.py`.
4. After successful execution, the executor (the script) automatically:
   - Appends an `[TYPE: ACTION]` entry to the project's completed-actions log with `before / after / why / verification`.
   - **Removes** the executed ACTION block from this file (so this file always reflects pending work only).
   - Removes the originating TODO row from `the project's todos file`.

The completed-actions log is the single chronological source of truth for resolved items; this file shows only what's still open.

## Repo context

- Working directory: `<absolute path to repo root>`
- Main artifact: `<relative path>`
- Build command: `<e.g. cd ... && latexmk -pdf -bibtex -silent main.tex>`
- Do **not** run `git push`. Do **not** delete files unless an ACTION below explicitly says so.

## Verification before editing

Line numbers below are accurate as of the timestamp on each ACTION block. **Before applying any line-numbered edit, re-grep for the surrounding context** to confirm the line hasn't drifted. The exact prose to find is quoted in each action.

---

## Pending ACTIONs

*(none — when there are pending items, append `## ACTION N — title` blocks below using the template at the bottom of this file.)*

---

## ACTION block template (copy this when promoting a TODO)

```markdown
## ACTION N — Short title (resolves TODO X)

**Goal:** One-sentence description of what this changes and why the user approved it.

**File:** path/to/file.tex (or .bib, etc.)

**Find this exact passage (around line LLL):**

```latex
<verbatim quote of current text — must be unique enough to anchor the edit>
```

**Replace with:**

```latex
<verbatim quote of new text>
```

**Verification after edit:**

```bash
grep -n "..." path/to/file.ext
# Should return ... hits.
```

**Recompile:** Yes / No (Yes if it touches anything that affects the rendered output).
```

---

## What's NOT in this file (still open in `the project's todos file`)

*(list TODOs that are still under discussion, with one-line summaries — keep this in sync as items move)*
