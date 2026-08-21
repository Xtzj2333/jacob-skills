#!/usr/bin/env python3
"""Summarise the restore-focus trial: did the extension ever actually steal focus?

    python3 focus-log-report.py

Reads ~/.claude/chrome-tab-focus.log and answers the one question the trial
exists to answer. For every RESTORED it also looks at what *else* was going on
in the minutes before — which sessions were browsing, and whether any session
ran something that drives app focus (AppleScript `activate`, `open -a`,
`macdrive`, `chrome-tab open`, a screen-recorder...). A RESTORED is only
evidence if nothing else could have moved focus.

Background: on 2026-08-15 the claim "browser automation steals focus" was
retracted — on a quiet machine no browser operation moved focus at all, and the
earlier readings turned out to be contaminated by the user using Chrome at the same
time. The hooks were installed as an instrument rather than a fix. The first
RESTORED after that (16 Aug 17:40) looked like the answer and was not: a second
session was running a screen-recorder that had activated Terminal 96 s before
the snapshot and drove Finder/Terminal/Claude focus for the next three minutes,
while the user was pasting into a web form in Chrome by hand. Hence the confounder check —
a log line alone cannot carry the verdict.
"""

import collections
import datetime
import json
import pathlib
import re
import sys
import time

LOG = pathlib.Path.home() / ".claude" / "chrome-tab-focus.log"
PROJECTS = pathlib.Path.home() / ".claude" / "projects"
REMOVE = 'python3 "$HOME/.claude/skills/chrome-tab/scripts/install-focus-hook.py" --remove'
LOOKBACK = 2 * 60  # seconds before the burst's SNAPSHOT to inspect (window runs to the RESTORED)

# Anything in a Bash command that can move app focus on macOS.
FOCUS_DRIVERS = re.compile(
    r"\bactivate\b|open -a\b|open -b\b|osascript|tell application|macdrive|"
    r"chrome-tab open|record\.sh|screencapture|\bopen +\S+\.(html?|pdf)\b",
    re.I,
)


def local_epoch(ts):
    """'2026-08-16 17:40:03' (local, as the hook writes it) -> epoch seconds."""
    return time.mktime(time.strptime(ts, "%Y-%m-%d %H:%M:%S"))


