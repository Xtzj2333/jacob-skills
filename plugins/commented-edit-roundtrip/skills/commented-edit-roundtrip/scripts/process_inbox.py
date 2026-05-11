"""
Process a perpetual commenting inbox (a .docx the user keeps adding margin
comments to) WITHOUT renaming or replacing the file.

Two phases, both done in-place on the inbox .docx:
  1. EXTRACT — read all comments matching the filter (--author / --since /
     --not-received) and emit JSON. Caller hands this JSON to whatever picks
     up new TODOs (typically revision-queue's todos file, resolved via the
     `project-filename` skill as `todos [<shorthand>].md`).
  2. MARK   — modify each processed comment's body in word/comments.xml so
     it's prefixed with "[RECEIVED YYYY-MM-DD] " and reauthored to "Claude
     (received)". This makes received items visually distinct in Word so the
     user can see what Claude has picked up, without losing the original
     conversation thread.

The inbox .docx keeps its name and path. The user can keep commenting in
Word the whole time (after closing the file briefly while this runs — the
script refuses to write if Word has an open lock on the file).

Inbox naming convention: a copy of the manuscript with "[inbox] " prefixed
to the filename, kept in a project-side revisions folder. The script can
auto-create the inbox on first call: pass --from-manuscript and the inbox
path; if no inbox exists yet, the manuscript is copied to that path.

A snapshot of the pre-process inbox is copied to an archive folder for safety.

Usage:
  python3 process_inbox.py INBOX.docx \\
      --extract-out new_comments.json \\
      --archive-dir "manuscript_comment_rounds (claude)" \\
      [--author "<USER>"] [--since 2026-04-30] \\
      [--mark-only] [--no-mark]

Auto-create form (when the inbox doesn't yet exist):
  python3 process_inbox.py "revisions/[inbox] manuscript.docx" \\
      --from-manuscript path/to/manuscript.docx \\
      --extract-out new_comments.json \\
      --archive-dir "manuscript_comment_rounds (claude)"

Flags:
  --extract-out PATH      Write extracted comments here. Required unless --no-extract.
  --archive-dir DIR       Snapshot the pre-process inbox to DIR/snapshot_<ts>.docx.
                          Required unless --no-archive.
  --from-manuscript PATH  If the inbox doesn't exist, copy this manuscript to it first.
  --author NAME           Only process comments by this author (default: all).
  --since YYYY-MM-DD      Only process comments dated >= this.
  --not-received          Skip comments already prefixed with "[RECEIVED" (or legacy
                          "[DRAINED"). Recommended in normal use.
  --mark-only             Skip extraction; only mark matching comments. Useful for
                          migration of pre-existing commented files whose comments
                          are already filed elsewhere.
  --no-mark               Skip the in-place marking; only extract.
  --no-archive            Skip the snapshot copy.
  --no-extract            Skip the extraction step (implied by --mark-only).
  --received-author STR   Author label to apply to processed comments
                          (default: "Claude (received)").
"""
import argparse, json, os, re, shutil, sys, zipfile, datetime, html
from pathlib import Path
from xml.etree import ElementTree as ET

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

# Recognize legacy [DRAINED ...] markers as already-received for filter purposes,
# so older inboxes migrate cleanly without re-processing.
RECEIVED_PREFIX_RE = re.compile(r'^\s*\[(RECEIVED|DRAINED)\b')


def check_lockfile(docx_path: Path):
    """Refuse to write if Word has the file open (~$<name>.docx exists)."""
    lock = docx_path.with_name('~$' + docx_path.name)
    if lock.exists():
        sys.exit(
            f'ERROR: {docx_path.name} appears to be open in Word '
            f'(lockfile {lock.name} present). Close it first, then re-run.'
        )


def read_comments_raw(docx_path: Path):
    """Return list of {id, author, date, text, anchor, received} from a docx."""
    with zipfile.ZipFile(docx_path) as z:
        try:
            comments_xml = z.read('word/comments.xml').decode('utf-8')
        except KeyError:
            return []
        document_xml = z.read('word/document.xml').decode('utf-8')

    com_root = ET.fromstring(comments_xml)
    out = []
    for c in com_root.iter(f'{{{W}}}comment'):
        cid = c.get(f'{{{W}}}id')
        text = ''.join(t.text or '' for t in c.iter(f'{{{W}}}t'))
        out.append({
            'id': cid,
            'author': c.get(f'{{{W}}}author', ''),
            'date': c.get(f'{{{W}}}date', ''),
            'text': text,
            'received': bool(RECEIVED_PREFIX_RE.match(text)),
        })

    starts = {m.group(1): m.start() for m in re.finditer(
        r'<w:commentRangeStart w:id="(\d+)"/>', document_xml)}
    ends = {m.group(1): m.start() for m in re.finditer(
        r'<w:commentRangeEnd w:id="(\d+)"/>', document_xml)}
    for c in out:
        s, e = starts.get(c['id']), ends.get(c['id'])
        if s is None or e is None or e <= s:
            c['anchor'] = ''
        else:
            raw = document_xml[s:e]
            c['anchor'] = re.sub(r'<[^>]+>', '', raw).strip()
    return out


def filter_comments(comments, author=None, since=None, not_received=False):
    out = comments
    if author:
        out = [c for c in out if c['author'] == author]
    if since:
        out = [c for c in out if c['date'] >= since]
    if not_received:
        out = [c for c in out if not c['received']]
    return out


