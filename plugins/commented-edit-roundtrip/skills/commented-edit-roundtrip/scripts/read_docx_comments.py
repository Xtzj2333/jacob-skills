"""
Read all comments from a .docx file and emit JSON.

Each comment carries:
  - id           Word comment id (string)
  - author
  - date         ISO 8601
  - text         comment body, plain text
  - anchor       text in the document the comment is attached to (plain text,
                 stripped from XML and joined across cross-run splits)

Usage:
  python3 read_docx_comments.py FILE.docx [--filter-author NAME] \\
                                          [--since YYYY-MM-DD] \\
                                          [--out comments.json]

Defaults: prints JSON to stdout.

Why anchor extraction is non-trivial: in Word docx, a single visible run of
text can be split across multiple <w:t> elements (e.g., when a tracked change
splits a sentence, or when proofing tags break a word). The anchor span between
<w:commentRangeStart/> and <w:commentRangeEnd/> often crosses several runs.
This script walks the XML in document order and concatenates ALL <w:t> content
between the matching range markers, ignoring formatting tags.
"""
import argparse, json, re, sys, zipfile
from xml.etree import ElementTree as ET

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def read_comments(docx_path):
    with zipfile.ZipFile(docx_path) as z:
        try:
            comments_xml = z.read('word/comments.xml').decode('utf-8')
        except KeyError:
            return []
        document_xml = z.read('word/document.xml').decode('utf-8')

    # Parse comment metadata + body
    com_root = ET.fromstring(comments_xml)
    meta = {}
    for c in com_root.iter(f'{{{W}}}comment'):
        cid = c.get(f'{{{W}}}id')
        meta[cid] = {
            'id': cid,
            'author': c.get(f'{{{W}}}author', ''),
            'date': c.get(f'{{{W}}}date', ''),
            'text': ''.join(t.text or '' for t in c.iter(f'{{{W}}}t')),
        }

    # Map ranges to anchor text by walking document.xml positions
    starts = {m.group(1): m.start() for m in re.finditer(
        r'<w:commentRangeStart w:id="(\d+)"/>', document_xml)}
    ends = {m.group(1): m.start() for m in re.finditer(
        r'<w:commentRangeEnd w:id="(\d+)"/>', document_xml)}

    out = []
    for cid, m in meta.items():
        s, e = starts.get(cid), ends.get(cid)
        if s is None or e is None or e <= s:
            m['anchor'] = ''
        else:
            raw = document_xml[s:e]
            m['anchor'] = re.sub(r'<[^>]+>', '', raw).strip()
        out.append(m)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('docx')
    ap.add_argument('--filter-author', help='Only return comments by this author')
    ap.add_argument('--since', help='Only return comments dated >= YYYY-MM-DD')
    ap.add_argument('--out', help='Write JSON to file (default: stdout)')
    args = ap.parse_args()

    comments = read_comments(args.docx)
    if args.filter_author:
        comments = [c for c in comments if c['author'] == args.filter_author]
    if args.since:
        comments = [c for c in comments if c['date'] >= args.since]

    payload = json.dumps(comments, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, 'w') as f:
            f.write(payload)
        print(f'Wrote {len(comments)} comments → {args.out}', file=sys.stderr)
    else:
        print(payload)


if __name__ == '__main__':
    main()
