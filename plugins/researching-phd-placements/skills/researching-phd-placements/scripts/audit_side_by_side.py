"""Line up the blind audit against the doc, person by person, for step 7 of the skill.

Usage: python3 audit_side_by_side.py people.json audit.jsonl [--alias "Audit Name=Doc Name" ...]

people.json is the doc input (references/doc-format.md); audit.jsonl is the blind agent's output in the agent-brief
schema (jobs with start/end/title/employer/confidence). Prints, per person, the doc's jobs and the audit's jobs, and a
first-job / current-job verdict hint (same start year within 1, shared employer word). The hint is only a sort key:
read every pair yourself, and open the sources where they disagree before deciding which side is right.
"""
import argparse, json, re

ap = argparse.ArgumentParser()
ap.add_argument("people")
ap.add_argument("audit")
ap.add_argument("--alias", action="append", default=[], help='"Name in audit=Name in doc"')
a = ap.parse_args()
alias = dict(x.split("=", 1) for x in a.alias)
people = {p["name"]: p for p in json.load(open(a.people))}

STOP = {"university", "of", "the", "college", "department", "school", "center", "centre", "and", "for", "in", "at"}
words = lambda s: {w for w in re.findall(r"[a-z]+", (s or "").lower()) if w not in STOP and len(w) > 2}
start = lambda y: int(y[:4]) if y and y[:4].isdigit() else None


def hint(d, x):
    if not d or not x:
        return "missing"
    same_emp = bool(words(d.get("employer")) & words(x.get("employer")))
    ds, xs = start(d.get("years", "")), x.get("start")
    same_year = ds is None or xs is None or abs(ds - xs) <= 1
    return "agree" if same_emp and same_year else "employer differs" if not same_emp else f"year {ds} vs {xs}"


for line in open(a.audit):
    if not line.strip():
        continue
    r = json.loads(line)
    name = alias.get(r["name"], r["name"])
    p = people.get(name)
    print("=" * 8, name, "" if p else "(NOT IN people.json — add an --alias)")
    if not p:
        continue
    dj, aj = p.get("jobs") or [], r.get("jobs") or []
    print("  doc  :", " | ".join(f"[{j['years']}] {j['title']}, {j.get('employer', '')}" for j in dj) or p.get("empty"))
    print("  audit:", " | ".join(f"[{j.get('start')}-{j.get('end') or ''}] {j.get('title')}, {j.get('employer')} ({j.get('confidence')})" for j in aj) or r.get("status"))
    print(f"  first: {hint(dj[0] if dj else None, aj[0] if aj else None)}   current: {hint(dj[-1] if dj else None, aj[-1] if aj else None)}")
