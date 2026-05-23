#!/usr/bin/env python3
"""
parse_comments.py — span-based comment attribution for to do.docx

WHY THIS EXISTS
---------------
The naive approach ("a comment belongs to the nearest preceding [tNNN] marker
in the rendered text") is WRONG for Word docs. Word comments are anchored to
explicit character ranges via w:commentRangeStart / w:commentRangeEnd — these
ranges can span multiple paragraphs and may enclose zero, one, or many task
markers. A comment on t017's TITLE can show visually near the t044 block if
t044 follows t017 in the document, and a line-based scan will mis-assign.

The correct algorithm: use the actual w:commentRangeStart / w:commentRangeEnd
elements in document.xml, figure out which [tNNN] markers lie INSIDE that
range, and only fall back to surrounding context if the range is empty.

USAGE
-----
    python3 parse_comments.py <docx_path> [--json]

Prints, for each comment in the docx:
    comment id, author, text, target task ids (inside the range),
    and — if the range is empty of markers — candidate ids from
    the preceding/following 500 chars, clearly labeled as fallback.

Exit status 0 on success. Use --json for machine-readable output.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = f"{{{NS['w']}}}"
MARKER_RE = re.compile(r"\[t\d+\]")


def load_xml(docx_path: str) -> tuple[str, str]:
    with zipfile.ZipFile(docx_path) as z:
        doc_xml = z.read("word/document.xml").decode()
        try:
            com_xml = z.read("word/comments.xml").decode()
        except KeyError:
            com_xml = ""
    return doc_xml, com_xml


def parse_comments(com_xml: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not com_xml:
        return out
    root = ET.fromstring(com_xml)
    for c in root.findall(f"{W}comment"):
        cid = c.get(f"{W}id")
        if cid is None:
            continue
        out[cid] = {
            "author": c.get(f"{W}author", "?"),
            "date": c.get(f"{W}date", ""),
            "text": "".join(t.text or "" for t in c.iter(f"{W}t")),
        }
    return out


def walk_events(body: ET.Element) -> list[tuple[str, str]]:
    """Linearize the body into ('crstart'|'crend'|'cref'|'text', value) events."""
    events: list[tuple[str, str]] = []

    def walk(el: ET.Element) -> None:
        tag = el.tag
        if tag == f"{W}commentRangeStart":
            events.append(("crstart", el.get(f"{W}id", "")))
        elif tag == f"{W}commentRangeEnd":
            events.append(("crend", el.get(f"{W}id", "")))
        elif tag == f"{W}commentReference":
            events.append(("cref", el.get(f"{W}id", "")))
        elif tag == f"{W}t":
            events.append(("text", el.text or ""))
        for child in el:
            walk(child)

    walk(body)
    return events


def attribute_comments(docx_path: str) -> list[dict]:
    doc_xml, com_xml = load_xml(docx_path)
    comments = parse_comments(com_xml)
    droot = ET.fromstring(doc_xml)
    body = droot.find(f"{W}body")
    if body is None:
        return []
    events = walk_events(body)

    # Build a single concatenated text and find ALL [tNNN] marker positions.
    # This lets us detect markers that PARTIALLY overlap a comment span — the
    # case that broke attribution on 2026-04-28 (comment span started at
    # "t043]" because the leading "[" was excluded from the user's selection).
    full_text = "".join(e[1] for e in events if e[0] == "text")
    all_markers = [(m.start(), m.end(), m.group(0)) for m in MARKER_RE.finditer(full_text)]

    # Translate event index → cumulative character offset in full_text
    text_positions: list[int] = []
    pos = 0
    for kind, val in events:
        text_positions.append(pos)
        if kind == "text":
            pos += len(val)
    text_positions.append(pos)  # sentinel for end

    results: list[dict] = []
    for i, (kind, val) in enumerate(events):
        if kind != "crstart":
            continue
        cid = val
        end_idx: int | None = None
        for j in range(i + 1, len(events)):
            if events[j][0] == "crend" and events[j][1] == cid:
                end_idx = j
                break

        span_start = text_positions[i + 1]
        span_end = text_positions[end_idx if end_idx is not None else len(events)]
        span_text = full_text[span_start:span_end]

        # Markers fully inside the span (strict — selection includes the brackets)
        strict_inside = [m for m in all_markers if m[0] >= span_start and m[1] <= span_end]
        # Markers that even partially overlap the span (any character touches)
        overlapping = [m for m in all_markers if m[0] < span_end and m[1] > span_start]

        if strict_inside:
            inside_markers = strict_inside
            attribution = "range"
        elif overlapping:
            inside_markers = overlapping
            attribution = "range-partial"  # selection cut off a bracket — still trustworthy
        else:
            inside_markers = []
            attribution = None  # fall through to context fallback below

        # Context fallback (only used if span had no markers at all)
        preceding = full_text[:span_start]
        following = full_text[span_end:]
        after = MARKER_RE.findall(following[:500])
        before = MARKER_RE.findall(preceding[-500:])

        if inside_markers:
            targets = list(dict.fromkeys(m[2] for m in inside_markers))
        elif after:
            targets = [after[0]]
            attribution = "fallback-following"
        elif before:
            targets = [before[-1]]
            attribution = "fallback-preceding"
        else:
            targets = []
            attribution = "unattributed"

        meta = comments.get(cid, {"author": "?", "text": "?"})
        results.append(
            {
                "comment_id": cid,
                "author": meta["author"],
                "date": meta.get("date", ""),
                "text": meta.get("text", ""),
                "targets": targets,
                "attribution": attribution,
                # ALWAYS include the literal span text so consumers can verify
                # attribution visually without re-parsing the docx.
                "span_text": span_text,
                "span_text_short": (span_text[:120] + "…") if len(span_text) > 120 else span_text,
                "inside_range": [m[2] for m in strict_inside],
                "overlapping_range": [m[2] for m in overlapping],
                "nearby_after_500": after[:3],
                "nearby_before_500": before[-3:],
            }
        )
    return results


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: parse_comments.py <docx_path> [--json]", file=sys.stderr)
        return 2
    docx_path = argv[1]
    as_json = "--json" in argv[2:]

    results = attribute_comments(docx_path)

    if as_json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

    if not results:
        print("(no comments found)")
        return 0

    for r in results:
        print(f"=== Comment id={r['comment_id']} ({r['attribution']}) ===")
        print(f"  author    : {r['author']}")
        print(f"  targets   : {', '.join(r['targets']) if r['targets'] else '(none — UNATTRIBUTED)'}")
        print(f"  text      : {r['text'][:200]}")
        # ALWAYS show literal span text — Rule 12b reinforced 2026-04-28.
        # Visual ground-truth eliminates fallback-misattribution errors.
        print(f"  span text : {r['span_text_short']!r}")
        if r["attribution"] in ("fallback-following", "fallback-preceding", "unattributed"):
            print(f"  ⚠ FALLBACK — span had no [tNNN] markers. Verify visually before acting.")
            print(f"  nearby-before: {r['nearby_before_500']}")
            print(f"  nearby-after : {r['nearby_after_500']}")
        elif r["attribution"] == "range-partial":
            print(f"  ℹ partial-overlap — selection straddled a marker boundary; trust span text.")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
