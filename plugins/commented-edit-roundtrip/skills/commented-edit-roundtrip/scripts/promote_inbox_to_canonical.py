"""
Promote the current inbox markdown to canonical: the inbox prose becomes
the new safe baseline. The inbox itself (filename, comments) is unchanged.

This is the OTHER half of the inverted role model:
  - apply_edit_to_inbox.py = edits land on the inbox (canonical untouched)
  - promote_inbox_to_canonical.py = at user sign-off, inbox prose is
    written to canonical, canonical .docx is regenerated, prior canonical
    is snapshotted for reversion.

Algorithm:
  1. Snapshot current canonical .md and .docx to snapshot dir.
  2. Copy inbox.md → canonical.md (verbatim).
  3. Regenerate canonical.docx via pandoc.
  4. Print a unified diff (canonical pre vs. post) for the user to review.

Usage:
  python3 promote_inbox_to_canonical.py \\
      --inbox-md     "revisions/[inbox] manuscript.md" \\
      --canonical-md "<MANUSCRIPT_DIR>/manuscript.md" \\
      --canonical-docx "<MANUSCRIPT_DIR>/manuscript.docx" \\
      --snapshot-dir "manuscript_comment_rounds (claude)/canonical_snapshots"
"""
import argparse, datetime, difflib, shutil, subprocess, sys
from pathlib import Path


def snapshot(file_path: Path, snapshot_dir: Path) -> Path:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    dest = snapshot_dir / f'{file_path.stem}_pre-promotion_{ts}{file_path.suffix}'
    shutil.copy2(file_path, dest)
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--inbox-md', required=True)
    ap.add_argument('--canonical-md', required=True)
    ap.add_argument('--canonical-docx', required=True)
    ap.add_argument('--snapshot-dir', required=True)
    ap.add_argument('--diff-out', default=None,
                    help='Optional path to write the diff to (else just printed)')
    args = ap.parse_args()

    inbox_md = Path(args.inbox_md).expanduser().resolve()
    canonical_md = Path(args.canonical_md).expanduser().resolve()
    canonical_docx = Path(args.canonical_docx).expanduser().resolve()
    snapshot_dir = Path(args.snapshot_dir).expanduser().resolve()

    if not inbox_md.exists():
        sys.exit(f'ERROR: inbox markdown not found: {inbox_md}')
    if not canonical_md.exists():
        sys.exit(f'ERROR: canonical markdown not found: {canonical_md}')

    md_snap = snapshot(canonical_md, snapshot_dir)
    print(f'Pre-promotion canonical .md snapshotted → {md_snap}')
    if canonical_docx.exists():
        docx_snap = snapshot(canonical_docx, snapshot_dir)
        print(f'Pre-promotion canonical .docx snapshotted → {docx_snap}')

    pre_lines = canonical_md.read_text().splitlines(keepends=True)

    shutil.copy2(inbox_md, canonical_md)
    print(f'Canonical .md replaced with inbox prose.')

    try:
        subprocess.run(['pandoc', str(canonical_md), '-o', str(canonical_docx)],
                       check=True)
        print(f'Canonical .docx regenerated via pandoc.')
    except subprocess.CalledProcessError as e:
        sys.exit(f'ERROR: pandoc failed: {e}')

    post_lines = canonical_md.read_text().splitlines(keepends=True)
    diff = list(difflib.unified_diff(
        pre_lines, post_lines,
        fromfile=f'canonical (pre-promotion: {md_snap.name})',
        tofile=f'canonical (post-promotion: from {inbox_md.name})',
    ))

    if args.diff_out:
        Path(args.diff_out).write_text(''.join(diff))
        print(f'Diff written → {args.diff_out}')
    else:
        if diff:
            print('\n--- Diff (canonical pre vs. post) ---\n')
            sys.stdout.writelines(diff)
        else:
            print('No textual changes (inbox.md identical to prior canonical.md).')


if __name__ == '__main__':
    main()
