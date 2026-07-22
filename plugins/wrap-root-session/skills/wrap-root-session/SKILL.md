---
name: wrap-root-session
description: Use when a Claude Code session run from ~/Claude (the workspace root) is ending and its artifacts sit loose — new files at root, in Unordered/, or scattered across folders — and Jacob wants the session's work tidied into one self-contained folder. Triggers: "organize this session's files into a folder", "wrap up this session", "I'm going to close this session", "/wrap-root-session". Also fires proactively at session close when this session created root-level or Unordered/ files on a topic with no owning folder.
---

# wrap-root-session

## Overview

Sessions launched from `~/Claude/` often create files "for convenience" at root or in `Unordered/`. When such a session ends, its work should leave the root and become one self-contained, self-orienting folder that a future session (or future Jacob) can pick up cold — files plus the context that exists only in the conversation. The folder is the session's durable memory; the chat is about to be closed.

**Core principle: nothing valuable may exist only in the conversation after wrap-up.** Files are easy; the knowledge (status, decisions, dead ends, next actions) is what evaporates when the session closes.

## When NOT to use

- The session's files already live in an owning project folder (Culture Lab, Oishi Lab, a manuscript repo…) — file them there per that project's conventions instead; no new root folder.
- Single throwaway artifact with no follow-up work → `Unordered/` (per root MAP.md convention) is fine; don't create a folder for one dead file.
- The work belongs to an existing workstream folder (check root `MAP.md` first) — extend that folder, don't fork a sibling.

## The recipe

Work through all six steps in one turn. The steps assemble everything, then commit atomically — content written in steps 3–4 may reference destination paths that only exist after step 5's moves.

### 0. Close what's trivially closable first

If the session left an agreed piece of *work* unfinished that would take minutes (a small edit, one more section), offer to finish it before freezing state — don't silently archive a 10-minute job as a future session's task. External-world loops (unsent drafts, pending replies) are different: those get recorded, not rushed.

### 1. Inventory this session's footprint

List every file this session created or modified: at root, in `Unordered/`, in `reports/`, in any project folder, plus root `MAP.md` lines added earlier in the session. Include artifacts delivered elsewhere (an unsent email draft, a published page) — those are *facts to record in the handoff*, not files to move.

### 2. Choose the destination

Read root `MAP.md`. If an existing folder owns the topic *as a workstream* (someone is doing this work there), use it and stop creating structure. An umbrella folder that merely could contain the topic (`Personal/` for anything personal) doesn't count unless Jacob says so. Otherwise create ONE new folder at `~/Claude/` with a plain-English name Jacob would say out loud ("Harvard forgiveness stipend", not "hfs-stipend-tracker"). Topic folders carry no `(claude)` suffix — AI authorship is recorded in the folder MAP.md's Provenance section (and by the `reports (claude)/` subfolder name, when present).

### 3. Build the standard skeleton

```
<Topic name>/
├── MAP.md              ← orientation: what this is, structure, provenance, shareability
├── HANDOFF.md          ← the session's context & knowledge (see step 4)
└── reports (claude)/   ← rendered deliverables (HTML, docx/pdf), if any
    ├── CATALOG.md      ← per reports-catalog skill
    └── <files>
```

Route each file by what it IS:

- **Reports about the work** (rendered briefs, chat-substitutes, review HTMLs) → `reports (claude)/` with a `CATALOG.md` row (invoke `reports-catalog`; chat-substitutes keep their stable un-prefixed filenames under "Conversation surfaces").
- **The work itself — living tools, apps, dashboards Jacob reopens or reruns** → folder top level (or a plain subfolder), keeping their stable filename. NO catalog row, NO `s.v` prefix — versioned renaming breaks bookmarks and muscle memory. Provenance goes in MAP.md.
- **Scratch notes that fed real knowledge into the HANDOFF** → move in as the raw record (per global CLAUDE.md §6, superseded ≠ garbage). Only truly contentless leftovers get deleted.
- **Data, scripts, source material** → sibling subfolders as needed, `(claude)`-flagged where the convention applies.

### 4. Write the HANDOFF.md — the load-bearing step

Written for a cold reader. Must contain, in roughly this order:

