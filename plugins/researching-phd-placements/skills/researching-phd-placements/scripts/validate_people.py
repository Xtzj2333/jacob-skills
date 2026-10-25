"""Check people.json before building the doc. Exit code 1 if anything would render wrong.

Usage: python3 validate_people.py people.json

Errors: missing name/year, duplicate names, a person with neither jobs nor an "empty" line (or both),
year ranges not in the doc's "[2016-19]" style, an end year before its start.
Warnings (read them, they are where mistakes hide): advisers sharing a first name (rendered "Jeff D."),
people sharing a surname (surname matching of department lines will collide), jobs out of order,
jobs without an employer.
"""
import json, re, sys
from collections import defaultdict

YEARS = re.compile(r"^(\d{4}(-(\d{2}\+?|\?)?)?|\?(-(\d{4})?)?|dates n/a)$")


def span(y):
    m = re.match(r"^(\d{4})-(\d{2})", y)
    return (int(m.group(1)), int(m.group(1)[:2] + m.group(2))) if m else None


def check(people):
    errors, warnings = [], []
    seen = set()
    for p in people:
        n = p.get("name") or "<no name>"
        if not p.get("name"):
            errors.append("a person has no name")
        if not isinstance(p.get("phd_year"), int):
            errors.append(f"{n}: phd_year missing or not an integer")
        if n in seen:
            errors.append(f"{n}: listed twice")
        seen.add(n)
        jobs = p.get("jobs") or []
        if bool(jobs) == bool(p.get("empty")):
            errors.append(f"{n}: needs either jobs or an 'empty' line, not {'both' if jobs else 'neither'} (no jobs and no empty line)")
        if not p.get("advisers") and not p.get("committee"):
            warnings.append(f"{n}: no advisers and no committee; the person line will be blank")
        starts = []
        for j in jobs:
            y = j.get("years", "")
            if not YEARS.match(y):
                errors.append(f"{n}: years '{y}' not in doc style (2016-19, 2023-, 2015-?, ?-2020, 2026, ?)")
            s = span(y)
            if s and s[1] < s[0]:
                errors.append(f"{n}: years '{y}' end before they start")
            if not j.get("title"):
                errors.append(f"{n}: a job has no title")
            if not j.get("employer"):
                warnings.append(f"{n}: job '{j.get('title')}' has no employer")
            if y[:4].isdigit():
                starts.append(int(y[:4]))
        if starts != sorted(starts):
            warnings.append(f"{n}: jobs not in start-year order {starts}")
    advisers = {a for p in people for a in (p.get("advisers") or p.get("committee") or [])}
    by_first = defaultdict(set)
    for a in advisers:
        by_first[a.split()[0]].add(a)
    for f, ns in by_first.items():
        if len(ns) > 1:
            warnings.append(f"advisers share the first name {f}: {sorted(ns)} (rendered as '{f} X.')")
    by_last = defaultdict(list)
    for p in people:
        if p.get("name"):
            by_last[p["name"].split()[-1]].append(p["name"])
    for l, ns in by_last.items():
        if len(ns) > 1:
            warnings.append(f"graduates share the surname {l}: {ns} (match department lines by full name)")
    return errors, warnings


if __name__ == "__main__":
    people = json.load(open(sys.argv[1]))
    errors, warnings = check(people)
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    print(f"{len(people)} people, {len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)
