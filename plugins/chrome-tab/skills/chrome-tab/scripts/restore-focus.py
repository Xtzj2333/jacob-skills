#!/usr/bin/env python3
"""Put focus back where it was after Claude drives the Chrome extension.

Written on the theory that the Claude-in-Chrome extension activates Chrome when
Claude browses. Two controlled runs (2026-08-15, 2026-08-20) found that it does
not — every operation it offers, with the user idle, left the front app alone.
The one steal this hook ever caught (2026-08-16) was `chrome-tab` itself, since
fixed. It stays as an instrument: anything that pulls the user into Chrome
during a browsing turn gets logged, judged by focus-log-report.py, and undone.

Two halves, wired to two hook events:

    --snapshot   PreToolUse on mcp__claude-in-chrome__.*   record where you were
    --restore    Stop                                       put you back

Snapshot records the frontmost app, Chrome's front window and active tab, and
the full list of Chrome window ids. Only the FIRST browser call of a turn
snapshots; later calls see a snapshot already pending and leave it alone, so
what gets restored is where you were before the burst — not where the extension
put you halfway through it.

The restore is deliberately timid. It only fires when it can prove the extension
is what moved you, and does nothing at all when you appear to have moved
yourself. See `safe_to_restore` for the exact test — that conservatism is the
whole design: a restore that occasionally does nothing is a minor annoyance, one
that yanks you out of a window you chose is a bug you would not forgive.

Reads the hook payload on stdin (for session_id); always exits 0 so it can never
interfere with a turn.
"""

import json
import os
import pathlib
import re
import subprocess
import sys
import time

STATE_DIR = pathlib.Path.home() / ".claude" / ".chrome-tab-focus"
LOG = pathlib.Path.home() / ".claude" / "chrome-tab-focus.log"
STALE_AFTER = 20 * 60  # a snapshot older than this is discarded unused
# How recently must Claude have actually browsed for a focus change to be
# blamed on it? Learned the hard way: the first real firing, 2026-08-15 21:47,
# restored a snapshot taken 1198 s earlier — two seconds inside the staleness
# window. Twenty minutes is ample time for the user to have walked into Chrome
# himself, so that "evidence" proved nothing and may have yanked him out of a
# window he chose. If the last browser call was minutes ago, it is not what
# moved him.
RECENT_CALL = 120


def log(msg):
    """Append one line to the log.

    This has to be a file, not stderr. A hook that exits 0 has its stderr
    discarded by the harness, so the whole point of running this as an
    instrument — finding out whether the focus steal ever actually happens —
    would produce nothing anyone could read afterwards. `tail` the file instead.
    """
    try:
        with LOG.open("a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}\n")
    except Exception:
        pass
    if os.environ.get("CHROME_TAB_FOCUS_DEBUG"):
        print(f"[restore-focus] {msg}", file=sys.stderr)


def osa(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def front_app():
    """(name, bundleid) of the frontmost app. lsappinfo needs no Accessibility grant."""
    try:
        asn = subprocess.run(["lsappinfo", "front"], capture_output=True, text=True).stdout.strip()
        if not asn:
            return (None, None)
        out = subprocess.run(
            ["lsappinfo", "info", "-only", "name,bundleid", asn], capture_output=True, text=True
        ).stdout
        name = bid = None
        m = re.search(r'"LSDisplayName"="([^"]*)"', out)
        if m:
            name = m.group(1)
        m = re.search(r'"CFBundleIdentifier"="([^"]*)"', out)
        if m:
            bid = m.group(1)
        return (name, bid)
    except Exception:
        return (None, None)


CHROME_STATE = '''tell application "Google Chrome"
  if (count of windows) is 0 then return "none"
  set ids to ""
  repeat with w in windows
    set ids to ids & (id of w) & ","
  end repeat
  return (id of front window) & "|" & (active tab index of front window) & "|" & ids
end tell'''


def chrome_state():
    """(front_window_id, active_tab_index, [all window ids]) or None if Chrome has no windows."""
    out = osa(CHROME_STATE)
    if not out or out == "none":
        return None
    try:
        fid, idx, ids = out.split("|")
        return (int(fid), int(idx), [int(i) for i in ids.strip(",").split(",") if i])
    except (ValueError, IndexError):
        return None


def state_file(payload):
    sid = str(payload.get("session_id") or os.getppid())
    sid = "".join(c for c in sid if c.isalnum() or c in "-_")[:80]
    return STATE_DIR / f"{sid}.json"


# ---------------------------------------------------------------- snapshot


def snapshot(payload):
    f = state_file(payload)
    now = time.time()
    # Already pending? Then this is a later call in the same burst. Keep the
    # position — it is the one taken before the extension moved anything — but
    # refresh `last_call`, so the restore knows how recently browsing happened.
    if f.exists():
        try:
            data = json.loads(f.read_text())
        except Exception:
            data = None
        if data and now - data.get("ts", 0) < STALE_AFTER:
            data["last_call"] = now
            f.write_text(json.dumps(data))
            return
    name, bid = front_app()
    ch = chrome_state()
    data = {
        "ts": now,
        "last_call": now,
        "app_name": name,
        "app_bid": bid,
        "chrome_front": ch[0] if ch else None,
        "chrome_tab": ch[1] if ch else None,
        "windows": ch[2] if ch else [],
    }
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data))
    log(f"snapshot   you were in {name}")


# ---------------------------------------------------------------- restore


