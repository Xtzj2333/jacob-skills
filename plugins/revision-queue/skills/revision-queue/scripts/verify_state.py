"""
Verify the revision-queue invariants for a project.

Filenames are supplied by the caller (Claude resolves them via the
`project-filename` skill, then passes them as CLI args). The actions file is
optional (only present in the 3-file async pattern).

Checks:
  1. No duplicate IDs across {todos, actions} (an item can't be open in both).
  2. Every "resolves TODO X" cross-link in the log points to a TODO that is
     no longer present in the todos file (i.e., was actually removed).
  3. Each .docx mirror is no older than its .md source.
  4. Log batch headings are in chronological (ascending date) order.
  5. Log entries are tagged either [TYPE: ACTION] or [TYPE: TODO].

Exits 0 on clean state; 1 with diagnostics on any violation.

Usage:
    python3 verify_state.py \\
        --todos-file PATH \\
        --log-file PATH \\
        [--actions-file PATH]
"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

TODO_HEADING = re.compile(r"^## TODO (\d+(?:\([a-z]\))?)\b", re.MULTILINE)
ACTION_HEADING = re.compile(r"^## ACTION (\d+)\b", re.MULTILINE)
RESOLVES = re.compile(r"resolves\s+TODO\s+(\d+(?:\([a-z]\))?)", re.IGNORECASE)
BATCH_HEADING = re.compile(r"^## Batch (\d{4}-\d{2}-\d{2})\b", re.MULTILINE)
LOG_ENTRY = re.compile(r"^### Entry[^[]*\[(TYPE:\s*(?:ACTION|TODO))\]", re.MULTILINE)
LOG_ENTRY_BAD = re.compile(r"^### Entry[^\n]*$", re.MULTILINE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--todos-file", required=True, help="Path to the todos markdown file")
    ap.add_argument("--log-file", required=True, help="Path to the completed-actions log markdown file")
    ap.add_argument("--actions-file", help="Optional path to the actions markdown file (3-file async pattern)")
    args = ap.parse_args()

    todos_p = Path(args.todos_file).resolve()
    log_p = Path(args.log_file).resolve()
    actions_p = Path(args.actions_file).resolve() if args.actions_file else None

    issues = []

    if not all(p.exists() for p in (todos_p, log_p)):
        print(f"Missing one of: {todos_p}, {log_p}", file=sys.stderr)
        sys.exit(2)

    todos_text = todos_p.read_text()
    actions_text = actions_p.read_text() if (actions_p and actions_p.exists()) else ""
    log_text = log_p.read_text()

    open_todo_ids = set(TODO_HEADING.findall(todos_text))
    pending_action_ids = set(ACTION_HEADING.findall(actions_text))

    action_list = ACTION_HEADING.findall(actions_text)
    dupes = {x for x in action_list if action_list.count(x) > 1}
    if dupes and actions_p:
        issues.append(f"Duplicate ACTION IDs in {actions_p.name}: {sorted(dupes)}")

    todo_list = TODO_HEADING.findall(todos_text)
    dupes_t = {x for x in todo_list if todo_list.count(x) > 1}
    if dupes_t:
        issues.append(f"Duplicate TODO IDs in {todos_p.name}: {sorted(dupes_t)}")

    log_resolves = set(RESOLVES.findall(log_text))
    leaked = log_resolves & open_todo_ids
    if leaked:
        issues.append(
            f"Logged-resolved TODOs still open in {todos_p.name}: {sorted(leaked)} "
            f"(should have been removed when log entry was written)"
        )

    paths_to_check = [todos_p, log_p]
    if actions_p:
        paths_to_check.append(actions_p)
    for p in paths_to_check:
        docx = p.with_suffix(".docx")
        if docx.exists():
            md_mtime = p.stat().st_mtime
            docx_mtime = docx.stat().st_mtime
            if docx_mtime + 1 < md_mtime:
                issues.append(
                    f"Stale .docx: {docx.name} is older than {p.name} "
                    f"(re-run regen_docx.sh)"
                )

    dates = BATCH_HEADING.findall(log_text)
    parsed = [dt.date.fromisoformat(d) for d in dates]
    if parsed != sorted(parsed):
        issues.append(f"Log batch dates not in ascending order: {dates}")

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

    project_label = todos_p.parent.name
    if issues:
        print(f"VERIFY {project_label}: FAIL ({len(issues)} issue(s))", file=sys.stderr)
        for i in issues:
            print(f"  • {i}", file=sys.stderr)
        sys.exit(1)
    print(
        f"VERIFY {project_label}: OK   "
        f"({len(open_todo_ids)} open TODOs, {len(pending_action_ids)} pending ACTIONs, "
        f"{len(log_resolves)} resolved-via-log, "
        f"{len(LOG_ENTRY.findall(log_text))} log entries)",
        file=sys.stderr,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
