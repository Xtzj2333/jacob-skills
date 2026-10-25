"""Build the placement Google-Doc HTML in Jacob's format from one people.json file.

Usage:
  python3 build_gdoc.py people.json --intro intro.txt --out gdoc.html [--dup-reason "co-advisers"]

people.json is a list of people (schema in references/doc-format.md):
  {"name": "Maya Lindqvist", "phd_year": 2016,
   "advisers": ["Helen Park", "Marcus Webb"],       # primary first; [] if not public yet
   "adviser_note": "dissertation co-chairs",        # optional, shown in the duplicate tag
   "committee": ["..."],                            # shown only when advisers is []
   "jobs": [{"years": "2016-23", "title": "Assistant Professor of Psychology",
             "employer": "University of Toronto", "note": ""}],
   "empty": "[2022-] No placement found publicly (checked Oct 2026)"}   # instead of jobs

Output: one <h2> per primary adviser ("Name（N 人，另有 M 人共同指导）"), most primary students first;
each person once in full under the primary adviser and again, yellow-highlighted and tagged
"— 重复：主导师 X 名下已计（reason）", under every other adviser; first and last job bold; people whose
adviser is not public go in a final section with their committee. Upload with upload_gdoc.sh.
"""
import argparse, html, json
from collections import defaultdict

HL = "#fff2cc"
PENDING = "主导师尚未公开"
PENDING_NOTE = "论文尚未入库，列出答辩委员会"


def esc(t):
    return html.escape(t or "", quote=False)


def base_short(name):
    parts = name.split()
    # "J. Allen Hart" -> "J. Allen"; otherwise the first name
    return " ".join(parts[:2]) if len(parts) > 2 and len(parts[0]) <= 2 and parts[0].endswith(".") else parts[0]


def short_names(people):
    """First name for each adviser, or "First L." when two advisers in the doc share a first name."""
    names = {a for p in people for a in (p.get("advisers") or p.get("committee") or [])}
    by_first = defaultdict(list)
    for n in names:
        by_first[base_short(n)].append(n)
    return {n: (f if len(ns) == 1 else f"{f} {n.split()[-1][0]}.") for f, ns in by_first.items() for n in ns}


def job_html(j, bold):
    head = f"[{esc(j['years'])}] {esc(j['title'])}" + ("," if j.get("employer") else "")
    emp, note = esc(j.get("employer")), esc(j.get("note"))
    if bold:
        return f"<b>{head} </b>" + (f"<b><i>{emp}</i></b>" if emp else "") + (f"<b> ({note})</b>" if note else "")
    return f"{head} " + (f"<i>{emp}</i>" if emp else "") + (f" ({note})" if note else "")


def person_line(p, short, dup_of=None, dup_reason=""):
    adv = p.get("advisers") or []
    if adv:
        lab = f"(PhD {p['phd_year']}; {'PIs' if len(adv) > 1 else 'PI'}: {' & '.join(short[a] for a in adv)})"
    else:
        lab = f"(PhD {p['phd_year']}; committee: {', '.join(short[a] for a in p.get('committee') or [])})"
    line = f"{p['name']} {lab}"
    if dup_of:
        line += f" — 重复：主导师 {short[dup_of]} 名下已计（{p.get('adviser_note') or dup_reason}）"
    return line


def person_block(p, short, dup_of=None, dup_reason=""):
    wrap = (lambda s: f'<span style="background-color:{HL}">{s}</span>') if dup_of else (lambda s: s)
    jobs = p.get("jobs") or []
    items = [f"<b>{esc(p['empty'])}</b>"] if not jobs else \
            [job_html(j, bold=(i == 0 or i == len(jobs) - 1)) for i, j in enumerate(jobs)]
    sub = "".join(f"<li>{wrap(s)}</li>" for s in items)
    return f"<li>{wrap(esc(person_line(p, short, dup_of, dup_reason)))}<ul>{sub}</ul></li>"


def group(people):
    groups = {}
    for p in people:
        for k, a in enumerate(p.get("advisers") or [PENDING]):
            g = groups.setdefault(a, {"primary": [], "secondary": []})
            (g["primary"] if k == 0 else g["secondary"]).append(p)
    order = sorted(groups, key=lambda a: (a == PENDING, -len(groups[a]["primary"]),
                                          -len(groups[a]["secondary"]), a.split()[-1]))
    return groups, order


def build(people, intro, dup_reason="co-advisers", pending_note=PENDING_NOTE):
    bad = [p["name"] for p in people if not p.get("jobs") and not p.get("empty")]
    assert not bad, f"no jobs and no 'empty' line for {bad}"
    short = short_names(people)
    groups, order = group(people)
    yr = lambda p: (p.get("phd_year") or 0, p["name"])
    out = [f"<p>{esc(intro)}</p>"]
    # Docs' import bolds a whole Heading 2 unless the count is explicitly normal weight
    normal = lambda s: f'<span style="font-weight:normal">{s}</span>'
    for a in order:
        g = groups[a]
        if a == PENDING:
            out.append(f"<h2><b>{PENDING}</b>{normal(f'（{len(g['primary'])} 人：{esc(pending_note)}）')}</h2><ul>")
        else:
            cnt = f"（{len(g['primary'])} 人" + (f"，另有 {len(g['secondary'])} 人共同指导" if g["secondary"] else "") + "）"
            out.append(f"<h2><b>{esc(a)}</b>{normal(cnt)}</h2><ul>")
        out += [person_block(p, short) for p in sorted(g["primary"], key=yr)]
        out += [person_block(p, short, p["advisers"][0], dup_reason) for p in sorted(g["secondary"], key=yr)]
        out.append("</ul>")
    return "<html><body>" + "".join(out) + "</body></html>", groups, order


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("people")
    ap.add_argument("--intro", required=True, help="text file with the intro paragraph")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dup-reason", default="co-advisers", help="default reason in the duplicate tag")
    ap.add_argument("--pending-note", default=PENDING_NOTE)
    a = ap.parse_args()
    people = json.load(open(a.people))
    doc, groups, order = build(people, open(a.intro).read().strip(), a.dup_reason, a.pending_note)
    open(a.out, "w").write(doc)
    print(f"{len(people)} people, {len(order)} headings -> {a.out}")
    for k in order:
        print(f"  {k}: {len(groups[k]['primary'])} + {len(groups[k]['secondary'])}")
