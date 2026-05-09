"""
Execute approved ACTION blocks from <USER>_actions.md against the target files
(where <USER> = $USER_NAME or "user").

Atomically: parse → find/replace → verify → log → remove from queue.
Refuses to log if the find-text isn't unique or the verification fails, so the
log never claims a change that didn't happen.

Usage:
    python3 execute_action.py --dir Projects/<proj>-revisions --action-id 1
    python3 execute_action.py --dir Projects/<proj>-revisions --all
    python3 execute_action.py --dir Projects/<proj>-revisions --all --regen-docx

Options:
    --dir         Project directory containing the three files.
    --action-id N One ACTION to execute (matched by number in heading).
    --all         Execute every ACTION block in order.
    --regen-docx  After successful execution, run regen_docx.sh.
    --dry-run     Parse + report; do not modify any file.
    --no-todo-cleanup  Skip the "remove resolved TODO" step.
"""
import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

USER = os.environ.get("USER_NAME", "user")
ACTIONS_FILE = f"{USER}_actions.md"
TODOS_FILE = f"{USER}_todos.md"
LOG_FILE = "completed_actions_log.md"

ACTION_HEADING = re.compile(r"^## ACTION (\d+)\b.*$", re.MULTILINE)
RESOLVES_TAG = re.compile(r"resolves\s+(TODO\s+\d+(?:\([a-z]\))?|Shige\s+#\d+(?:[–-]\d+)?)", re.IGNORECASE)
TODO_HEADING = re.compile(r"^## TODO (\d+(?:\([a-z]\))?)\b.*$", re.MULTILINE)


def read(p):
    return Path(p).read_text()


def write(p, s):
    Path(p).write_text(s)


def fenced_block_after(text, marker):
    """Find ``` ... ``` block that appears after `marker` substring."""
    idx = text.find(marker)
    if idx == -1:
        return None
    rest = text[idx + len(marker):]
    m = re.search(r"```[a-zA-Z0-9]*\n(.*?)```", rest, re.DOTALL)
    if not m:
        return None
    return m.group(1).rstrip("\n")


def extract_actions(actions_text):
    """Yield (action_id, block_text, start_idx, end_idx) for each ACTION block."""
    matches = list(ACTION_HEADING.finditer(actions_text))
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(actions_text)
        # If trailing "## After all actions complete" or "## What's NOT" is in the block, trim it.
        rest = actions_text[start:end]
        cut = re.search(r"\n## (?!ACTION )", rest)
        if cut:
            end = start + cut.start()
        yield int(m.group(1)), actions_text[start:end].rstrip() + "\n", start, end


def parse_block(block):
    """Return dict with file, find_text, replace_text, verify_cmd, recompile, resolves."""
    out = {}
    # Heading line
    head = block.splitlines()[0]
    out["heading"] = head.strip()
    # File
    fm = re.search(r"\*\*File:\*\*\s+`?([^`\n]+?)`?\s*$", block, re.MULTILINE)
    out["file"] = fm.group(1).strip() if fm else None
    # Find / Replace
    out["find_text"] = fenced_block_after(block, "Find this exact passage")
    out["replace_text"] = fenced_block_after(block, "Replace with:")
    # Verification
    out["verify_cmd"] = fenced_block_after(block, "Verification after edit")
    # Recompile
    rm = re.search(r"\*\*Recompile:\*\*\s+(Yes|No)\b", block, re.IGNORECASE)
    out["recompile"] = rm.group(1).capitalize() if rm else None
    # Resolves
    res = RESOLVES_TAG.search(head)
    out["resolves"] = res.group(1) if res else None
    return out


def remove_action_block(actions_text, start, end):
    """Remove [start:end] plus the trailing '---' separator if present."""
    new = actions_text[:start] + actions_text[end:]
    # Tidy 3+ blank lines / orphan ---
    new = re.sub(r"\n{4,}", "\n\n\n", new)
    new = re.sub(r"\n---\n+\n## ", "\n## ", new)
    return new


