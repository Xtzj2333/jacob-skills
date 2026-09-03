#!/opt/anaconda3/bin/python3
"""Focus experiment 3 (2026-09-03): idle-gated, exercises the REAL fixed chrome-tab.

Waits until the user has been idle >= IDLE_NEEDED seconds (so macOS will honour
app activations, as on 2026-08-20), then:
  E1 put Slack in front (the 2026-08-20 condition)
  E2 raw `make new window` + set URL, no restore     -> does Chrome come forward?
  E3 raw add-tab with URL, no restore                -> does Chrome come forward?
  E4 real `chrome-tab open` (new tab)                -> spans + tool's own report
  E5 real `chrome-tab open` again (reload path)      -> spans
  E6 minimized scratch window + real chrome-tab open -> stays minimized?
  E7 Chrome in front, other window on top + real open-> window order / active tab kept?
  E8 close scratch, return to the app that was in front
Aborts (and restores) if the idle clock drops — i.e. the user came back.
"""
import os
import subprocess
import sys
import threading
import time

from AppKit import NSWorkspace

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = "file://" + os.path.join(HERE, "focus-test.html")
LOGP = os.path.join(HERE, "focus-experiment3.log")
LOG = open(LOGP, "a")
T0 = time.perf_counter()
SLACK = "com.tinyspeck.slackmacgap"
CHROME = "com.google.Chrome"
IDLE_NEEDED = int(os.environ.get("IDLE_NEEDED", "240"))
MAX_WAIT = int(os.environ.get("MAX_WAIT", str(150 * 60)))
CHROME_TAB = os.path.expanduser("~/.claude/skills/chrome-tab/scripts/chrome-tab")


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} +{(time.perf_counter()-T0):8.3f}s  {msg}"
    LOG.write(line + "\n"); LOG.flush()
    print(line, flush=True)


def front():
    a = NSWorkspace.sharedWorkspace().frontmostApplication()
    if a is None:
        return (None, None, None)
    return (a.localizedName(), a.bundleIdentifier(), a.processIdentifier())


def idle():
    out = subprocess.run("ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}'",
                         shell=True, capture_output=True, text=True).stdout.strip()
    return int(out) if out.isdigit() else -1


def osa(script, *args):
    p = subprocess.run(["osascript", "-", *map(str, args)], input=script, capture_output=True, text=True)
    return (p.returncode, p.stdout.strip(), p.stderr.strip())


def bring(bid, timeout=4.0):
    subprocess.run(["open", "-b", bid], capture_output=True)
    t = time.perf_counter()
    while time.perf_counter() - t < timeout:
        if front()[1] == bid:
            return True
        time.sleep(0.02)
    return False


CREATE = '''
on run argv
  tell application "Google Chrome"
    set w to make new window
    set given name of w to item 1 of argv
    set URL of active tab of w to item 2 of argv
    return id of w as text
  end tell
end run
'''
ADD = '''
on run argv
  tell application "Google Chrome"
    repeat with ww in windows
      if (id of ww as text) is item 1 of argv then
        make new tab at end of tabs of ww with properties {URL:item 2 of argv}
        return "added"
      end if
    end repeat
    return "nowindow"
  end tell
end run
'''
FRONTWIN = 'tell application "Google Chrome" to if (count of windows) > 0 then return id of front window'
RAISE = '''
on run argv
  tell application "Google Chrome"
    repeat with ww in windows
      if (id of ww as text) is item 1 of argv then
        set index of ww to 1
        return "ok"
      end if
    end repeat
  end tell
end run
'''
MINIMIZE = '''
on run argv
  tell application "Google Chrome"
    repeat with ww in windows
      if (id of ww as text) is item 1 of argv then
        set minimized of ww to (item 2 of argv is "1")
        return "ok"
      end if
    end repeat
  end tell
end run
'''
WINSTATE = '''
on run argv
  tell application "Google Chrome"
    repeat with ww in windows
      if (id of ww as text) is item 1 of argv then
        return "active=" & (active tab index of ww as text) & " tabs=" & ((count of tabs of ww) as text) & " minimized=" & (minimized of ww as text) & " index=" & (index of ww as text)
      end if
    end repeat
    return "gone"
  end tell
end run
'''
CLOSE = '''
on run argv
  tell application "Google Chrome"
    repeat with ww in windows
      if (id of ww as text) is item 1 of argv then
        close ww
        return "closed"
      end if
    end repeat
  end tell
end run
'''


class Watcher(threading.Thread):
    """Observe only: log every front-app change, measure how long Chrome held it."""

    def __init__(self, label, dur, step=0.002):
        super().__init__(daemon=True)
        self.label, self.dur, self.step = label, dur, step
        self.spans = []

    def run(self):
        t0 = time.perf_counter(); last = None; since = None
        while True:
            now = time.perf_counter() - t0
            name, bid, _ = front()
            if bid != last:
                log(f"  [{self.label}] +{now*1000:7.1f} ms  front={name}")
                if bid == CHROME:
                    since = now
                elif since is not None:
                    self.spans.append((since, now)); since = None
                last = bid
            if now >= self.dur:
                break
            time.sleep(self.step)
        if since is not None:
            self.spans.append((since, self.dur))

    def summary(self):
        sp = ", ".join(f"{(b-a)*1000:.0f} ms (at +{a*1000:.0f})" for a, b in self.spans)
        return f"chrome-front spans: {len(self.spans)} [{sp or 'none'}]"