def mark_comments_received(docx_path: Path, ids_to_mark, received_author, today_iso):
    """In-place: prefix each target comment's first <w:t> with [RECEIVED <date>],
    change w:author + w:initials. Writes back to the same file."""
    if not ids_to_mark:
        return 0
    ids_set = set(str(i) for i in ids_to_mark)

    with zipfile.ZipFile(docx_path) as z:
        files = {name: z.read(name) for name in z.namelist()}
    comments_xml = files['word/comments.xml'].decode('utf-8')

    prefix = f'[RECEIVED {today_iso}] '
    initials = ''.join(w[0] for w in received_author.split() if w)[:3].upper() or 'CR'

    def replace_comment(match):
        full = match.group(0)
        cid = re.search(r'w:id="(\d+)"', full).group(1)
        if cid not in ids_set:
            return full
        full = re.sub(r'w:author="[^"]*"', f'w:author="{html.escape(received_author)}"', full, count=1)
        full = re.sub(r'w:initials="[^"]*"', f'w:initials="{initials}"', full, count=1)
        if 'w:initials=' not in full:
            full = full.replace('w:author=', f'w:initials="{initials}" w:author=', 1)

        def prefix_first_t(s):
            m = re.search(r'(<w:t(\s[^>]*)?>)([^<]*)(</w:t>)', s)
            if not m:
                return s
            opener, _, body, closer = m.group(1), m.group(2) or '', m.group(3), m.group(4)
            if 'xml:space' not in opener:
                opener = opener[:-1] + ' xml:space="preserve">'
            return s[:m.start()] + opener + html.escape(prefix) + body + closer + s[m.end():]
        return prefix_first_t(full)

    new_xml, _ = re.subn(
        r'<w:comment\b[^>]*>.*?</w:comment>',
        replace_comment,
        comments_xml,
        flags=re.DOTALL,
    )
    files['word/comments.xml'] = new_xml.encode('utf-8')

    tmp = docx_path.with_suffix('.docx.tmp')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)
    os.replace(tmp, docx_path)
    return len(ids_set)


def snapshot(docx_path: Path, archive_dir: Path):
    archive_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    dest = archive_dir / f'{docx_path.stem}_snapshot_{ts}.docx'
    shutil.copy2(docx_path, dest)
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inbox', help='Path to perpetual inbox .docx')
    ap.add_argument('--extract-out', help='Where to write extracted comments JSON')
    ap.add_argument('--archive-dir', help='Folder to snapshot the pre-process inbox into')
    ap.add_argument('--from-manuscript', help='Source manuscript to seed inbox from if missing')
    ap.add_argument('--author')
    ap.add_argument('--since')
    ap.add_argument('--not-received', action='store_true')
    ap.add_argument('--mark-only', action='store_true')
    ap.add_argument('--no-mark', action='store_true')
    ap.add_argument('--no-archive', action='store_true')
    ap.add_argument('--no-extract', action='store_true')
    ap.add_argument('--received-author', default='Claude (received)')
    ap.add_argument('--received-date', help='ISO date for the [RECEIVED ...] tag (default: today)')
    args = ap.parse_args()

    inbox = Path(args.inbox).expanduser().resolve()
    if not inbox.exists():
        if args.from_manuscript:
            src = Path(args.from_manuscript).expanduser().resolve()
            if not src.exists():
                sys.exit(f'ERROR: --from-manuscript not found: {src}')
            inbox.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, inbox)
            print(f'Created inbox from {src.name} → {inbox}')
        else:
            sys.exit(f'ERROR: inbox not found: {inbox}\n'
                     f'Pass --from-manuscript PATH to auto-create from a manuscript.')

    today = args.received_date or datetime.date.today().isoformat()
    do_extract = not (args.no_extract or args.mark_only)
    do_mark = not args.no_mark
    do_archive = not args.no_archive

    if do_extract and not args.extract_out:
        sys.exit('ERROR: --extract-out required (or pass --no-extract / --mark-only).')
    if do_archive and not args.archive_dir:
        sys.exit('ERROR: --archive-dir required (or pass --no-archive).')

    if do_mark:
        check_lockfile(inbox)

    all_comments = read_comments_raw(inbox)
    targets = filter_comments(all_comments,
                              author=args.author,
                              since=args.since,
                              not_received=args.not_received)

    print(f'Inbox: {inbox}')
    print(f'Total comments: {len(all_comments)}')
    print(f'Already received: {sum(1 for c in all_comments if c["received"])}')
    print(f'Matching filter: {len(targets)}')

    if do_archive:
        snap = snapshot(inbox, Path(args.archive_dir).expanduser().resolve())
        print(f'Snapshot → {snap}')

    if do_extract:
        out = Path(args.extract_out).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(targets, indent=2, ensure_ascii=False))
        print(f'Extracted {len(targets)} comments → {out}')

    if do_mark and targets:
        n = mark_comments_received(
            inbox,
            ids_to_mark=[c['id'] for c in targets],
            received_author=args.received_author,
            today_iso=today,
        )
        print(f'Marked {n} comments as received in {inbox.name}')
    elif do_mark:
        print('Nothing to mark.')


if __name__ == '__main__':
    main()
