"""
Refresh a perpetual commenting inbox by regenerating it from the current
manuscript while carrying forward un-drained comments by anchor matching.

Use this when Claude has made manuscript-body changes and the user wants a
fresh commenting surface that reflects the new prose. Refresh is opt-in
because it loses anchor positions for any comment whose anchor text no
longer exists verbatim.

Algorithm:
  1. Lockfile guard: refuse if Word has the inbox open.
  2. Snapshot the current inbox to the archive folder for safety.
  3. Read all comments from the current inbox; partition into:
        - received: prefixed with [RECEIVED (or legacy [DRAINED) — drop,
                    they're already in the revision-queue todos / log
        - live:     un-received — these need to be carried forward
  4. Copy the new manuscript to the inbox path (overwriting old inbox).
  5. For each live comment, look up its anchor in the new inbox; if found
     uniquely, inject it via inject_comments.py's logic. If not found,
     append the comment to a sidecar file <inbox>.lost_anchors.md so
     nothing silently disappears.
  6. Write a short summary.

Usage:
  python3 refresh_inbox.py \\
      --inbox revisions/<USER>_inbox.docx \\
      --new-manuscript <MANUSCRIPT_DIR>/<MANUSCRIPT_FILE>.docx \\
      --archive-dir "manuscript_comment_rounds (claude)"
"""
import argparse, datetime, html, json, os, re, shutil, sys, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

# Reuse the inject logic from the existing script by importing it as a module.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from inject_comments import inject_comment_at_anchor, build_comment_xml  # noqa: E402

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def check_lockfile(docx_path: Path):
    lock = docx_path.with_name('~$' + docx_path.name)
    if lock.exists():
        sys.exit(
            f'ERROR: {docx_path.name} is open in Word (lockfile {lock.name}). '
            'Close it first, then re-run.'
        )


def read_comments_raw(docx_path: Path):
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
            'received': text.lstrip().startswith(('[RECEIVED', '[DRAINED')),
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


def snapshot(docx_path: Path, archive_dir: Path):
    archive_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    dest = archive_dir / f'{docx_path.stem}_snapshot_{ts}.docx'
    shutil.copy2(docx_path, dest)
    return dest


def inject_into_docx(docx_path: Path, comments_to_inject):
    """In-place inject comments into docx_path. Returns (inserted, skipped)."""
    with zipfile.ZipFile(docx_path) as z:
        files = {name: z.read(name) for name in z.namelist()}
    doc_xml = files['word/document.xml'].decode()
    comments_xml = files.get(
        'word/comments.xml',
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        b'<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"></w:comments>'
    ).decode()
    existing_ids = [int(x) for x in re.findall(r'<w:comment w:id="(\d+)"', comments_xml)]
    next_id = (max(existing_ids) + 1) if existing_ids else 1

    new_comment_xmls = []
    inserted, skipped = [], []
    for c in comments_to_inject:
        anchor = c['anchor']
        if not anchor:
            skipped.append(c)
            continue
        new_doc = inject_comment_at_anchor(doc_xml, anchor, next_id)
        if new_doc is None:
            skipped.append(c)
            continue
        doc_xml = new_doc
        new_comment_xmls.append(build_comment_xml(
            cid=next_id,
            author=c.get('author') or 'Carried forward',
            initials='CF',
            date_iso=c.get('date') or datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            body_text=c['text'],
        ))
        inserted.append(c)
        next_id += 1

    if new_comment_xmls:
        comments_xml = comments_xml.replace(
            '</w:comments>', ''.join(new_comment_xmls) + '</w:comments>')

    files['word/document.xml'] = doc_xml.encode('utf-8')
    files['word/comments.xml'] = comments_xml.encode('utf-8')

    tmp = docx_path.with_suffix('.docx.tmp')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)
    os.replace(tmp, docx_path)
    return inserted, skipped


def write_lost_anchors_sidecar(inbox_path: Path, lost):
    sidecar = inbox_path.with_suffix('.lost_anchors.md')
    lines = [f'# Lost anchors after refresh on {datetime.date.today().isoformat()}\n']
    lines.append(
        'These comments were live in the previous inbox but their anchor '
        'text no longer exists verbatim in the refreshed manuscript. '
        'Review them manually and re-comment in the new location.\n'
    )
    for c in lost:
        lines.append(f"## Comment {c['id']} — {c.get('author','?')} ({c.get('date','?')})\n")
        lines.append(f"**Original anchor:** `{c.get('anchor','(none)')[:200]}`\n")
        lines.append(f"**Body:**\n\n> {c['text']}\n")
    sidecar.write_text('\n'.join(lines))
    return sidecar


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--inbox', required=True, help='Path to the perpetual inbox .docx')
    ap.add_argument('--new-manuscript', required=True,
                    help='Path to the current canonical manuscript .docx to seed the new inbox from')
    ap.add_argument('--archive-dir', required=True,
                    help='Folder to snapshot the pre-refresh inbox into')
    args = ap.parse_args()

    inbox = Path(args.inbox).expanduser().resolve()
    new_ms = Path(args.new_manuscript).expanduser().resolve()
    archive_dir = Path(args.archive_dir).expanduser().resolve()

    if not new_ms.exists():
        sys.exit(f'ERROR: new manuscript not found: {new_ms}')

    if inbox.exists():
        check_lockfile(inbox)
        all_comments = read_comments_raw(inbox)
        live = [c for c in all_comments if not c['received']]
        received = [c for c in all_comments if c['received']]
        snap = snapshot(inbox, archive_dir)
        print(f'Snapshot of pre-refresh inbox → {snap}')
        print(f'Live comments to carry forward: {len(live)}')
        print(f'Received comments dropped on refresh: {len(received)}')
    else:
        all_comments, live, received = [], [], []
        print('No existing inbox; creating a fresh one.')

    # Replace the inbox with a fresh copy of the manuscript.
    inbox.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(new_ms, inbox)
    print(f'Seeded inbox from {new_ms.name}')

    inserted, skipped = inject_into_docx(inbox, live)
    print(f'Carried forward {len(inserted)} comments by anchor match.')
    print(f'Lost (anchor not found): {len(skipped)}')
    if skipped:
        sidecar = write_lost_anchors_sidecar(inbox, skipped)
        print(f'Lost-anchor sidecar → {sidecar}')


if __name__ == '__main__':
    main()