def utc_prefixes(t0, t1):
    """Minute prefixes 'YYYY-MM-DDTHH:MM' covering [t0, t1] in UTC, for a cheap substring pre-filter."""
    out, t = [], t0 - (t0 % 60)
    while t <= t1:
        out.append(datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M"))
        t += 60
    return out


def iso_epoch(ts):
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def context_for(snapshot_epoch, restored_epoch):
    """What every session was doing from shortly before the snapshot up to the RESTORED."""
    t0, t1 = snapshot_epoch - LOOKBACK, restored_epoch + 5
    prefixes = ['"timestamp":"' + p for p in utc_prefixes(t0, t1)]
    browsing, drivers, sessions = [], [], set()
    for f in PROJECTS.glob("*/*.jsonl"):
        try:
            if f.stat().st_mtime < t0:
                continue
            with f.open(errors="ignore") as fh:
                for line in fh:
                    if '"tool_use"' not in line or not any(p in line for p in prefixes):
                        continue
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    ts = d.get("timestamp")
                    if not ts:
                        continue
                    t = iso_epoch(ts)
                    if not (t0 <= t <= t1):
                        continue
                    msg = d.get("message") or {}
                    for c in (msg.get("content") or []) if isinstance(msg, dict) else []:
                        if not isinstance(c, dict) or c.get("type") != "tool_use":
                            continue
                        sid = f.stem[:8]
                        when = time.strftime("%H:%M:%S", time.localtime(t))
                        name = c.get("name", "")
                        inp = c.get("input") or {}
                        if name.startswith("mcp__claude-in-chrome__"):
                            sessions.add(sid)
                            browsing.append((when, sid, name.replace("mcp__claude-in-chrome__", "")))
                        elif name == "Bash":
                            cmd = inp.get("command", "")
                            m = FOCUS_DRIVERS.search(cmd)
                            if m:
                                sessions.add(sid)
                                first = cmd.strip().splitlines()[0] if cmd.strip() else ""
                                drivers.append((when, sid, m.group(0), first[:110]))
        except Exception:
            continue
    return sorted(browsing), sorted(drivers), sessions


def main():
    if not LOG.exists():
        print("No log yet — the hooks have not run, or no session has browsed since install.")
        print(f"Expected at: {LOG}")
        return

    lines = [l.rstrip("\n") for l in LOG.read_text().splitlines() if l.strip()]
    kinds = collections.Counter()
    restored, reasons, first, last = [], collections.Counter(), None, None
    last_snapshot = None
    measurable = 0  # bursts where the user was NOT already in Chrome — the only ones that can show a steal
    for l in lines:
        m = re.match(r"(\S+ \S+)\s+(\S+)\s+(.*)", l)
        if not m:
            continue
        ts, kind, rest = m.groups()
        first = first or ts
        last = ts
        kinds[kind] += 1
        if kind == "snapshot":
            last_snapshot = ts
            if "Google Chrome" not in rest:
                measurable += 1
        if kind == "RESTORED":
            restored.append((last_snapshot or ts, ts, l))
        elif kind == "skipped":
            reasons[rest] += 1

    span = f"{first} → {last}" if first else "—"
    print(f"restore-focus trial · {span}")
    print(f"  browsing bursts seen : {kinds.get('snapshot', 0)}"
          f"   (measurable — user not already in Chrome: {measurable})")
    print(f"  end-of-turn decisions: {kinds.get('skipped', 0) + kinds.get('RESTORED', 0)}"
          f"   (+{kinds.get('discarded', 0)} discarded as stale)")
    print(f"  RESTORED             : {kinds.get('RESTORED', 0)}")
    if kinds.get("error"):
        print(f"  errors               : {kinds['error']}  (grep the log)")
    if kinds.get("chrome-tab"):
        print(f"  chrome-tab self-reports: {kinds['chrome-tab']}  (chrome-tab measured its own call moving focus — "
              f"a chrome-tab bug, not the extension; the add-tab path did this until 2026-08-20)")

    if reasons:
        print("\n  why it stood down:")
        for r, n in reasons.most_common():
            print(f"    {n:4}  {r}")

    print()
    if not kinds.get("snapshot"):
        print("VERDICT: inconclusive — no browsing recorded yet, so the instrument")
        print("has had nothing to measure. Leave it until Claude has browsed a few times.")
        return

    if not restored:
        print(f"VERDICT: no steal observed across {kinds['snapshot']} browsing bursts, "
              f"{measurable} of which could have shown one.")
        if measurable < 5:
            print("That is thin evidence — most bursts happened while the user was already in Chrome,")
            print("where a steal is invisible. Leave the hooks in, or run a controlled test.")
        else:
            print("Cause ③ does not reproduce on this Mac. Safe to take the hooks out:")
            print(f"  {REMOVE}")
        return

    print(f"{len(restored)} RESTORED line(s). Each is a CANDIDATE, not a verdict — it means focus was in")
    print("Chrome at end of turn and had not been when browsing began. Below, what else was happening")
    print(f"from {LOOKBACK // 60} min before the burst's snapshot until the restore:\n")
    clean = 0
    for snap_ts, ts, l in restored:
        print(f"  {l}")
        print(f"    (snapshot taken {snap_ts})")
        browsing, drivers, sessions = context_for(local_epoch(snap_ts), local_epoch(ts))
        bsids = {s for _, s, _ in browsing}
        others = [d for d in drivers if d[1] not in bsids]
        if browsing:
            ops = collections.Counter(n for _, _, n in browsing)
            print(f"    browsing session(s) {sorted(bsids)}: " + ", ".join(f"{n}×{k}" for k, n in ops.most_common()))
        else:
            print("    no browser calls found in any transcript for this window (transcript moved or pruned?)")
        for when, sid, hit, cmd in drivers:
            tag = "SAME session" if sid in bsids else "OTHER session"
            print(f"    {when}  {sid}  [{tag}] focus-driving command ({hit}): {cmd}")
        if any(h == "chrome-tab open" for _, _, h, _ in drivers) and ts < "2026-08-20 16:44":
            print("    → LIKELY CAUSE: chrome-tab open ran in this window, and before 2026-08-20 16:44 its")
            print("      add-tab path raised Chrome and never restored it (Chrome's `set URL` activates twice).")
            print("      Fixed that day; treat this as a chrome-tab steal, not an extension one.")
        elif others:
            print("    → CONFOUNDED: another session was driving app focus. Not admissible.")
        elif drivers:
            print("    → AMBIGUOUS: the browsing session itself ran a focus-driving command; the")
            print("      extension may not be what moved focus.")
        else:
            clean += 1
            print("    → UNCONFOUNDED candidate. Still cannot exclude the user switching to Chrome by")
            print("      hand; ask whether they were bounced out of Chrome at this time.")
        print()

    if clean:
        print(f"VERDICT: {clean} unconfounded candidate(s). Ask the user about each timestamp; if they were")
        print("NOT in Chrome by choice, the steal is real and the 2026-08-15 retraction was premature.")
    else:
        print("VERDICT: every RESTORED so far is confounded or ambiguous — no admissible evidence of")
        print(f"a steal across {measurable} measurable bursts. The trial continues; nothing to act on.")


if __name__ == "__main__":
    sys.exit(main())