1. **What this is** — one paragraph, no session jargon.
2. **Status right now** — what is done, what is mid-flight (e.g. "reply composed but NOT sent; stub sits in Outlook Drafts"), any environment constraints discovered (e.g. "Claude's M365 connection is read-only").
3. **Key verified facts** — the concrete knowledge the session dug up (names, ticket numbers, dates, root causes), so nobody re-does the archaeology.
4. **Decisions made and their why** — including reversals ("previously offered X; current intent is Y — keep future work consistent with Y").
5. **Next actions, in order** — concrete, starting with the very next physical step.
6. **Pointers** — where the full detail lives (files in this folder, external threads/systems by name).

When a constraint concerns a specific artifact that will outlive the handoff ("open in Chrome, not Safari"), also embed it in the artifact itself — an HTML comment, a visible badge, a header line — not only in HANDOFF.md.

### 5. Move files and fix what the move breaks

Move (don't copy) the inventoried files in. Then:

- Grep moved HTML/markdown for self-referencing paths (footers, source lists) and update them.
- If a browser tab was opened on the old path this session, `open` the new path.
- Moves also break what only Jacob can fix — bookmarks, dock aliases, muscle-memory paths. State the new path explicitly in the closing chat message for anything he actively uses.
- Never delete Jacob-authored content without asking; scratch notes follow the routing rule in step 3.

### 6. Update root MAP.md in the same turn

- Add the folder to the top-level tree with a one-line description (mark it self-orienting: "see HANDOFF.md").
- Remove superseded lines, if any (e.g. the file's old `Unordered/` bullet). Files never registered in MAP.md have nothing to remove — verify rather than hunt.
- Add a dated History entry naming what moved and any still-open item.

## Quick reference

| Artifact | Where it goes |
|---|---|
| Report / chat-substitute HTML | `<Topic>/reports (claude)/` + CATALOG.md row |
| Living tool, app, dashboard | `<Topic>/` top level, stable filename, no catalog row |
| Scratch notes that fed the HANDOFF | `<Topic>/`, kept as raw record |
| Session knowledge, open loops, constraints | `<Topic>/HANDOFF.md` (+ embedded in the artifact if artifact-specific) |
| Folder orientation & provenance | `<Topic>/MAP.md` |
| Root bookkeeping | root `MAP.md`: tree + removals + History, same turn |
| Cross-project lessons (rare) | Claude memory — propose to Jacob, don't silently write |

## Common mistakes

- **Filing a living tool into `reports (claude)/` with a versioned name.** The catalog scheme is for review-round deliverables that get superseded; renaming and burying a tool Jacob reopens daily breaks its path. Tools keep stable names at folder top level.
- **Deleting scratch notes because the HANDOFF "absorbed" them.** The notes are the raw record and usually hold detail the summary dropped. Keep them.
- **HANDOFF that only says what was done.** The cold reader needs what's *open* and *why decisions went the way they did* more than a done-list. Lead with status and next actions.
- **Root MAP.md not updated in the same turn** — the tree, the stale `Unordered/` bullet, and History all drift.
- **Stale self-referencing paths** inside moved HTML (footer still points at the old location).
- **Copies left behind** in `Unordered/` or at root after the "move".
- **Folder for a dead one-off.** If there is no conceivable follow-up, `Unordered/` was already correct — don't create ceremony.
- **Burying a mid-flight external action.** An unsent draft, a pending reply, a ticket awaiting response must appear in HANDOFF "Status right now", or the next session won't know the ball is in Jacob's court.
- **Freezing work that step 0 could have finished.** Offer before archiving.

## Worked example

The 2026-07-22 wrap-up that motivated this skill: a session that reconstructed the Harvard forgiveness-stipend email saga had left one chat-substitute HTML in `Unordered/`. Wrap-up produced `~/Claude/Harvard forgiveness stipend/` with MAP.md, a HANDOFF.md (status: "reply composed but not sent — paste from the HTML into the Outlook stub draft"; key facts: ticket number, the old-hotmail root cause; next actions in order), the HTML moved to `reports (claude)/` with a CATALOG.md, its footer path fixed, and root MAP.md updated (tree + Unordered bullet removed + History entry) — all in one turn.
