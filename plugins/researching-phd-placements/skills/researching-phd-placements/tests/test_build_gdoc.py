"""Tests for build_gdoc.py and validate_people.py. Run: python3 tests/test_build_gdoc.py"""
import json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)
from build_gdoc import build  # noqa: E402
from validate_people import check  # noqa: E402

SAMPLE = json.load(open(os.path.join(HERE, "sample_people.json")))


def test_format():
    doc, groups, order = build(SAMPLE, "intro")
    assert order[0] == "Helen Park" and order[-1] == "主导师尚未公开", order
    # heading counts: Helen has 2 primary, Marcus 1 primary + 1 co-advised
    # counts stay normal weight (Docs' import would otherwise bold the whole heading)
    assert '<h2><b>Helen Park</b><span style="font-weight:normal">（2 人）</span></h2>' in doc
    assert '<h2><b>Marcus Webb</b><span style="font-weight:normal">（1 人，另有 1 人共同指导）</span></h2>' in doc
    # person line and PIs label with first names
    assert "Daniel Osei (PhD 2019; PIs: Helen &amp; Marcus)" in doc
    # duplicate copy is highlighted and tagged with the per-person reason
    assert re.search(r'background-color:#fff2cc">Daniel Osei \(PhD 2019; PIs: Helen &amp; Marcus\) — 重复：主导师 Helen 名下已计（Marcus was committee member / mentor）', doc)
    # first and last job bold, middle plain, employer italic
    assert "<b>[2019-21] Postdoctoral Research Fellow, </b><b><i>Northwestern University</i></b>" in doc
    assert "<li>[2021-22] Senior Research Associate, <i>Northwestern University</i></li>" in doc
    assert "<b>[2026-] Associate Professor (with tenure), </b><b><i>Washington University in St. Louis</i></b>" in doc
    # a single job is bold; an empty person gets the bold empty line
    assert "<b>[2016-23] Assistant Professor of Psychology, </b><b><i>University of Toronto</i></b><b> (promotion 2023)</b>" in doc
    assert "<b>[2022-] No placement found publicly (checked Oct 2026)</b>" in doc
    # pending section lists committee by first name, with shared first names disambiguated
    assert "Ana Ruiz (PhD 2026; committee: Jeff M., Jeff N., Susan)" in doc


def test_validator_flags_problems():
    bad = [dict(SAMPLE[0]), {"name": "X Y", "phd_year": 2020, "advisers": ["A B"], "jobs": [], "empty": ""},
           {"name": "P Q", "phd_year": 2020, "advisers": ["A B"],
            "jobs": [{"years": "2020-2021", "title": "T", "employer": "E"}]}]
    errors, warnings = check(bad)
    assert any("X Y" in e and "no jobs" in e for e in errors), errors
    assert any("P Q" in e and "years" in e for e in errors), errors
    errors, warnings = check(SAMPLE)
    assert not errors, errors
    assert any("Jeff" in w for w in warnings), warnings  # shared adviser first name noted


def test_princeton_regression():
    """The generic builder reproduces the Princeton doc HTML byte for byte (when that project exists)."""
    root = os.path.expanduser("~/Claude/Berkeley/PhD placements (Codex)/Princeton English (claude)/research_notes")
    merged, ref = os.path.join(root, "people_merged.json"), os.path.join(root, "gdoc.html")
    if not (os.path.exists(merged) and os.path.exists(ref)):
        print("  (skipped: Princeton project not on this machine)")
        return
    people = []
    for p in json.load(open(merged)):
        people.append({"name": p["name"], "phd_year": p["phd_year"], "advisers": p["advisers"],
                       "committee": p.get("committee_pending") or [],
                       "jobs": [{k: j[k] for k in ("years", "title", "employer", "note")} for j in p["doc_jobs"]],
                       "empty": p.get("doc_empty")})
    intro = open(os.path.join(root, "gdoc_intro.txt")).read().strip()
    doc, _, _ = build(people, intro, pending_note="论文尚未进入普林斯顿论文库，列出答辩委员会")
    # the Princeton build predates the normal-weight heading counts; apply that one change to the reference
    expected = re.sub(r"</b>（(.*?)）</h2>", r'</b><span style="font-weight:normal">（\1）</span></h2>', open(ref).read())
    assert doc == expected, "generic builder output differs from the Princeton gdoc.html"


def test_cli():
    with tempfile.TemporaryDirectory() as d:
        intro = os.path.join(d, "intro.txt")
        open(intro, "w").write("intro")
        out = os.path.join(d, "doc.html")
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "build_gdoc.py"), os.path.join(HERE, "sample_people.json"),
                            "--intro", intro, "--out", out], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert os.path.getsize(out) > 500
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "validate_people.py"), os.path.join(HERE, "sample_people.json")],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr


def test_audit_side_by_side():
    with tempfile.TemporaryDirectory() as d:
        audit = os.path.join(d, "audit.jsonl")
        with open(audit, "w") as f:
            f.write(json.dumps({"name": "D. Osei", "jobs": [
                {"start": 2019, "end": 2021, "title": "Postdoc", "employer": "Northwestern University", "confidence": "high"},
                {"start": 2026, "end": None, "title": "Associate Professor", "employer": "WashU", "confidence": "high"}]}) + "\n")
            f.write(json.dumps({"name": "Nobody Here", "jobs": []}) + "\n")
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "audit_side_by_side.py"), os.path.join(HERE, "sample_people.json"),
                            audit, "--alias", "D. Osei=Daniel Osei"], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert "first: agree" in r.stdout, r.stdout                 # same employer word, same start year
        assert "current: employer differs" in r.stdout, r.stdout     # "WashU" vs "Washington University in St. Louis"
        assert "Nobody Here (NOT IN people.json" in r.stdout


def _readback(heading):
    return ("[**Helen Park（2 人）** **2**](?tab=t.0#heading=h.abc123)\n"
            f"## {heading}\n  - Maya Lindqvist (PhD 2016; PI: Helen)\n  - **\\[2016-\\] Lecturer**\n")


def test_readback_flags_bold_counts():
    """After the Normal->Heading 2 repair, Docs re-bolds the whole heading; the checker must catch it."""
    script = os.path.join(SCRIPTS, "check_readback.py")
    with tempfile.TemporaryDirectory() as d:
        bad, good = os.path.join(d, "bad.md"), os.path.join(d, "good.md")
        open(bad, "w").write(_readback("**Helen Park（2 人）**"))
        open(good, "w").write(_readback("**Helen Park**（2 人）"))
        r = subprocess.run([sys.executable, script, bad, "--people", "1"], capture_output=True, text=True)
        assert r.returncode == 1 and "bold" in r.stdout, r.stdout
        r = subprocess.run([sys.executable, script, good, "--people", "1"], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout


def _fake_rclone(d, existing_id="DOC1", new_id_on_copy=None):
    """A stand-in rclone: lsjson lists one Doc; copyto logs its args (and can simulate a duplicate)."""
    state = os.path.join(d, "state.json")
    json.dump({"docs": [{"Name": "Old Title.html", "ID": existing_id}] if existing_id else []}, open(state, "w"))
    fake = os.path.join(d, "rclone")
    open(fake, "w").write(f"""#!/usr/bin/env python3
import json, sys
st = json.load(open({state!r}))
if sys.argv[1] == "lsjson":
    print(json.dumps(st["docs"]))
elif sys.argv[1] == "copyto":
    open({os.path.join(d, "calls.log")!r}, "a").write(" ".join(sys.argv[1:]) + "\\n")
    name = sys.argv[3].rsplit("/", 1)[-1]
    if {new_id_on_copy!r} or not any(x["Name"] == name for x in st["docs"]):
        st["docs"].append({{"Name": name, "ID": {new_id_on_copy!r} or "NEW9"}})
    json.dump(st, open({state!r}, "w"))
""")
    os.chmod(fake, 0o755)
    return dict(os.environ, PATH=d + os.pathsep + os.environ["PATH"])


def test_upload_replace_mode():
    script = os.path.join(SCRIPTS, "upload_gdoc.sh")
    with tempfile.TemporaryDirectory() as d:
        html = os.path.join(d, "doc.html")
        open(html, "w").write("<html><body><h2>x</h2></body></html>")
        env = _fake_rclone(d)
        # an existing title without --replace: refuse, upload nothing
        r = subprocess.run(["bash", script, html, "remote:Folder", "Old Title"], capture_output=True, text=True, env=env)
        assert r.returncode == 1 and "--replace" in r.stderr, r.stderr
        assert not os.path.exists(os.path.join(d, "calls.log"))
        # --replace: content replaced under the same ID, same link printed
        r = subprocess.run(["bash", script, "--replace", html, "remote:Folder", "Old Title"], capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stdout + r.stderr
        assert r.stdout.strip().endswith("https://docs.google.com/document/d/DOC1/edit"), r.stdout
        assert "--ignore-times" in open(os.path.join(d, "calls.log")).read()
        # --replace on a title that doesn't exist: refuse (nothing to replace)
        r = subprocess.run(["bash", script, "--replace", html, "remote:Folder", "Missing"], capture_output=True, text=True, env=env)
        assert r.returncode == 1, r.stdout
    with tempfile.TemporaryDirectory() as d:
        html = os.path.join(d, "doc.html")
        open(html, "w").write("<html></html>")
        env = _fake_rclone(d, new_id_on_copy="DUP2")   # rclone made a second Doc instead of replacing
        r = subprocess.run(["bash", script, "--replace", html, "remote:Folder", "Old Title"], capture_output=True, text=True, env=env)
        assert r.returncode == 1 and "duplicate" in r.stderr.lower(), r.stdout + r.stderr


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