def remove_todo(todos_text, todo_id):
    """Delete `## TODO <todo_id>` block (header → next section/horizontal-rule)."""
    pattern = re.compile(
        rf"\n*## TODO {re.escape(todo_id)}\b.*?(?=\n## |\n# |\Z)",
        re.DOTALL,
    )
    new = pattern.sub("\n", todos_text, count=1)
    new = re.sub(r"\n{4,}", "\n\n\n", new)
    return new


def log_entry(action, before, after, today):
    why_bits = []
    if action["resolves"]:
        why_bits.append(f"originating: {action['resolves']}")
    why = "; ".join(why_bits) or "(see source TODO discussion)"
    return (
        f"### Entry — [TYPE: ACTION] {action['heading'][3:].strip()}\n"
        f"- **File:** `{action['file']}`\n"
        f"- **Before:**\n  ```\n{before}\n  ```\n"
        f"- **After:**\n  ```\n{after}\n  ```\n"
        f"- **Why:** {why}\n"
        f"- **Verified:** `{action['verify_cmd']}`\n"
        f"- **Executed:** {today.isoformat()}\n"
        f"- **Recompile:** {action['recompile']}\n\n"
    )


def append_to_log(log_text, entry, today, batch_label):
    """Append entry under today's batch heading; create the batch if absent."""
    today_str = today.strftime("%Y-%m-%d")
    batch_pat = re.compile(
        rf"^## Batch {today_str}\b[^\n]*$", re.MULTILINE
    )
    sentinel = "*(Append future batches below this line."
    if batch_pat.search(log_text):
        # Append entry just before the next "## Batch" or before sentinel
        m = batch_pat.search(log_text)
        next_batch = re.search(r"^## Batch ", log_text[m.end():], re.MULTILINE)
        if next_batch:
            insert_at = m.end() + next_batch.start()
        elif sentinel in log_text:
            insert_at = log_text.find(sentinel)
        else:
            insert_at = len(log_text)
        return log_text[:insert_at].rstrip() + "\n\n" + entry + log_text[insert_at:]
    # Create a new batch block
    new_batch = (
        f"## Batch {today_str} — {batch_label}\n\n"
        f"### Source\n`{ACTIONS_FILE}` ACTIONs executed by `execute_action.py`.\n\n"
        f"---\n\n{entry}"
    )
    if sentinel in log_text:
        idx = log_text.find(sentinel)
        return log_text[:idx].rstrip() + "\n\n" + new_batch + "\n" + log_text[idx:]
    return log_text.rstrip() + "\n\n" + new_batch


def run_verify(cmd, cwd):
    """Run a shell verification snippet; return (ok, output)."""
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=60)
        return r.returncode == 0, r.stdout + r.stderr
    except Exception as e:
        return False, str(e)


def execute_one(action_block, action, project_dir, dry_run, do_todo_cleanup):
    """Apply one ACTION. Returns (ok, message, todo_id_to_remove)."""
    if not action["file"] or not action["find_text"] or not action["replace_text"]:
        return False, "ACTION missing file / find_text / replace_text", None
    # Resolve target file path. Use project root as cwd: assume project_dir is
    # nested under the repo root; walk up until we find apa-workflow/ or .git/.
    cwd = find_repo_root(project_dir)
    target = cwd / action["file"]
    if not target.exists():
        return False, f"Target file not found: {target}", None
    src = target.read_text()
    if src.count(action["find_text"]) == 0:
        return False, f"find_text not present in {target}", None
    if src.count(action["find_text"]) > 1:
        return False, f"find_text not unique in {target} (appears {src.count(action['find_text'])}×)", None
    if dry_run:
        return True, f"DRY-RUN: would edit {target}", None
    new = src.replace(action["find_text"], action["replace_text"], 1)
    target.write_text(new)
    # Verify
    if action["verify_cmd"]:
        ok, out = run_verify(action["verify_cmd"], cwd)
        if not ok:
            # Roll back
            target.write_text(src)
            return False, f"Verification failed: {out[:400]}", None
    # Find originating TODO ID for cleanup
    todo_id = None
    if do_todo_cleanup and action["resolves"]:
        m = re.match(r"TODO\s+(\d+(?:\([a-z]\))?)", action["resolves"], re.IGNORECASE)
        if m:
            todo_id = m.group(1)
    return True, "applied + verified", todo_id