def safe_to_restore(snap, now_app_bid, ch):
    """Restore only on the one signal that measures reliably: the app switch.

    Returns (do_it, reason).

    The first version of this tested Chrome's *window* order too — "if a window
    id appears that wasn't there before the burst, that's the extension's, so
    it's safe to act". Measured 2026-08-15, that test does not work: Chrome's
    AppleScript window order does not update when a window is created (a
    freshly-made window reported `index` 58 and never became `front window`),
    so the check silently never fired. App-level frontmost, read via
    `lsappinfo`, does track reality — so that is the whole trigger now.

    The cost of dropping window-level detection is the one ambiguity that has no
    clean answer: if you switch to Chrome *yourself* while Claude is browsing,
    this cannot tell that apart from the extension pulling you there, and it
    will put you back. That case is the residual risk; `--remove` undoes it.
    """
    if now_app_bid != "com.google.Chrome":
        # You are already somewhere else — either you never got pulled, or you
        # pulled yourself back. Either way there is nothing to undo.
        return (False, "you are not in Chrome")

    if snap.get("app_bid") == "com.google.Chrome":
        # You were in Chrome before Claude browsed, so no app switch happened
        # and there is nothing to reverse.
        return (False, "you were already in Chrome when Claude started")

    if not snap.get("app_bid"):
        return (False, "no app recorded to go back to")

    return (True, f"Chrome is front but you were in {snap.get('app_name')}")


def reap_stale():
    """Delete other sessions' snapshots that can never be used.

    A session that browses and then dies, compacts, or is killed mid-turn never
    reaches its Stop hook, so its snapshot sits in STATE_DIR for ever. That is
    harmless for correctness (it would be discarded as stale if ever read) but
    not for cost: restore-focus.sh's fast path only skips Python when the
    directory is EMPTY, so one orphan makes every turn of every session pay the
    ~40 ms Python start. Seen 2026-08-20: two orphans from 16 Aug, four days old.
    """
    try:
        now = time.time()
        for g in STATE_DIR.glob("*.json"):
            try:
                if now - g.stat().st_mtime > STALE_AFTER:
                    g.unlink()
            except FileNotFoundError:
                pass
    except Exception:
        pass


def restore(payload):
    reap_stale()
    f = state_file(payload)
    if not f.exists():
        return
    try:
        snap = json.loads(f.read_text())
    except Exception:
        f.unlink(missing_ok=True)
        return
    f.unlink(missing_ok=True)

    age = time.time() - snap.get("ts", 0)
    if age > STALE_AFTER:
        # Logged rather than silent: without this line a burst that ends in a
        # long turn simply vanishes from the record, and the report under-counts
        # how often the instrument had nothing to say.
        log(f"discarded  snapshot was {age/60:.0f} min old when the turn ended — too old to use")
        return

    # The decisive guard. Without it, a snapshot taken at the start of a long
    # turn gets cashed in twenty minutes later against a focus change that had
    # nothing to do with Claude.
    since = time.time() - snap.get("last_call", snap.get("ts", 0))
    if since > RECENT_CALL:
        log(f"skipped    last browser call was {since/60:.1f} min ago — too stale to blame")
        return

    name, bid = front_app()
    ch = chrome_state()
    ok, reason = safe_to_restore(snap, bid, ch)
    if not ok:
        log(f"skipped    {reason}")
        return

    # Put Chrome's window order back first, so that if the app switch below is
    # what the user notices, the window underneath is already the right one.
    wid = snap.get("chrome_front")
    tab = snap.get("chrome_tab")
    if wid:
        osa(f'''tell application "Google Chrome"
  try
    set w to (first window whose id is {int(wid)})
    set index of w to 1
    if {int(tab or 0)} > 0 and {int(tab or 0)} <= (count of tabs of w) then
      set active tab index of w to {int(tab)}
    end if
  end try
end tell''')

    # Then the app itself — unless you were in Chrome anyway, in which case
    # raising the window above was the whole job.
    if snap.get("app_bid") and snap["app_bid"] != "com.google.Chrome":
        subprocess.run(["open", "-b", snap["app_bid"]], capture_output=True)

    log(f"RESTORED   pulled back to {snap.get('app_name')} / window {wid} tab {tab} "
        f"— the extension DID steal focus")

    # Escalate into the session's context. A Stop hook that exits 0 has its
    # STDOUT handed to Claude, so this is how a restore reaches a human without
    # anyone remembering to read a log file: whichever session it happens in,
    # that Claude sees the line and can raise it. Deliberately only on RESTORED
    # — this is the rare, load-bearing event. Skips stay in the log.
    print(
        f"[chrome-tab restore-focus] Focus was in Chrome at end of turn but the user was in "
        f"{snap.get('app_name')} when Claude started browsing, so it was put back there. This is "
        f"a CANDIDATE focus steal for the restore-focus trial — not yet a verdict: the "
        f"first candidate (16 Aug 17:40) turned out to be confounded by another session driving "
        f"app focus. Run  python3 ~/.claude/skills/chrome-tab/scripts/focus-log-report.py  which "
        f"checks what else was touching focus at the time, then tell him what it says."
    )


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {}

    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if mode == "--snapshot":
            snapshot(payload)
        elif mode == "--restore":
            restore(payload)
    except Exception as e:  # never let a focus helper break a turn
        log(f"error      {e}")
    sys.exit(0)


if __name__ == "__main__":
    main()
