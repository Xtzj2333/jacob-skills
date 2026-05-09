"""
Close a TODO without a code edit (compliment, prior fix, inaction, declined).

Atomically: append a [TYPE: TODO] entry to completed_actions_log.md AND remove
the TODO section from <USER>_todos.md (where <USER> = $USER_NAME or "user").

Usage:
    python3 close_todo.py --dir DIR --todo-id 11 \
        --resolution no-action \
        --reason "Misread of source — was a reply, not a delete request"

Resolution must be one of:
    no-action         resolved without doing anything (Shige reply, etc.)
    compliment        positive feedback, not a request
    prior-fix         already addressed before this session
    declined          user explicitly declined the suggestion
    deferred-cancelled originally deferred, now cancelled (won't re-open)
"""
import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path

USER = os.environ.get("USER_NAME", "user")
TODOS_FILE = f"{USER}_todos.md"
LOG_FILE = "completed_actions_log.md"

VALID_RESOLUTIONS = {"no-action", "compliment", "prior-fix", "declined", "deferred-cancelled"}


def read(p):
    return Path(p).read_text()


def write(p, s):
    Path(p).write_text(s)


def find_todo(todos_text, todo_id):
    """Return (heading, body, start, end) for the matching TODO section."""
    pattern = re.compile(
        rf"(^## TODO {re.escape(todo_id)}\b[^\n]*\n)(.*?)(?=\n## |\n# |\Z)",
        re.DOTALL | re.MULTILINE,
    )
    m = pattern.search(todos_text)
    if not m:
        return None
    return m.group(1).strip(), m.group(2).strip(), m.start(), m.end()


def remove_todo(todos_text, start, end):
    new = todos_text[:start] + todos_text[end:]
    new = re.sub(r"\n{4,}", "\n\n\n", new)
    return new


def append_to_log(log_text, entry, today, batch_label):
    today_str = today.strftime("%Y-%m-%d")
    sentinel = "*(Append future batches below this line."
    batch_pat = re.compile(rf"^## Batch {today_str}\b[^\n]*$", re.MULTILINE)
    if batch_pat.search(log_text):
        m = batch_pat.search(log_text)
        next_batch = re.search(r"^## Batch ", log_text[m.end():], re.MULTILINE)
        if next_batch:
            insert_at = m.end() + next_batch.start()
        elif sentinel in log_text:
            insert_at = log_text.find(sentinel)
        else:
            insert_at = len(log_text)
        return log_text[:insert_at].rstrip() + "\n\n" + entry + log_text[insert_at:]
    new_batch = (
        f"## Batch {today_str} — {batch_label}\n\n"
        f"### Source\n`{TODOS_FILE}` TODO closures (no code edits).\n\n"
        f"---\n\n{entry}"
    )
    if sentinel in log_text:
        idx = log_text.find(sentinel)
        return log_text[:idx].rstrip() + "\n\n" + new_batch + "\n" + log_text[idx:]
    return log_text.rstrip() + "\n\n" + new_batch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--todo-id", required=True, help="e.g. 11 or 2(a)")
    ap.add_argument("--resolution", required=True, choices=sorted(VALID_RESOLUTIONS))
    ap.add_argument("--reason", required=True)
    ap.add_argument("--batch-label", default="TODO closures")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    proj = Path(args.dir).resolve()
    todos_path = proj / TODOS_FILE
    log_path = proj / LOG_FILE
    for p in (todos_path, log_path):
        if not p.exists():
            print(f"Missing required file: {p}", file=sys.stderr)
            sys.exit(2)

    todos_text = read(todos_path)
    found = find_todo(todos_text, args.todo_id)
    if not found:
        print(f"TODO {args.todo_id} not found in {todos_path}", file=sys.stderr)
        sys.exit(2)
    heading, body, start, end = found
    title = heading.replace(f"## TODO {args.todo_id}", "").lstrip(" ——–-")

    today = dt.date.today()
    entry = (
        f"### Entry — [TYPE: TODO] TODO {args.todo_id}: {title}\n"
        f"- **Resolution:** {args.resolution}\n"
        f"- **Why:** {args.reason}\n"
        f"- **Closed:** {today.isoformat()}\n\n"
    )

    if args.dry_run:
        print("DRY-RUN — would append this entry:\n", entry, file=sys.stderr)
        print("DRY-RUN — would remove this TODO heading:\n", heading, file=sys.stderr)
        return

    new_log = append_to_log(read(log_path), entry, today, args.batch_label)
    write(log_path, new_log)
    new_todos = remove_todo(todos_text, start, end)
    write(todos_path, new_todos)
    print(f"Closed TODO {args.todo_id} — appended to log, removed from todos.", file=sys.stderr)


if __name__ == "__main__":
    main()
