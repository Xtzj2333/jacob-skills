---
name: tony-github-push
description: Push manuscript edits from a configured local subdirectory to a configured branch on a configured GitHub remote. **Trigger ONLY when the user explicitly says one of:** "tony github push", "tony and github push them", "push tony", "push to tony's github", "push to tony", or invokes "/tony-github-push". Do NOT auto-trigger on generic "git push", "push the manuscript", or "commit and push" — those should defer to normal git workflow with user confirmation. Skill scope: stage + commit + push exactly what the user has changed, force-push on conflict (the user's branch is authoritative). Never edit, regenerate, rename, or reformat files on Claude's own initiative.
allowed-tools:
  - Bash
  - Read
---

# tony-github-push

Skill for pushing manuscript edits to a collaborator-owned GitHub repo, on the user's behalf, on the user's working branch.

## Configuration (read these from the user's environment, not from this file)

This skill is *intentionally* parameterized so the public skill-marketplace copy doesn't hardcode a private repo URL. Read the values below from the user's local config:

| Variable | Default | Where to set |
|---|---|---|
| `MANUSCRIPT_DIR` | `manuscript_repo_tony` | Subdirectory inside the working bundle that contains the git working tree to push. |
| `MANUSCRIPT_REMOTE` | *(no default — required)* | Full GitHub remote URL of the collaborator's manuscript repo. |
| `MANUSCRIPT_BRANCH` | `jacob` | Branch on `MANUSCRIPT_REMOTE` that the user owns / overwrites. |

The user typically configures these in `~/.claude/CLAUDE.md` or a project-local `CLAUDE.md`. If `MANUSCRIPT_REMOTE` is not set when the skill fires, **ask the user** before proceeding.

## The push contract

Three rules. Follow them exactly.

1. **Only `${MANUSCRIPT_DIR}` is pushed.** Everything inside that folder's working tree goes to GitHub — nothing from elsewhere in the bundle (sibling folders, top-level files like `MAP.md`, etc.) is pushed. Run all `git` commands from inside `${MANUSCRIPT_DIR}`. Never `git init`, `git add`, or `git push` from anywhere else.

2. **Push target is the branch `${MANUSCRIPT_BRANCH}`.** If it does not exist locally, create it (`git checkout -b ${MANUSCRIPT_BRANCH}`). On the first push, set upstream (`git push -u origin ${MANUSCRIPT_BRANCH}`). The remote URL is `${MANUSCRIPT_REMOTE}`.

3. **On conflict, overwrite.** If a push is rejected (non-fast-forward / remote `${MANUSCRIPT_BRANCH}` diverged), force-push: `git push --force origin ${MANUSCRIPT_BRANCH}`. The user's local state is authoritative for `${MANUSCRIPT_BRANCH}` — overwrite whatever is on the remote.

## Scope rule — what Claude does and does not do

Claude's job is to **stage, commit, and push whatever the user has changed**. Nothing more.

- Do **not** edit files on Claude's own initiative.
- Do **not** regenerate the `.md` from the `.docx` (or vice versa) — even if they no longer match.
- Do **not** rename files, reformat, "clean up," or apply any naming conventions.
- Do **not** touch any file the user did not edit.

If the user only edited the `.docx`, only the `.docx` change is committed and pushed. Push exactly what the user produced.

## Standard workflow

Always show the user the planned commands first (briefly), then execute. Never push without showing what's about to happen.

```bash
cd "${MANUSCRIPT_DIR}"

# Show current state — staged, unstaged, untracked
git status

# Diff for review (paginated)
git diff --stat

# Ensure we're on the user's branch (create if missing)
git checkout "${MANUSCRIPT_BRANCH}" 2>/dev/null || git checkout -b "${MANUSCRIPT_BRANCH}"

# Stage everything the user changed in this folder
git add -A
git commit -m "<short description of the edit>"

# Push; if rejected as non-fast-forward, overwrite the remote branch
git push -u origin "${MANUSCRIPT_BRANCH}" || git push --force origin "${MANUSCRIPT_BRANCH}"
```

## Procedure when invoked

1. **Verify configuration.** Confirm `MANUSCRIPT_DIR`, `MANUSCRIPT_REMOTE`, and `MANUSCRIPT_BRANCH` are known. If `MANUSCRIPT_REMOTE` is missing, ask.
2. **Confirm scope.** `cd "${MANUSCRIPT_DIR}" && git status && git diff --stat` — show what will be staged. If anything looks unexpected (files the user didn't intend to change), pause and ask.
3. **Draft the commit message.** Short, factual, in the style of the repo's recent commits. Run `git log --oneline -5` if unsure of style.
4. **Confirm before pushing.** Show the user the commit message and the file list one more time. Wait for green light.
5. **Push.** Use the workflow above. If the first `git push` fails with non-fast-forward, run `git push --force origin "${MANUSCRIPT_BRANCH}"` per the contract.
6. **Confirm.** `git log --oneline -3` to show the new commit landed; report the GitHub URL the user can open to verify.

## Failure modes (avoid these)

| Mode | Fix |
|---|---|
| Pushing from outside `${MANUSCRIPT_DIR}` | All commands `cd` into `${MANUSCRIPT_DIR}` first |
| Pushing to `main` or another protected branch instead of `${MANUSCRIPT_BRANCH}` | Always `git checkout "${MANUSCRIPT_BRANCH}"` (or create) before `git push` |
| Force-pushing without authorization on a non-`${MANUSCRIPT_BRANCH}` branch | The force-push rule applies *only* to `${MANUSCRIPT_BRANCH}`. Never force-push `main` or any other branch |
| Auto-regenerating `.md` from `.docx` to "make them match" | Do NOT. Push exactly what the user staged. Mismatch is the user's call |
| Bundling unrelated changes into a commit | If the user edited multiple files, ask whether they want one commit or several |
| Pushing committed `.DS_Store` or `~$*.docx` lock files | Verify `.gitignore` excludes these before staging; if not, add them and commit the `.gitignore` change separately |
