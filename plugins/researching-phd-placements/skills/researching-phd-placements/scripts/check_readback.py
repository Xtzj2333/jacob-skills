"""Check a placement Google Doc after upload, from its Drive readback (markdown from read_file_content).

Usage: python3 check_readback.py readback.md [--people N]

Checks: the table of contents exists and every entry links to a heading ID (an empty "#heading=" means the
headings were imported without IDs: repair them, see references/gdocs-publish.md); TOC entries = Heading 2 count;
adviser counts in normal weight ("**Name**（3 人）", as in Jacob's Berkeley doc; the heading-ID repair re-bolds them);
optionally the number of distinct people. Exit code 1 on any failure.
"""
import argparse, re, sys

ap = argparse.ArgumentParser()
ap.add_argument("readback")
ap.add_argument("--people", type=int, help="expected number of distinct graduates")
a = ap.parse_args()
md = open(a.readback).read()

fails = []
toc = re.findall(r"#heading=([^)\s]*)\)", md)
heads = re.findall(r"^## (.+)$", md, flags=re.M)
if not toc:
    fails.append("no table of contents found (insert one: Insert > Page elements > Table of contents)")
empty = sum(1 for t in toc if not t)
if empty:
    fails.append(f"{empty} of {len(toc)} TOC entries link to an empty heading ID (headings imported without IDs)")
if toc and len(toc) != len(heads):
    fails.append(f"{len(toc)} TOC entries but {len(heads)} Heading 2 headings (refresh the TOC)")
bold_counts = [h for h in heads if re.match(r"\*\*[^*]*（.*\*\*\s*$", h)]
if bold_counts:
    fails.append(f"{len(bold_counts)} of {len(heads)} headings have the count in bold, e.g. {bold_counts[0]!r} "
                 "(un-bold each count after the heading-ID repair; see references/gdocs-publish.md)")
if a.people is not None:
    names = {re.sub(r"\*|\\", "", m).strip() for m in re.findall(r"^\s*- ([^\[\n]+?) \(PhD \d{4};", md, flags=re.M)}
    if len(names) != a.people:
        fails.append(f"{len(names)} distinct people in the doc, expected {a.people}")
for f in fails:
    print("FAIL:", f)
print(f"{len(heads)} headings, {len(toc)} TOC links, {len(fails)} failures")
sys.exit(1 if fails else 0)
