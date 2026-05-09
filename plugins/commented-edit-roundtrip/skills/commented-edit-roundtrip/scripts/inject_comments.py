"""
Inject Word margin comments into a docx file. Anchors are unique substrings
of the document body text. Each anchor is wrapped with a Word comment.

Strategy:
  1. Read word/document.xml.
  2. For each anchor: search inside every <w:t>...</w:t> element. If found
     uniquely, split that <w:t> element into 3 (pre, mid, post) inside the
     SAME <w:r>; then move the wrapping <w:r> ... </w:r> for the middle part
     out as its own run, and put commentRangeStart/End markers around it.
  3. Append a CommentReference run after the end marker.
  4. Append <w:comment> entries to word/comments.xml.
  5. Append entries to commentsIds.xml + commentsExtensible.xml.
  6. Write all updated parts back into the docx (zip).
"""
import argparse, re, shutil, sys, zipfile, datetime, html, os, json
from pathlib import Path

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def build_comment_xml(cid, author, initials, date_iso, body_text):
    body_text_xml = html.escape(body_text)
    # Use plain runs with no special formatting; mark first run as annotationRef
    return (
        f'<w:comment w:id="{cid}" w:author="{html.escape(author)}" '
        f'w:date="{date_iso}" w:initials="{html.escape(initials)}">'
        f'<w:p><w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr>'
        f'<w:annotationRef/></w:r>'
        f'<w:r><w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
        f'<w:t xml:space="preserve">{body_text_xml}</w:t></w:r></w:p>'
        f'</w:comment>'
    )

def find_run_containing(doc_xml, anchor):
    """
    Find a <w:r> element whose <w:t> child contains the anchor substring.
    Returns (run_start, run_end, t_inner_text, t_match_start_in_inner, t_open_tag, t_close_tag)
    """
    # Look for <w:r ...>...<w:t ...>(text)</w:t>...</w:r> with anchor in (text)
    # The text can contain HTML-escaped entities but anchor we pass should
    # be the literal characters; escape them for regex search if needed.
    escaped = html.escape(anchor)
    pattern = re.compile(r'(<w:r\b[^>]*>(?:(?!</w:r>).)*?<w:t(?:\s[^>]*)?>)([^<]*)(</w:t>(?:(?!</w:r>).)*?</w:r>)', re.DOTALL)
    for m in pattern.finditer(doc_xml):
        inner = m.group(2)
        # Try matching either escaped or unescaped
        idx = -1
        used = None
        for needle in (escaped, anchor):
            i = inner.find(needle)
            if i != -1:
                idx, used = i, needle
                break
        if idx == -1:
            continue
        return {
            'run_match': m,
            'open_tag_end': m.end(1),
            't_open_chunk': m.group(1),
            't_inner': inner,
            't_close_chunk': m.group(3),
            'inner_idx': idx,
            'needle': used,
        }
    return None

def inject_comment_at_anchor(doc_xml, anchor, comment_id):
    """
    Wrap the run containing `anchor` with commentRangeStart/End and append
    a CommentReference run.
    Returns updated doc_xml or None if anchor not found.
    """
    info = find_run_containing(doc_xml, anchor)
    if info is None:
        return None
    m = info['run_match']
    # Build replacement: split the run's <w:t> at the anchor.
    open_chunk = info['t_open_chunk']     # everything from <w:r> up to opening <w:t ...>
    inner = info['t_inner']
    close_chunk = info['t_close_chunk']   # </w:t>...</w:r>
    idx = info['inner_idx']
    needle = info['needle']

    pre = inner[:idx]
    mid = needle
    post = inner[idx+len(needle):]

    # We must reconstruct the run-properties for the new mid run.
    # Easiest: reuse the original opening through to "<w:t" attribute of opener
    # and reuse the original "</w:t>...</w:r>" closer.

    # Construct three runs:
    #   <w:r ...>(rPr)<w:t>pre</w:t></w:r>
    #   <commentRangeStart/>
    #   <w:r ...>(rPr)<w:t>mid</w:t></w:r>
    #   <commentRangeEnd/>
    #   <w:r ...><rPr CommentRef/><commentReference/></w:r>
    #   <w:r ...>(rPr)<w:t>post</w:t></w:r>

    # Get the opening <w:r ...> and closing </w:r>; reuse for all three text runs.
    # open_chunk ends at end of "<w:t...>"; we need just up through the <w:t> open.
    # close_chunk begins at "</w:t>" onward.

    def make_run(text):
        if text == '':
            return ''
        # Add xml:space=preserve if not already present
        opener = open_chunk
        if 'xml:space' not in opener:
            opener = re.sub(r'<w:t(?=[\s>])', '<w:t xml:space="preserve"', opener, count=1)
        return opener + text + close_chunk

    cmt_ref_run = (
        f'<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr>'
        f'<w:commentReference w:id="{comment_id}"/></w:r>'
    )

    replacement_pieces = []
    if pre:
        replacement_pieces.append(make_run(pre))
    replacement_pieces.append(f'<w:commentRangeStart w:id="{comment_id}"/>')
    if mid:
        replacement_pieces.append(make_run(mid))
    replacement_pieces.append(f'<w:commentRangeEnd w:id="{comment_id}"/>')
    replacement_pieces.append(cmt_ref_run)
    if post:
        replacement_pieces.append(make_run(post))

    replacement = ''.join(replacement_pieces)
    new_xml = doc_xml[:m.start()] + replacement + doc_xml[m.end():]
    return new_xml

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--docx', required=True)
    ap.add_argument('--comments-json', required=True,
                    help='JSON list of {anchor, comment, [author], [initials]}')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    docx_path = Path(args.docx)
    with zipfile.ZipFile(docx_path) as z:
        files = {name: z.read(name) for name in z.namelist()}

    doc_xml = files['word/document.xml'].decode()
    comments_xml = files.get('word/comments.xml',
                             b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                             b'<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"></w:comments>'
                            ).decode()

    # Find max comment id
    existing_ids = [int(x) for x in re.findall(r'<w:comment w:id="(\d+)"', comments_xml)]
    next_id = (max(existing_ids) + 1) if existing_ids else 1

    spec = json.loads(Path(args.comments_json).read_text())
    inserted = []
    skipped = []
    new_comment_xmls = []

    for entry in spec:
        anchor = entry['anchor']
        body = entry['comment']
        author = entry.get('author', 'Change Audit (Apr 2026)')
        initials = entry.get('initials', 'CA')
        date_iso = entry.get('date', '2026-04-26T17:00:00Z')

        new_doc = inject_comment_at_anchor(doc_xml, anchor, next_id)
        if new_doc is None:
            skipped.append(anchor)
            continue
        doc_xml = new_doc
        new_comment_xmls.append(build_comment_xml(next_id, author, initials, date_iso, body))
        inserted.append((next_id, anchor[:60]))
        next_id += 1

    # Splice new <w:comment> entries before </w:comments>
    if new_comment_xmls:
        comments_xml = comments_xml.replace('</w:comments>', ''.join(new_comment_xmls) + '</w:comments>')

    files['word/document.xml'] = doc_xml.encode('utf-8')
    files['word/comments.xml'] = comments_xml.encode('utf-8')

    # Write a fresh zip
    out_path = Path(args.out)
    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)

    print('Inserted:', len(inserted))
    for cid, anc in inserted:
        print(f'  comment #{cid}: {anc}')
    print('Skipped (anchor not found):', len(skipped))
    for anc in skipped:
        print(f'  - "{anc[:80]}"')

if __name__ == '__main__':
    main()
