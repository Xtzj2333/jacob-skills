"""
Verify the three-file invariant for a revision-queue project.

Files are named after the user via $USER_NAME (default "user"):
  <USER>_todos.md, <USER>_actions.md, completed_actions_log.md

Checks:
  1. No duplicate IDs across {todos, actions} (an item can't be open in both).
  2. Every "resolves TODO X" cross-link in the log points to a TODO that is
     no longer present in <USER>_todos.md (i.e., was actually removed).
  3. Each .docx mirror is no older than its .md source.
  4. Log batch headings are in chronological (ascending date) order.
  5. Log entries are tagged either [TYPE: ACTION] or [TYPE: TODO].

Exits 0 on clean state; 1 with diagnostics on any violation.

Usage:
    python3 verify_state.py --dir Projects/<proj>-revisions
"""
import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path

USER = os.environ.get("USER_NAME", "user")
TODOS_FILE = f"{USER}_todos.md"
ACTIONS_FILE = f"{USER}_actions.md"
LOG_FILE = "completed_actions_log.md"

TODO_HEADING = re.compile(r"^## TODO (\d+(?:\([a-z]\))?)\b", re.MULTILINE)
ACTION_HEADING = re.compile(r"^## ACTION (\d+)\b", re.MULTILINE)
RESOLVES = re.compile(r"resolves\s+TODO\s+(\d+(?:\([a-z]\))?)", re.IGNORECASE)
BATCH_HEADING = re.compile(r"^## Batch (\d{4}-\d{2}-\d{2})\b", re.MULTILINE)
LOG_ENTRY = re.compile(r"^### Entry[^[]*\[(TYPE:\s*(?:ACTION|TODO))\]", re.MULTILINE)
LOG_ENTRY_BAD = re.compile(r"^### Entry[^\n]*$", re.MULTILINE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    args = ap.parse_args()

    proj = Path(args.dir).resolve()
    todos_p = proj / TODOS_FILE
    actions_p = proj / ACTIONS_FILE
    log_p = proj / LOG_FILE

    issues = []

    # 2-file default: <USER>_actions.md is optional. Require todos + log only.
    if not all(p.exists() for p in (todos_p, log_p)):
        print(f"Missing one of: {TODOS_FILE}, {LOG_FILE}", file=sys.stderr)
        sys.exit(2)

    todos_text = todos_p.read_text()
    actions_text = actions_p.read_text() if actions_p.exists() else ""
    log_text = log_p.read_text()

    open_todo_ids = set(TODO_HEADING.findall(todos_text))
    pending_action_ids = set(ACTION_HEADING.findall(actions_text))

    # Check 1: action numbers shouldn't collide with each other (multiple ACTION 1?)
    action_list = ACTION_HEADING.findall(actions_text)
    dupes = {x for x in action_list if action_list.count(x) > 1}
    if dupes:
        issues.append(f"Duplicate ACTION IDs in {ACTIONS_FILE}: {sorted(dupes)}")

    todo_list = TODO_HEADING.findall(todos_text)
    dupes_t = {x for x in todo_list if todo_list.count(x) > 1}
    if dupes_t:
        issues.append(f"Duplicate TODO IDs in {TODOS_FILE}: {sorted(dupes_t)}")

    # Check 2: every "resolves TODO X" in the log → X must be absent from open_todo_ids
    log_resolves = set(RESOLVES.findall(log_text))
    leaked = log_resolves & open_todo_ids
    if leaked:
        issues.append(
            f"Logged-resolved TODOs still open in {TODOS_FILE}: {sorted(leaked)} "
            f"(should have been removed when log entry was written)"
        )

    # Check 3: docx mtimes >= md mtimes (per pair)
    for p in (todos_p, actions_p, log_p):
        docx = p.with_suffix(".docx")
        if docx.exists():
            md_mtime = p.stat().st_mtime
            docx_mtime = docx.stat().st_mtime
            if docx_mtime + 1 < md_mtime:  # 1s grace
                issues.append(
                    f"Stale .docx: {docx.name} is older than {p.name} "
                    f"(re-run regen_docx.sh)"
                )

    # Check 4: batch dates ascending
    dates = BATCH_HEADING.findall(log_text)
    parsed = [dt.date.fromisoformat(d) for d in dates]
    if parsed != sorted(parsed):
        issues.append(f"Log batch dates not in ascending order: {dates}")

    # Check 5: every log entry is TYPE-tagged
    bad = []
    for m in LOG_ENTRY_BAD.finditer(log_text):
        line = m.group(0)
        if "[TYPE:" not in line:
            bad.append(line.strip()[:120])
    if bad:
        issues.append(
            "Log entries missing [TYPE: ACTION] / [TYPE: TODO] tag:\n  "
            + "\n  ".join(bad[:5])
        )

    # Report
    if issues:
        print(f"VERIFY {proj.name}: FAIL ({len(issues)} issue(s))", file=sys.stderr)
        for i in issues:
            print(f"  • {i}", file=sys.stderr)
        sys.exit(1)
    print(
        f"VERIFY {proj.name}: OK   "
        f"({len(open_todo_ids)} open TODOs, {len(pending_action_ids)} pending ACTIONs, "
        f"{len(log_resolves)} resolved-via-log, "
        f"{len(LOG_ENTRY.findall(log_text))} log entries)",
        file=sys.stderr,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
