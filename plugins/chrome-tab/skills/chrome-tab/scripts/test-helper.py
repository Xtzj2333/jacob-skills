#!/usr/bin/env python3
"""Tests for the chrome-tab helper: the native-messaging host, and the extension end to end.

Part 1 (always runs; no browser): the host is started with pipes standing in for Chrome.
The test plays the extension on the host's stdin/stdout and plays chrome-tab on its
socket, through chrome-tab's own client code:
  * requests are relayed in native-messaging framing and replies routed back by id;
  * `host` is answered by the host itself and names its parent process as Chrome;
  * a request the extension never answers times out with a clear error;
  * the socket is 0600 inside a 0700 directory;
  * when Chrome hangs up, the host exits and removes its socket;
  * a stale socket file is replaced; a live one makes a second host wait, then take over.

Part 2 (runs when Chrome for Testing is available): a throwaway headless Chrome for Testing
with its own profile loads the real extension, installed by `chrome-tab helper install`
into scratch directories. Chrome starts the real host. Then open / reuse / group /
createWindow / tab / move are exercised against real tabs. It never touches the user's
Chrome: every AppleScript path is disabled for the run (CHROME_TAB_NO_APPLESCRIPT=1), and
Chrome for Testing is a separate app that `tell application "Google Chrome"` doesn't reach.
Point CHROME_TAB_TEST_BROWSER at the "Google Chrome for Testing" binary, or install one with
`npx @puppeteer/browsers install chrome@stable --path ~/.cache/chrome-tab-test`, where both
end-to-end suites find it without the variable.

Run:  python3 scripts/test-helper.py
"""
import importlib.machinery
import importlib.util
import json
import os
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "chrome-tab"
HOST = HERE.parent / "helper" / "chrome_tab_host.py"