def find_repo_root(start):
    """Walk up from start looking for a directory with apa-workflow/ or .git.

    Falls back to start itself (the project dir) if no marker is found.
    """
    p = Path(start).resolve()
    for candidate in [p] + list(p.parents):
        if (candidate / ".git").exists() or (candidate / "apa-workflow").exists():
            return candidate
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="Project revisions directory")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--action-id", type=int)
    g.add_argument("--all", action="store_true")
    ap.add_argument("--regen-docx", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-todo-cleanup", action="store_true")
    ap.add_argument("--batch-label", default="Auto batch from execute_action.py")
    args = ap.parse_args()

    proj = Path(args.dir).resolve()
    actions_path = proj / ACTIONS_FILE
    todos_path = proj / TODOS_FILE
    log_path = proj / LOG_FILE
    for p in (actions_path, todos_path, log_path):
        if not p.exists():
            print(f"Missing required file: {p}", file=sys.stderr)
            sys.exit(2)

    actions_text = read(actions_path)
    blocks = list(extract_actions(actions_text))
    if not blocks:
        print(f"No ACTION blocks pending in {ACTIONS_FILE}.", file=sys.stderr)
        sys.exit(0)

    if args.action_id is not None:
        blocks = [b for b in blocks if b[0] == args.action_id]
        if not blocks:
            print(f"ACTION {args.action_id} not found.", file=sys.stderr)
            sys.exit(2)

    today = dt.date.today()
    successes = []
    failures = []

    for action_id, block_text, start, end in blocks:
        action = parse_block(block_text)
        # NOTE: after each successful execution we re-read actions_text since
        # offsets shift; we work newest-to-oldest to keep this simple.

    # Process from bottom to top so removal offsets stay valid.
    for action_id, block_text, start, end in reversed(blocks):
        action = parse_block(block_text)
        before = action.get("find_text", "")
        after = action.get("replace_text", "")
        ok, msg, todo_id = execute_one(block_text, action, proj, args.dry_run, not args.no_todo_cleanup)
        print(f"ACTION {action_id}: {'OK' if ok else 'FAIL'} — {msg}", file=sys.stderr)
        if not ok:
            failures.append((action_id, msg))
            continue

        if not args.dry_run:
            # 1. Append log entry
            log_text = read(log_path)
            entry = log_entry(action, before, after, today)
            new_log = append_to_log(log_text, entry, today, args.batch_label)
            write(log_path, new_log)
            # 2. Remove ACTION block from actions file
            actions_text = read(actions_path)
            # Re-find the same block by heading line (offsets shifted)
            head_line = block_text.splitlines()[0]
            head_idx = actions_text.find(head_line)
            if head_idx >= 0:
                # find next "## " after head_idx that isn't an ACTION continuation
                tail = actions_text[head_idx + len(head_line):]
                cut = re.search(r"\n## (?!ACTION )", tail)
                if cut:
                    block_end = head_idx + len(head_line) + cut.start()
                else:
                    next_action = re.search(r"\n## ACTION ", tail)
                    block_end = (head_idx + len(head_line) + next_action.start()) if next_action else len(actions_text)
                new_actions = remove_action_block(actions_text, head_idx, block_end)
                write(actions_path, new_actions)
            # 3. Remove originating TODO from todos file (if any)
            if todo_id:
                todos_text = read(todos_path)
                new_todos = remove_todo(todos_text, todo_id)
                write(todos_path, new_todos)
        successes.append(action_id)

    # Optional docx regen
    if args.regen_docx and successes and not args.dry_run:
        regen = Path(__file__).parent / "regen_docx.sh"
        subprocess.run(["bash", str(regen), str(proj)], check=False)

    print(f"\nDone. Succeeded: {successes}. Failed: {[f[0] for f in failures]}.", file=sys.stderr)
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()
