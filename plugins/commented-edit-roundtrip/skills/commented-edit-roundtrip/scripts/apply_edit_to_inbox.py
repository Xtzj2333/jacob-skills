"""
Apply a text edit to the inbox's working markdown source, archive any
margin comments whose anchor text would be overwritten, then regenerate
the inbox .docx so user can keep commenting on the new prose.

This is the primary edit operation in the inverted role model:
  - inbox.md   = Claude's editing surface (working markdown).
  - inbox.docx = User's commenting surface (rendered + comments).
  - canonical  = safe baseline; untouched until promotion.

Algorithm:
  1. Lockfile guard on inbox.docx.
  2. Read all comments from inbox.docx; classify which overlap target text.
  3. Archive overlapping comments under <archive-dir>/ as per-comment .md
     files + an INDEX.md row.
  4. Apply find/replace on inbox.md (target → replacement).
  5. Snapshot the pre-edit inbox.docx for safety.
  6. Render the new inbox.md to a temp .docx via pandoc.
  7. Re-inject all NON-archived comments by anchor matching against the
     new docx prose. Anchors that no longer match → lost-anchors sidecar.
  8. Replace inbox.docx with the regenerated version.

Usage:
  python3 apply_edit_to_inbox.py \\
      --inbox-md   "revisions/[inbox] manuscript.md" \\
      --inbox-docx "revisions/[inbox] manuscript.docx" \\
      --target     "old prose to replace" \\
      --replacement "new prose" \\
      --archive-dir "revisions/comment_archive" \\
      --snapshot-dir "manuscript_comment_rounds (claude)" \\
      --log-entry-id "ACTION-2026-04-30-007"
"""
import argparse, datetime, json, shutil, subprocess, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from refresh_inbox import (  # noqa: E402
    check_lockfile, read_comments_raw, snapshot,
    inject_into_docx, write_lost_anchors_sidecar,
)
from scan_overlapping_comments import classify_overlap  # noqa: E402


def safe_id(comment_id: str) -> str:
    """Normalize a comment ID for use as a filename component."""
    return ''.join(ch if ch.isalnum() else '-' for ch in str(comment_id)).strip('-') or 'unknown'


def find_paragraph_around(md_text: str, target: str, lines_around: int = 3) -> str:
    """Return surrounding context (lines_around lines before/after) of the
    first occurrence of target in md_text. Returns target itself if not found."""
    idx = md_text.find(target)
    if idx < 0:
        return target
    line_start = md_text.rfind('\n', 0, idx) + 1
    line_end = md_text.find('\n', idx + len(target))
    if line_end < 0:
        line_end = len(md_text)
    pre = md_text[:line_start].splitlines()
    post = md_text[line_end:].splitlines()
    pre_ctx = pre[-lines_around:] if pre else []
    post_ctx = post[1:1 + lines_around] if len(post) > 1 else []
    middle = md_text[line_start:line_end]
    return '\n'.join(pre_ctx + [middle] + post_ctx)


def write_archive_entry(archive_dir: Path, archive_id: str, comment: dict,
                        overlap_kind: str, shared: str,
                        target: str, replacement: str,
                        inbox_md: Path, surrounding: str,
                        log_entry_id: str) -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{archive_id}_comment-{safe_id(comment['id'])}.md"
    path = archive_dir / fname
    body = [
        f"# Archived comment #{comment['id']} — {archive_id}",
        '',
        f"- **Author:** {comment.get('author', '?')}",
        f"- **Date:** {comment.get('date', '?')}",
        f"- **Overlap kind:** {overlap_kind}",
        f"- **Shared substring:** `{shared[:200]}`",
        f"- **Resolving log entry:** {log_entry_id}",
        '',
        '## Comment body (verbatim)',
        '',
        '```',
        comment.get('text', ''),
        '```',
        '',
        '## Original anchor text (verbatim)',
        '',
        '```',
        comment.get('anchor', ''),
        '```',
        '',
        '## Surrounding paragraph at edit time',
        '',
        '```',
        surrounding,
        '```',
        '',
        '## Displacing edit',
        '',
        f"- **File:** {inbox_md}",
        '- **Before:**',
        '',
        '```',
        target,
        '```',
        '',
        '- **After:**',
        '',
        '```',
        replacement,
        '```',
        '',
    ]
    path.write_text('\n'.join(body))
    return path


def append_index_row(index_path: Path, archive_id: str, comment: dict,
                     overlap_kind: str, target: str, log_entry_id: str,
                     archive_file: Path):
    is_new = not index_path.exists()
    with index_path.open('a') as f:
        if is_new:
            f.write('# Comment archive — INDEX\n\n')
            f.write('Append-only ledger of inbox comments displaced by edits. '
                    'Each row points to a per-comment archive file with full context.\n\n')
            f.write('| Archive ID | Date | Comment ID | Author | Overlap kind | Anchor (truncated) | Edit target (truncated) | Resolving log entry | Archive file |\n')
            f.write('|---|---|---|---|---|---|---|---|---|\n')
        anchor = (comment.get('anchor') or '').replace('|', '\\|')[:60]
        target_trunc = target.replace('|', '\\|')[:60]
        f.write(f"| {archive_id} | {datetime.date.today().isoformat()} | "
                f"#{comment['id']} | {comment.get('author', '?')} | "
                f"{overlap_kind} | `{anchor}{'...' if len(comment.get('anchor', '')) > 60 else ''}` | "
                f"`{target_trunc}{'...' if len(target) > 60 else ''}` | "
                f"{log_entry_id} | [{archive_file.name}](./{archive_file.name}) |\n")


