"""
Map source-text anchors to page numbers in a rendered PDF.

Use case: when a Word docx (or markdown / LaTeX) is converted to PDF, an
anchor like "the pattern flips" needs to be resolved to "PDF page 15" so the
sidecar margin comment can say "[CHANGED IN PDF p. 15]".

Usage:
  python3 pdf_page_locator.py PDF.pdf --anchor "TEXT"
  python3 pdf_page_locator.py PDF.pdf --anchors-file anchors.txt
  python3 pdf_page_locator.py PDF.pdf --anchors-json anchors.json --out pages.json

For each anchor, prints (or emits) the list of page numbers that contain it.
If the anchor is not found, returns []. If multi-page, returns ALL pages.

Strips a configurable running-header pattern so per-page first-line matches
don't get false positives.

Requires: pdftotext (poppler) — `brew install poppler` on macOS.
"""
import argparse, json, os, re, subprocess, sys, tempfile


def normalize(s):
    return re.sub(r'\s+', ' ', s).strip().lower()


def extract_pages(pdf_path, header_pattern=None):
    """Return list of strings, one per PDF page (text content)."""
    pages = []
    with tempfile.TemporaryDirectory() as td:
        # pdftotext numbers pages 1..N; -f, -l for ranges. We do per-page.
        # First find page count.
        info = subprocess.check_output(['pdfinfo', pdf_path], text=True)
        n = int(re.search(r'Pages:\s+(\d+)', info).group(1))
        for p in range(1, n + 1):
            out = os.path.join(td, f'p{p}.txt')
            subprocess.check_call(['pdftotext', '-layout', '-f', str(p), '-l',
                                   str(p), pdf_path, out])
            txt = open(out).read()
            if header_pattern:
                txt = re.sub(header_pattern, '', txt)
            pages.append(txt)
    return pages


def locate(anchor, pages):
    needle = normalize(anchor)
    hits = []
    for i, p in enumerate(pages, 1):
        if needle in normalize(p):
            hits.append(i)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--anchor')
    g.add_argument('--anchors-file', help='One anchor per line')
    g.add_argument('--anchors-json', help='JSON array or objects with "anchor" field')
    ap.add_argument('--header-pattern', default=None,
                    help='Regex of running header to strip from each page')
    ap.add_argument('--out', help='Write result JSON; default stdout')
    args = ap.parse_args()

    pages = extract_pages(args.pdf, header_pattern=args.header_pattern)

    if args.anchor:
        anchors = [args.anchor]
    elif args.anchors_file:
        anchors = [l.strip() for l in open(args.anchors_file) if l.strip()]
    else:
        data = json.load(open(args.anchors_json))
        if data and isinstance(data[0], dict):
            anchors = [d['anchor'] for d in data]
        else:
            anchors = list(data)

    result = {a: locate(a, pages) for a in anchors}

    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, 'w') as f:
            f.write(payload)
        print(f'Wrote anchor-page map → {args.out}', file=sys.stderr)
    else:
        print(payload)


if __name__ == '__main__':
    main()
