"""
Scan an inbox .docx for margin comments whose anchor text overlaps a target
text passage (the to-be-edited prose). Used by apply_edit_to_inbox.py to
decide which comments must be archived before an overwriting edit.

Overlap heuristics, in order:
  1. anchor_text is a substring of target_text  → "fully-overlapped"
  2. target_text is a substring of anchor_text  → "edit-within-anchor"
  3. anchor and target share a contiguous substring of >= N chars
     (default N=20)                              → "partial-overlap"
  4. otherwise: no overlap

Usage:
  python3 scan_overlapping_comments.py \\
      --inbox "revisions/[inbox] manuscript.docx" \\
      --target-text "the prose about to be replaced" \\
      [--min-substring 20] \\
      --out /tmp/overlapping.json

Output: a JSON list, one entry per overlapping comment, with:
  {id, author, date, text, anchor, overlap_kind, shared_substring}
"""
import argparse, json, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from refresh_inbox import read_comments_raw  # noqa: E402


def longest_common_substring(a: str, b: str) -> str:
    """Return the longest contiguous substring shared by a and b."""
    if not a or not b:
        return ''
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    best = 0
    end = 0
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
                if dp[i][j] > best:
                    best = dp[i][j]
                    end = i
    return a[end - best:end]


def classify_overlap(anchor: str, target: str, min_substring: int):
    if not anchor or not target:
        return None, ''
    a = anchor.strip()
    t = target.strip()
    if a in t:
        return 'fully-overlapped', a
    if t in a:
        return 'edit-within-anchor', t
    lcs = longest_common_substring(a, t)
    if len(lcs.strip()) >= min_substring:
        return 'partial-overlap', lcs.strip()
    return None, ''


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--inbox', required=True, help='Path to the inbox .docx')
    ap.add_argument('--target-text', required=True,
                    help='The prose passage about to be edited')
    ap.add_argument('--min-substring', type=int, default=20,
                    help='Minimum shared substring length (chars) for partial overlap')
    ap.add_argument('--out', required=True, help='JSON output path')
    args = ap.parse_args()

    inbox = Path(args.inbox).expanduser().resolve()
    if not inbox.exists():
        sys.exit(f'ERROR: inbox not found: {inbox}')

    comments = read_comments_raw(inbox)
    overlapping = []
    for c in comments:
        if c.get('received'):
            continue
        kind, shared = classify_overlap(c.get('anchor', ''), args.target_text,
                                        args.min_substring)
        if kind:
            overlapping.append({
                'id': c['id'],
                'author': c.get('author', ''),
                'date': c.get('date', ''),
                'text': c.get('text', ''),
                'anchor': c.get('anchor', ''),
                'overlap_kind': kind,
                'shared_substring': shared,
            })

    Path(args.out).write_text(json.dumps(overlapping, indent=2))
    print(f'Scanned {len(comments)} comments; '
          f'{len(overlapping)} overlap target text.')
    for c in overlapping:
        print(f"  - #{c['id']} ({c['overlap_kind']}): "
              f"{c['anchor'][:60]}{'...' if len(c['anchor']) > 60 else ''}")


if __name__ == '__main__':
    main()