def render_md_to_docx(md_path: Path, out_docx: Path):
    """Render markdown to docx via pandoc."""
    subprocess.run(['pandoc', str(md_path), '-o', str(out_docx)], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--inbox-md', required=True,
                    help='Path to inbox working markdown (Claude edits this)')
    ap.add_argument('--inbox-docx', required=True,
                    help='Path to inbox docx (user comments here)')
    ap.add_argument('--target', required=True,
                    help='Verbatim prose to replace in inbox-md')
    ap.add_argument('--replacement', required=True,
                    help='Replacement prose')
    ap.add_argument('--archive-dir', required=True,
                    help='Directory for archived comments (per-comment .md + INDEX.md)')
    ap.add_argument('--snapshot-dir', required=True,
                    help='Directory for pre-edit inbox.docx snapshots')
    ap.add_argument('--log-entry-id', default='(unset)',
                    help='Identifier of the resolving log entry')
    ap.add_argument('--min-substring', type=int, default=20)
    ap.add_argument('--dry-run', action='store_true',
                    help='Report overlapping comments but do not modify any file')
    args = ap.parse_args()

    inbox_md = Path(args.inbox_md).expanduser().resolve()
    inbox_docx = Path(args.inbox_docx).expanduser().resolve()
    archive_dir = Path(args.archive_dir).expanduser().resolve()
    snapshot_dir = Path(args.snapshot_dir).expanduser().resolve()

    if not inbox_md.exists():
        sys.exit(f'ERROR: inbox markdown not found: {inbox_md}')
    if not inbox_docx.exists():
        sys.exit(f'ERROR: inbox docx not found: {inbox_docx}')

    check_lockfile(inbox_docx)

    md_text = inbox_md.read_text()
    if args.target not in md_text:
        sys.exit(f'ERROR: target text not found in {inbox_md.name}.\n'
                 f'First 200 chars of target: {args.target[:200]!r}')
    occurrences = md_text.count(args.target)
    if occurrences > 1:
        sys.exit(f'ERROR: target text occurs {occurrences} times in {inbox_md.name}; '
                 'must be unique for safe replacement.')

    comments = read_comments_raw(inbox_docx)
    overlapping = []
    for c in comments:
        if c.get('received'):
            continue
        kind, shared = classify_overlap(c.get('anchor', ''), args.target,
                                        args.min_substring)
        if kind:
            overlapping.append((c, kind, shared))

    print(f'Comments scanned: {len(comments)} '
          f'({sum(1 for c in comments if not c.get("received"))} live).')
    print(f'Overlapping with target: {len(overlapping)}.')
    for c, kind, _shared in overlapping:
        print(f"  - #{c['id']} ({kind}): "
              f"{c.get('anchor', '')[:80]}{'...' if len(c.get('anchor', '')) > 80 else ''}")

    if args.dry_run:
        print('\n[dry-run] No files modified.')
        return

    archive_entries = []
    if overlapping:
        ts = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
        for i, (c, kind, shared) in enumerate(overlapping, start=1):
            archive_id = f"{ts}_{i:03d}"
            surrounding = find_paragraph_around(md_text, args.target)
            archive_file = write_archive_entry(
                archive_dir, archive_id, c, kind, shared,
                args.target, args.replacement, inbox_md, surrounding,
                args.log_entry_id,
            )
            append_index_row(archive_dir / 'INDEX.md', archive_id, c, kind,
                             args.target, args.log_entry_id, archive_file)
            archive_entries.append((c['id'], archive_id, archive_file))
            print(f'  archived #{c["id"]} → {archive_file.name}')

    new_md_text = md_text.replace(args.target, args.replacement, 1)
    inbox_md.write_text(new_md_text)
    print(f'inbox.md edited: 1 occurrence replaced.')

    snap = snapshot(inbox_docx, snapshot_dir)
    print(f'inbox.docx snapshot → {snap}')

    archived_ids = {cid for cid, _aid, _f in archive_entries}
    live_to_carry = [c for c in comments
                     if not c.get('received') and c['id'] not in archived_ids]

    tmp_docx = inbox_docx.with_suffix('.docx.regen')
    render_md_to_docx(inbox_md, tmp_docx)
    shutil.move(str(tmp_docx), str(inbox_docx))
    print(f'inbox.docx regenerated from inbox.md.')

    inserted, skipped = inject_into_docx(inbox_docx, live_to_carry)
    print(f'Carried forward {len(inserted)} comments by anchor match.')
    if skipped:
        sidecar = write_lost_anchors_sidecar(inbox_docx, skipped)
        print(f'Lost-anchor sidecar → {sidecar} ({len(skipped)} comments)')

    summary = {
        'log_entry_id': args.log_entry_id,
        'inbox_md': str(inbox_md),
        'inbox_docx': str(inbox_docx),
        'target': args.target,
        'replacement': args.replacement,
        'archived_count': len(archive_entries),
        'archived_comment_ids': [cid for cid, _, _ in archive_entries],
        'carried_forward_count': len(inserted),
        'lost_anchors_count': len(skipped),
        'snapshot': str(snap),
    }
    print('\n' + json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