def chrome_tab(*args):
    p = subprocess.run([CHROME_TAB, "open", *args], capture_output=True, text=True)
    out = (p.stdout + p.stderr).strip().replace("\n", " | ")
    return f"rc={p.returncode} {out}"


def main():
    # --- gate: wait for the user to be away --------------------------------
    t_start = time.time()
    log(f"WAITING for idle >= {IDLE_NEEDED}s (max {MAX_WAIT//60} min); idle now {idle()}s front={front()[0]}")
    while True:
        i = idle()
        f = front()[1]
        if i >= IDLE_NEEDED and f not in (None, "com.apple.loginwindow", "com.apple.ScreenSaver.Engine"):
            break
        if time.time() - t_start > MAX_WAIT:
            log("GAVE UP: user never idle long enough"); return 4
        time.sleep(5)
    base_idle = idle()
    name, bid, pid = front()
    log(f"START idle={base_idle}s front={name} ({bid})")
    orig_bid = bid
    rc, prev_front_win, err = osa(FRONTWIN)
    log(f"Chrome front window before: {prev_front_win}")

    def check(label):
        i = idle()
        if i < base_idle:
            log(f"ABORT at {label}: idle dropped to {i}s — user is back")
            return False
        return True

    def settle(label):
        for _ in range(30):
            if front()[1] == SLACK:
                break
            subprocess.run(["open", "-b", SLACK], capture_output=True); time.sleep(0.15)
        log(f"  settle after {label}: front={front()[0]} idle={idle()}s chromefront={osa(FRONTWIN)[1]}")
        time.sleep(1.2)

    ok = bring(SLACK)
    log(f"E1 Slack in front: {ok} (front={front()[0]}) idle={idle()}s")
    if not ok or not check("E1"):
        bring(orig_bid); return 2
    time.sleep(1.0)

    w = Watcher("E2 raw create", 2.5); w.start()
    rc, wid, err = osa(CREATE, "focus-test-scratch", PAGE + "?e2"); log(f"E2 create returned {wid!r} {err}")
    w.join(); log(f"E2 {w.summary()}"); settle("E2")
    if not wid.isdigit() or not check("E2"):
        bring(orig_bid); return 3

    w = Watcher("E3 raw add", 2.5); w.start()
    osa(ADD, wid, PAGE + "?e3"); w.join(); log(f"E3 {w.summary()}"); settle("E3")
    if not check("E3"): bring(orig_bid); return 5

    w = Watcher("E4 chrome-tab new tab", 3.5); w.start()
    r = chrome_tab(PAGE + "?e4", "--window", "focus-test-scratch"); w.join()
    log(f"E4 tool: {r}"); log(f"E4 {w.summary()}"); settle("E4")
    if not check("E4"): bring(orig_bid); return 5

    w = Watcher("E5 chrome-tab reload", 3.5); w.start()
    r = chrome_tab(PAGE + "?e4", "--window", "focus-test-scratch"); w.join()
    log(f"E5 tool: {r}"); log(f"E5 {w.summary()}"); settle("E5")
    if not check("E5"): bring(orig_bid); return 5

    osa(MINIMIZE, wid, "1"); time.sleep(1.0)
    log(f"E6 before: {osa(WINSTATE, wid)[1]}")
    w = Watcher("E6 chrome-tab into minimized", 3.5); w.start()
    r = chrome_tab(PAGE + "?e6", "--window", "focus-test-scratch"); w.join()
    log(f"E6 tool: {r}"); log(f"E6 {w.summary()}"); log(f"E6 after: {osa(WINSTATE, wid)[1]}")
    settle("E6")
    osa(MINIMIZE, wid, "0"); time.sleep(0.8)
    if not check("E6"): bring(orig_bid); return 5

    osa(RAISE, prev_front_win)
    ok = bring(CHROME); time.sleep(0.8)
    log(f"E7 Chrome in front: {ok} chromefront={osa(FRONTWIN)[1]} (prev={prev_front_win}) scratch: {osa(WINSTATE, wid)[1]}")
    r = chrome_tab(PAGE + "?e7", "--window", "focus-test-scratch")
    log(f"E7 tool: {r}")
    log(f"E7 after: chromefront={osa(FRONTWIN)[1]} scratch: {osa(WINSTATE, wid)[1]} front={front()[0]}")
    time.sleep(1.0)
    log(f"E7 +1s: chromefront={osa(FRONTWIN)[1]} scratch: {osa(WINSTATE, wid)[1]} front={front()[0]}")
    osa(RAISE, prev_front_win)

    log(f"E8 close: {osa(CLOSE, wid)[1]}")
    osa(RAISE, prev_front_win)
    ok = bring(orig_bid)
    log(f"END back to {orig_bid}: {ok} front={front()[0]} idle={idle()}s chromefront={osa(FRONTWIN)[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