def load():
    loader = importlib.machinery.SourceFileLoader("chrome_tab_helper_under_test", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


ct = load()


def short_tmp():
    # AF_UNIX paths are limited to 104 bytes on macOS; $TMPDIR is long.
    return Path(tempfile.mkdtemp(prefix="ctt-", dir="/tmp"))


def wait_for(pred, timeout, step=0.1):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        v = pred()
        if v:
            return v
        time.sleep(step)
    return pred()


class FakeChrome:
    """Starts the host the way Chrome does, and speaks for the extension."""

    def __init__(self, sock):
        self.sock = sock
        self.proc = subprocess.Popen(
            [sys.executable, str(HOST), "chrome-extension://test/"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=dict(os.environ, CHROME_TAB_SOCKET=str(sock)))

    def send(self, msg):
        data = json.dumps(msg).encode()
        self.proc.stdin.write(struct.pack("@I", len(data)) + data)
        self.proc.stdin.flush()

    def recv(self):
        head = self.proc.stdout.read(4)
        (n,) = struct.unpack("@I", head)
        return json.loads(self.proc.stdout.read(n))

    def hang_up(self):
        self.proc.stdin.close()
        return self.proc.wait(timeout=5)

    def kill(self):
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=5)
        for f in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            try:
                f.close()
            except Exception:
                pass


class HostRelay(unittest.TestCase):
    def setUp(self):
        self.dir = short_tmp()
        self.sock = self.dir / "run" / "bridge.sock"
        os.environ["CHROME_TAB_SOCKET"] = str(self.sock)
        self.chrome = FakeChrome(self.sock)
        self.chrome.send({"type": "hello", "version": "9.9.9", "extensionId": "test"})
        self.assertTrue(wait_for(self.sock.exists, 5), "host never bound its socket")

    def tearDown(self):
        self.chrome.kill()
        os.environ.pop("CHROME_TAB_SOCKET", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def call_in_thread(self, *a, **kw):
        import threading
        box = {}

        def run():
            try:
                box["result"] = ct.helper_call(*a, **kw)
            except Exception as e:  # noqa: BLE001
                box["error"] = e
        t = threading.Thread(target=run)
        t.start()
        return t, box

    def test_relays_a_request_and_routes_the_reply(self):
        t, box = self.call_in_thread("windows", timeout=5, x=1)
        req = self.chrome.recv()
        self.assertEqual((req["cmd"], req["args"]), ("windows", {"x": 1}))
        self.chrome.send({"id": req["id"], "ok": True, "result": [{"id": 7}]})
        t.join(5)
        self.assertEqual(box.get("result"), [{"id": 7}])

    def test_extension_error_becomes_helper_error(self):
        t, box = self.call_in_thread("open", timeout=5)
        req = self.chrome.recv()
        self.chrome.send({"id": req["id"], "ok": False, "error": "No window with id: 5."})
        t.join(5)
        self.assertIsInstance(box.get("error"), ct.HelperError)
        self.assertIn("No window with id", str(box["error"]))

    def test_host_answers_host_itself(self):
        info = ct.helper_call("host", timeout=2)
        self.assertEqual(info["chrome_pid"], os.getpid())      # our test process launched it
        self.assertEqual(info["pid"], self.chrome.proc.pid)
        self.assertEqual(info["extension"]["version"], "9.9.9")

    def test_unanswered_request_times_out(self):
        with self.assertRaises(ct.HelperError) as cm:
            ct.helper_call("ping", timeout=0.5)
        self.assertIn("did not answer", str(cm.exception))

    def test_socket_is_private(self):
        self.assertEqual(stat.S_IMODE(self.sock.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.sock.parent.stat().st_mode), 0o700)

    def test_hang_up_exits_and_removes_socket(self):
        self.assertEqual(self.chrome.hang_up(), 0)
        self.assertFalse(self.sock.exists())
        self.assertIsNone(ct.helper_call("host", timeout=1))   # "not running", not an error

    def test_second_host_waits_then_takes_over(self):
        second = FakeChrome(self.sock)
        try:
            time.sleep(1.5)
            self.assertEqual(ct.helper_call("host", timeout=2)["pid"], self.chrome.proc.pid)
            self.chrome.hang_up()
            took = wait_for(lambda: (ct.helper_call("host", timeout=1) or {}).get("pid") == second.proc.pid, 5)
            self.assertTrue(took, "the waiting host never took over")
        finally:
            second.kill()

    def test_stale_socket_is_replaced(self):
        self.chrome.kill()                       # dies without cleaning up
        self.assertTrue(self.sock.exists())
        fresh = FakeChrome(self.sock)
        try:
            ok = wait_for(lambda: (ct.helper_call("host", timeout=1) or {}).get("pid") == fresh.proc.pid, 5)
            self.assertTrue(ok)
        finally:
            fresh.kill()


def find_test_browser():
    env = os.environ.get("CHROME_TAB_TEST_BROWSER")
    if env and Path(env).exists():
        return env
    for root in [Path.home() / ".cache" / "chrome-tab-test", Path.home() / ".cache" / "puppeteer"]:
        for c in sorted(root.glob("**/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")):
            return str(c)
    return None


BROWSER = find_test_browser()


@unittest.skipUnless(BROWSER, "Chrome for Testing not found (set CHROME_TAB_TEST_BROWSER)")
class EndToEnd(unittest.TestCase):
    """The real extension and host, in a throwaway headless Chrome for Testing."""

    @classmethod
    def setUpClass(cls):
        cls.dir = short_tmp()
        cls.profile = cls.dir / "profile"
        cls.helper = cls.dir / "helper"
        cls.env = dict(os.environ,
                       CHROME_TAB_HELPER_DIR=str(cls.helper),
                       CHROME_TAB_SOCKET=str(cls.helper / "bridge.sock"),
                       CHROME_TAB_NMH_DIR=str(cls.profile / "NativeMessagingHosts"),
                       CHROME_TAB_STATE_DIR=str(cls.dir / "sessions"),
                       CHROME_TAB_NO_APPLESCRIPT="1")
        os.environ.update({k: cls.env[k] for k in
                           ("CHROME_TAB_HELPER_DIR", "CHROME_TAB_SOCKET", "CHROME_TAB_NMH_DIR",
                            "CHROME_TAB_STATE_DIR", "CHROME_TAB_NO_APPLESCRIPT")})
        out = subprocess.run([sys.executable, str(SCRIPT), "helper", "install"], env=cls.env,
                             capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        cls.install_out = out.stdout
        cls.pages = cls.dir / "pages"
        cls.pages.mkdir()
        for name in "abcdef":
            (cls.pages / f"{name}.html").write_text(f"<title>page {name}</title><h1 id=x>{name}</h1>")
        cls.chrome = subprocess.Popen(
            [BROWSER, "--headless=new", f"--user-data-dir={cls.profile}",
             f"--load-extension={cls.helper / 'extension'}",
             f"--disable-extensions-except={cls.helper / 'extension'}",
             "--no-first-run", "--no-default-browser-check", "--disable-background-networking",
             # Without these a fresh profile asks the macOS keychain for "Chromium Safe
             # Storage", which puts a password dialog in front of the user (2026-09-17).
             "--use-mock-keychain", "--password-store=basic",
             "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.host = wait_for(lambda: ct.helper_call("host", timeout=1), 30, step=0.5)

    @classmethod
    def tearDownClass(cls):
        cls.chrome.terminate()
        try:
            cls.chrome.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.chrome.kill()
        for k in ("CHROME_TAB_HELPER_DIR", "CHROME_TAB_SOCKET", "CHROME_TAB_NMH_DIR",
                  "CHROME_TAB_STATE_DIR", "CHROME_TAB_NO_APPLESCRIPT"):
            os.environ.pop(k, None)
        shutil.rmtree(cls.dir, ignore_errors=True)

    def url(self, name):
        return ct.to_url(str(self.pages / f"{name}.html"))

    def window_id(self):
        wins = ct.helper_call("windows")
        self.assertTrue(wins, "the test browser has no window")
        return wins[0]["id"]

    def groups(self, wid):
        w = next(w for w in ct.helper_call("windows") if w["id"] == wid)
        return {g["title"]: g for g in w["groups"]}

    def test_01_installer_wrote_a_valid_host_manifest(self):
        m = json.loads((self.profile / "NativeMessagingHosts" / f"{ct.HELPER_NAME}.json").read_text())
        self.assertEqual(m["allowed_origins"], [f"chrome-extension://{ct.HELPER_EXT_ID}/"])
        self.assertTrue(os.access(m["path"], os.X_OK))

    def test_02_chrome_started_the_host(self):
        self.assertIsNotNone(self.host, "the extension never connected to the host")
        self.assertEqual(self.host["chrome_pid"], self.chrome.pid)
        pong = ct.helper_call("ping")
        self.assertEqual(pong["extensionId"], ct.HELPER_EXT_ID)   # the manifest key fixes the id

    def test_03_open_groups_reuses_and_colours(self):
        wid = self.window_id()
        r1 = ct.helper_call("open", url=self.url("a"), windowId=wid, group="Wispr Flow")
        self.assertEqual(r1["action"], "added")
        self.assertTrue(r1["group"]["created"])
        self.assertEqual(r1["group"]["title"], "Wispr Flow")
        r2 = ct.helper_call("open", url=self.url("a"), windowId=wid, group="Wispr Flow")
        self.assertEqual((r2["action"], r2["tabId"]), ("reused", r1["tabId"]))
        r3 = ct.helper_call("open", url=self.url("b"), windowId=wid, group="wispr flow")
        self.assertEqual(r3["group"]["id"], r1["group"]["id"])       # same group, any case
        self.assertFalse(r3["group"]["created"])
        self.assertEqual(self.groups(wid)["Wispr Flow"]["tabs"], 2)
        r4 = ct.helper_call("open", url=self.url("c"), windowId=wid, group="mail archive", color="red")
        self.assertEqual(r4["group"]["color"], "red")
        # the same title always gets the same colour when none is asked for
        self.assertEqual(r1["group"]["color"], ct.helper_call(
            "open", url=self.url("d"), windowId=wid, group="Wispr Flow")["group"]["color"])

    def test_04_fragment_counts_as_the_same_page(self):
        wid = self.window_id()
        r1 = ct.helper_call("open", url=self.url("e") + "#x", windowId=wid)
        r2 = ct.helper_call("open", url=self.url("e"), windowId=wid)
        self.assertEqual((r2["action"], r2["tabId"]), ("reused", r1["tabId"]))

    def test_05_a_page_never_takes_over_the_tab_strip(self):
        # 0.5.0, the user's call: which tab a window shows is theirs. A page opens in the
        # background wherever they are — the old rule only protected the front window, so a
        # page opened while they were in another window took over that window's tab strip,
        # and that is what they came back to.
        wid = self.window_id()
        theirs = ct.helper_call("open", url=self.url("f"), windowId=wid, select=True)["tabId"]
        self.assertTrue(ct.helper_call("tab", tabId=theirs)["active"])
        for looking in (False, True):     # wherever the user is, same answer
            r = ct.helper_call("open", url=self.url("a") + f"?bg-{looking}", windowId=wid,
                               looking=looking)
            self.assertEqual(r["action"], "added")
            self.assertFalse(ct.helper_call("tab", tabId=r["tabId"])["active"])
            self.assertTrue(ct.helper_call("tab", tabId=theirs)["active"])
            self.assertEqual(r["showing"], r["showingBefore"])     # the reply says so too
            self.assertEqual(r["showing"], theirs)

    def test_05b_select_is_the_opt_in(self):
        wid = self.window_id()
        theirs = ct.helper_call("open", url=self.url("b") + "?theirs", windowId=wid,
                                select=True)["tabId"]
        r = ct.helper_call("open", url=self.url("c") + "?shown", windowId=wid, select=True)
        self.assertTrue(ct.helper_call("tab", tabId=r["tabId"])["active"])
        self.assertFalse(ct.helper_call("tab", tabId=theirs)["active"])
        self.assertNotEqual(r["showing"], r["showingBefore"])

    def test_05c_a_new_group_does_not_change_the_shown_tab(self):
        # Making a group moves the tab in the strip; measured 2026-09-20: it does not
        # select it. The whole of "it jumped to the new tab" was the explicit select.
        wid = self.window_id()
        theirs = ct.helper_call("open", url=self.url("d") + "?theirs2", windowId=wid,
                                select=True)["tabId"]
        r = ct.helper_call("open", url=self.url("e") + "?grouped", windowId=wid,
                           group="Proseminar", color="pink")
        self.assertTrue(r["group"]["created"])
        self.assertTrue(ct.helper_call("tab", tabId=theirs)["active"])
        self.assertEqual(r["showing"], theirs)

    def test_05d_reuse_leaves_the_shown_tab_alone(self):
        # Re-rendering a page the user has open somewhere reloads it in place, but does not
        # bring it forward; and when they are reading that very tab it isn't touched at all.
        wid = self.window_id()
        page = ct.helper_call("open", url=self.url("f") + "?reuse", windowId=wid)["tabId"]
        theirs = ct.helper_call("open", url=self.url("a") + "?theirs3", windowId=wid,
                                select=True)["tabId"]
        again = ct.helper_call("open", url=self.url("f") + "?reuse", windowId=wid)
        self.assertEqual((again["action"], again["tabId"]), ("reused", page))
        self.assertTrue(ct.helper_call("tab", tabId=theirs)["active"])
        self.assertEqual(again["showing"], theirs)
        # now they are reading it: their copy is left untouched, the render goes beside it
        ct.helper_call("open", url=self.url("f") + "?reuse", windowId=wid, select=True)
        beside = ct.helper_call("open", url=self.url("f") + "?reuse", windowId=wid, looking=True)
        self.assertEqual(beside["action"], "added-beside")
        self.assertTrue(ct.helper_call("tab", tabId=page)["active"])
        self.assertFalse(ct.helper_call("tab", tabId=beside["tabId"])["active"])

    def test_06_create_window_tab_and_move(self):
        before = {w["id"] for w in ct.helper_call("windows")}
        r = ct.helper_call("createWindow", url=self.url("a") + "?new", group="Home")
        self.assertNotIn(r["windowId"], before)
        self.assertEqual(r["group"]["title"], "Home")
        wid = min(before)
        moving = ct.helper_call("open", url=self.url("b") + "?move", windowId=wid, looking=True)
        info = ct.helper_call("tab", tabId=moving["tabId"])
        self.assertEqual(info["windowId"], wid)
        m = ct.helper_call("move", tabId=moving["tabId"], windowId=r["windowId"])
        self.assertTrue(m["moved"])
        after = ct.helper_call("tab", tabId=moving["tabId"])
        self.assertEqual(after["windowId"], r["windowId"])     # same tab id: moved, not re-made
        self.assertFalse(after["active"])
        self.assertTrue(after["url"].endswith("b.html?move"))

    def test_06b_move_group_keeps_its_id(self):
        # The Claude-in-Chrome mover moves a session's whole group. Its id must survive, or the
        # session's stored group id goes stale.
        before = {w["id"] for w in ct.helper_call("windows")}
        src = min(before)
        made = ct.helper_call("open", url=self.url("a") + "?group-move", windowId=src,
                              looking=True, group="Claude", color="orange")
        dest_win = ct.helper_call("createWindow", url=self.url("b") + "?dest")
        dest, dest_showing = dest_win["windowId"], dest_win["tabId"]
        r = ct.helper_call("moveGroup", groupId=made["group"]["id"], windowId=dest)
        self.assertTrue(r["moved"])
        tab = ct.helper_call("tab", tabId=made["tabId"])
        self.assertEqual(tab["windowId"], dest)
        self.assertEqual(tab["group"]["id"], made["group"]["id"])
        self.assertEqual((tab["group"]["title"], tab["group"]["color"]), ("Claude", "orange"))
        self.assertFalse(tab["active"])
        # and the window it arrived in still shows the tab it did (measured 2026-09-20)
        self.assertTrue(ct.helper_call("tab", tabId=dest_showing)["active"])
        # Recorded for the mover's design: did the tab report leaving its group on the way?
        print(f"\n    moveGroup groupId events during the move: {r['events']}", file=sys.stderr)

    def test_06c_move_group_lands_right_after_an_anchor_group(self):
        first = min(w["id"] for w in ct.helper_call("windows"))
        dest = ct.helper_call("createWindow", url=self.url("c") + "?anchor-win")["windowId"]
        anchor = ct.helper_call("open", url=self.url("d") + "?anchor", windowId=dest, group="Topic")
        ct.helper_call("open", url=self.url("e") + "?tail", windowId=dest)          # a loose tab after it
        moving = ct.helper_call("open", url=self.url("f") + "?beside", windowId=first, looking=True,
                                group="Claude", color="orange")
        r = ct.helper_call("moveGroup", groupId=moving["group"]["id"], windowId=dest,
                           afterGroupId=anchor["group"]["id"])
        anchor_tab = ct.helper_call("tab", tabId=anchor["tabId"])
        moved_tab = ct.helper_call("tab", tabId=moving["tabId"])
        self.assertEqual(moved_tab["windowId"], dest)
        self.assertEqual(moved_tab["index"], anchor_tab["index"] + 1)
        self.assertEqual(r["index"], anchor_tab["index"] + 1)

    def test_07_cli_open_goes_through_the_helper(self):
        # chrome-tab itself, with AppleScript disabled: names come from the host's Chrome by
        # pid, so this only works if the whole helper path works.
        wid = self.window_id()
        out = subprocess.run([sys.executable, str(SCRIPT), "open", str(self.pages / "c.html") + "",
                              "--window", str(wid), "--group", "CLI group"],
                             env=self.env, capture_output=True, text=True)
        if "AppleScript is disabled" in (out.stderr + out.stdout):
            self.skipTest("this Chrome for Testing build doesn't answer Apple events by pid "
                          "(headless); the CLI path is covered live instead")
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        self.assertIn("group “CLI group”", out.stdout)
        self.assertIn("CLI group", self.groups(wid))
        self.assertIn("in the background", out.stdout)

    def test_07c_cli_open_leaves_the_shown_tab_alone(self):
        wid = self.window_id()
        theirs = ct.helper_call("open", url=self.url("b") + "?cli-theirs", windowId=wid,
                                select=True)["tabId"]
        out = subprocess.run([sys.executable, str(SCRIPT), "open", str(self.pages / "c.html"),
                              "--window", str(wid), "--group", "CLI background"],
                             env=self.env, capture_output=True, text=True)
        if "AppleScript is disabled" in (out.stderr + out.stdout):
            self.skipTest("this headless build doesn't answer Apple events by pid")
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        self.assertTrue(ct.helper_call("tab", tabId=theirs)["active"], out.stdout)
        self.assertIn("still shows the tab it did", out.stdout)
        # --select is the opt-in, and it says so
        out = subprocess.run([sys.executable, str(SCRIPT), "open", str(self.pages / "d.html"),
                              "--window", str(wid), "--group", "CLI background", "--select"],
                             env=self.env, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        self.assertFalse(ct.helper_call("tab", tabId=theirs)["active"])
        self.assertIn("as asked", out.stdout)

    @unittest.skipUnless(os.environ.get("CHROME_TAB_SLOW_TESTS"), "slow; set CHROME_TAB_SLOW_TESTS=1")
    def test_09_survives_idle_and_comes_back_after_the_host_dies(self):
        # Chrome stops an idle extension worker after ~30 s unless something holds it; the
        # open native port should. Then kill the host: the worker's alarm reconnects within
        # a minute and Chrome starts a fresh host.
        time.sleep(45)
        self.assertEqual(ct.helper_call("ping")["extensionId"], ct.HELPER_EXT_ID)
        old = ct.helper_call("host")["pid"]
        os.kill(old, 9)
        back = wait_for(lambda: (ct.helper_call("host", timeout=1) or {}).get("pid") not in (None, old),
                        80, step=1)
        self.assertTrue(back, "no new host within 80 s of the old one dying")
        self.assertEqual(ct.helper_call("ping")["extensionId"], ct.HELPER_EXT_ID)

    def test_07b_cli_open_follows_a_group_into_its_window(self):
        # the user's pick 1A (17 Sep 2026): a matching group anywhere wins, else the home window.
        host = ct.helper_call("host")
        wins = ct.helper_call("windows")
        home = min(w["id"] for w in wins)
        other = ct.helper_call("createWindow", url=self.url("a") + "?other")["windowId"]
        try:
            ct.jxa(ct.JXA_NAME, host["chrome_pid"], home, "home")
            ct.jxa(ct.JXA_NAME, host["chrome_pid"], other, "elsewhere")
        except Exception as e:
            self.skipTest(f"can't name windows in this headless build by pid ({e})")
        ct.helper_call("open", url=self.url("b") + "?existing", windowId=other, group="Mail archive")
        env = dict(self.env, CHROME_TAB_HOME_WINDOW="home")
        out = subprocess.run([sys.executable, str(SCRIPT), "open", str(self.pages / "d.html"),
                              "--group", "mail archive"], env=env, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        self.assertIn("Chrome window “elsewhere”, group “Mail archive”", out.stdout)
        self.assertIn("followed the group", out.stdout)
        # a topic nobody has → a new group in the home window, and the session remembers it
        # ("Grooming": no earlier test makes that group; e.html is already open in home, so
        # this is also the reuse path getting grouped)
        out = subprocess.run([sys.executable, str(SCRIPT), "open", str(self.pages / "e.html"),
                              "--window", "Grooming"], env=env, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        self.assertIn("Chrome window “home”, group “Grooming” (new", out.stdout)
        self.assertIn("“Grooming” is the tab group", out.stdout)
        self.assertIn("other groups in this window:", out.stdout)
        out = subprocess.run([sys.executable, str(SCRIPT), "open", str(self.pages / "f.html")],
                             env=env, capture_output=True, text=True)
        self.assertIn("Chrome window “home”, group “Grooming”", out.stdout)
        self.assertNotIn("(new", out.stdout)

    def test_08_test_browser_never_came_forward(self):
        # Not "focus stayed put": the user may be working while this runs, and their own
        # clicks move focus. What must never happen is the throwaway browser taking the front.
        self.assertNotEqual(ct.front_app()[1], "com.google.chrome.for.testing")


if __name__ == "__main__":
    unittest.main(verbosity=2)
