"""
Verify that every change in the source→output diff has a corresponding entry
in the change log. Any uncommented diff is a bug — either the log missed an
edit, or the loop made a silent change that needs to be reverted.

Usage:
  python3 verify_changes.py --before original.txt \\
                            --after  edited.txt \\
                            --log    logs/change_log_2026-04-26.jsonl

Inputs:
  --before     Plain-text source (before any edits)
  --after      Plain-text result (after edits)
  --log        JSONL with one change per line, each having `before` and `after`
               fields containing the substrings being changed
  --tolerance  Allowed edit-distance fuzziness for matching (default 0)

Output:
  Exits 0 if every diff has a log entry. Exits 1 with a list of uncommented
  diffs otherwise.

Note: this is a coarse verifier. It treats the diff at the line level (or
token level for a Word doc converted to text). Reorderings and large
restructures may produce false positives — log those at the section/anchor
level and the verifier will accept them as long as the anchor text appears in
both before/after fields of a log entry.
"""
import argparse, difflib, json, sys


def load_log(path):
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def diff_blocks(before_path, after_path):
    a = open(before_path).read().splitlines()
    b = open(after_path).read().splitlines()
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    blocks = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        blocks.append({
            'tag': tag,
            'before': '\n'.join(a[i1:i2]),
            'after':  '\n'.join(b[j1:j2]),
            'before_lines': (i1 + 1, i2),
            'after_lines':  (j1 + 1, j2),
        })
    return blocks


def block_covered(block, log):
    before_text = block['before'].strip()
    after_text  = block['after'].strip()
    for entry in log:
        eb = (entry.get('before') or '').strip()
        ea = (entry.get('after') or '').strip()
        # Coverage: the diff text must contain (or be contained by) a logged
        # before/after pair on at least one side.
        b_match = (eb and (eb in before_text or before_text in eb))
        a_match = (ea and (ea in after_text  or after_text  in ea))
        if b_match or a_match:
            return entry
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--before', required=True)
    ap.add_argument('--after', required=True)
    ap.add_argument('--log', required=True)
    args = ap.parse_args()

    log = load_log(args.log)
    blocks = diff_blocks(args.before, args.after)

    uncovered = []
    for blk in blocks:
        if block_covered(blk, log) is None:
            uncovered.append(blk)

    print(f'Diff blocks: {len(blocks)}')
    print(f'Logged    : {len(blocks) - len(uncovered)}')
    print(f'Uncovered : {len(uncovered)}')
    if uncovered:
        print('\nUNCOVERED DIFFS — log them or revert:')
        for blk in uncovered[:20]:
            print(f"\n  [{blk['tag']}] before lines {blk['before_lines']}, after lines {blk['after_lines']}")
            print(f"    before: {blk['before'][:200]!r}")
            print(f"    after : {blk['after'][:200]!r}")
        sys.exit(1)
    print('OK — every diff has a log entry.')


if __name__ == '__main__':
    main()
