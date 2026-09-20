#!/usr/bin/env python3
"""Check that a cloud routine's saved prompt is byte-identical to a local prompt file.

Why: a routine prompt is updated by pasting the whole text into a RemoteTrigger `update` body,
and a single mis-escaped character silently changes what the routine does. After every update,
extract the prompt from the API's own response and compare checksums.

Usage:
  check_routine_prompt.py --scan LOCAL_PROMPT.txt
  check_routine_prompt.py --strip LOCAL_PROMPT.txt
  check_routine_prompt.py RESPONSE TRIGGER_ID LOCAL_PROMPT.txt

--scan is the pre-flight run before a routine is created or updated. It fails on any unexpanded
{{PLACEHOLDER}} and on any <<FILL: ...>> marker, and warns about a trailing newline. A routine
created with either of those in its prompt fires on schedule, delivers nothing useful, and still
reports success.

--strip removes a trailing newline in place. The API strips one on update, so a local snapshot
that ends in "\n" fails the checksum comparison forever. Heredocs and file writes both add one.

RESPONSE is either a saved RemoteTrigger response (a persisted tool-result file: "HTTP 200"
followed by JSON; `get`, `update` and `list` responses all work) or a Claude Code session
transcript (.jsonl), in which case the newest response for TRIGGER_ID in it is used.

Prints the md5 of the local file, of derived_state.prompt, and of the job_config event content.
Exit 0 only if all three match.
"""
import hashlib, json, sys


def md5(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def triggers_in(obj):
    """Yield every trigger object in a RemoteTrigger response."""
    if not isinstance(obj, dict):
        return
    if "trigger" in obj:
        yield obj["trigger"]
    for t in obj.get("data") or []:
        if isinstance(t, dict) and "job_config" in t:
            yield t


def from_text(text):
    i = text.find("{")
    if i < 0:
        return []
    try:
        return list(triggers_in(json.loads(text[i:])))
    except ValueError:
        return []


def event_contents(trig):
    """Yield (label, prompt_text) for every stored copy of the prompt in a trigger object."""
    for ev in (((trig.get("job_config") or {}).get("ccr") or {}).get("events") or []):
        c = (((ev.get("data") or {}).get("message") or {}).get("content"))
        if isinstance(c, str):
            yield "job_cfg", c
    for ev in ((trig.get("session_request") or {}).get("events") or []):
        c = (((ev.get("payload") or {}).get("message") or {}).get("content"))
        if isinstance(c, str):
            yield "sess_req", c


def scan(path):
    """Pre-flight: refuse a prompt that still has placeholders or FILL markers."""
    import re
    text = open(path, encoding="utf-8").read()
    bad = []
    for pat, what in ((r"\{\{[^}]{0,120}\}\}", "unexpanded placeholder"),
                      (r"<<\s*FILL:[^>]{0,200}>>", "unfilled FILL marker")):
        for m in re.finditer(pat, text):
            line = text.count("\n", 0, m.start()) + 1
            bad.append("  line %d: %s  %s" % (line, what, m.group(0)[:90]))
    if text.endswith("\n"):
        print("WARNING: file ends in a newline; the API strips it and the checksum will "
              "never match. Fix with: %s --strip %s" % (sys.argv[0], path))
    if bad:
        print("%s: %d blocker(s) — do NOT create or update the routine:" % (path, len(bad)))
        print("\n".join(bad))
        return 1
    print("%s: clean — no placeholders, no FILL markers." % path)
    return 0


def strip_trailing_newline(path):
    text = open(path, encoding="utf-8").read()
    stripped = text.rstrip("\n")
    if stripped == text:
        print("%s: already has no trailing newline." % path)
        return 0
    open(path, "w", encoding="utf-8").write(stripped)
    print("%s: stripped %d trailing newline(s)." % (path, len(text) - len(stripped)))
    return 0


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--scan":
        sys.exit(scan(sys.argv[2]))
    if len(sys.argv) == 3 and sys.argv[1] == "--strip":
        sys.exit(strip_trailing_newline(sys.argv[2]))
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    path, tid, local = sys.argv[1:]
    found = []
    if path.endswith(".jsonl"):
        for line in open(path, encoding="utf-8"):
            if tid not in line or "derived_state" not in line:
                continue
            try:
                content = json.loads(line).get("message", {}).get("content")
            except ValueError:
                continue
            for c in content if isinstance(content, list) else []:
                if not isinstance(c, dict) or c.get("type") != "tool_result":
                    continue
                parts = c.get("content")
                texts = [p.get("text", "") for p in parts] if isinstance(parts, list) else [parts or ""]
                for t in texts:
                    found += [x for x in from_text(t) if x.get("id") == tid]
    else:
        found = [x for x in from_text(open(path, encoding="utf-8").read()) if x.get("id") == tid]
    if not found:
        sys.exit("no response for %s in %s" % (tid, path))
    trig = found[-1]
    want = md5(open(local, encoding="utf-8").read())
    print("updated_at", trig.get("updated_at"))
    print("local    ", want)

    hashes = [want]
    derived = (trig.get("derived_state") or {}).get("prompt")
    if derived is not None:
        print("derived  ", md5(derived)); hashes.append(md5(derived))
    else:
        print("derived   (absent in this response)")

    # The stored routine comes back in two shapes depending on the call and how it was written:
    #   job_config.ccr.events[].data.message.content        (create/update form)
    #   session_request.events[].payload.message.content    (what list/get often return)
    # Check every copy present; a mismatch between them is exactly the corruption we are hunting.
    for label, content in event_contents(trig):
        print("%-9s" % label, md5(content)); hashes.append(md5(content))

    if len(hashes) == 1:
        sys.exit("found the trigger but no stored prompt in it — wrong response shape?")
    ok = len(set(hashes)) == 1
    print("MATCH" if ok else "MISMATCH — do not trust the live prompt")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
