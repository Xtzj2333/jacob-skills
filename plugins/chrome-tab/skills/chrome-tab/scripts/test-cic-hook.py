#!/usr/bin/env python3
"""Tests for `chrome-tab hook claude-in-chrome`, the Claude-in-Chrome group mover.

Part 1, the parser: the tool results below are real, copied from session transcripts of
2026-09-16/17 (see the helper's HANDOFF). A PostToolUse hook gets an MCP tool's result as
a list of content blocks. The group id sits in one of three shapes: tabs_context_mcp's own
JSON block, the block Claude Code appends to a navigate without a tabId, or
"[tabs_context_mcp] {…}" lines in a browser_batch.

Part 2, the decision (helper faked): it moves only a lone tab in the reported group, once,
never an active tab, never when the target window isn't open, and says why each time. The
target (the user's pick, 17 Sep 2026) is beside the group this session's pages went to, else the
browse window, which defaults to the home window.

Part 3 (needs Chrome for Testing, like test-helper.py): the real hook command moves a real
one-tab "Claude" group into a window named "Claude sessions" and keeps the group's id.

Run:  python3 scripts/test-cic-hook.py
"""
import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "chrome-tab"


def load():
    loader = importlib.machinery.SourceFileLoader("chrome_tab_cic_under_test", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


ct = load()


def blocks(*texts):
    return [{"type": "text", "text": t} for t in texts]


REMINDER = "<system-reminder>You used a single tool call this turn.</system-reminder>"
NEW_GROUP = blocks(
    '{"availableTabs":[{"tabId":940163608,"title":"New Tab","url":"chrome://newtab/"}],"tabGroupId":1933887913}',
    '\n\nTab Context:\n- Available tabs:\n  • tabId 940163608: "New Tab" ("chrome://newtab/")',
    REMINDER)
USED_GROUP = blocks(
    '{"availableTabs":[{"tabId":940163590,"title":"Podcasts","url":"https://docs.google.com/x"}],'
    '"selectedTabId":940163590,"tabGroupId":1988085227}', REMINDER)
NO_GROUP = blocks("No tab group exists for this session. Use createIfEmpty: true to create one.", REMINDER)
FRONT_LOADED = blocks(
    "Navigated to https://example.com/",
    "\n\nTab Context:\n- Executed on tabId: 940163184\n- Available tabs:\n  • tabId 940163184: …",
    REMINDER,
    '\nTab context (from front-loaded tabs_context_mcp):\n'
    '{"availableTabs":[{"tabId":940163184,"title":"New Tab","url":"chrome://newtab/"}],"tabGroupId":496297769}\n'
    "Tabs in this group were opened for this task and are yours to clean up: …")
BATCH = blocks(
    '[tabs_context_mcp] {"availableTabs":[{"tabId":940161247,"title":"New Tab","url":"chrome://newtab/"}],'
    '"tabGroupId":14663247}',
    "[navigate] Navigated to https://example.com/")
TWO_TABS = blocks('{"availableTabs":[{"tabId":1,"title":"a","url":"x"},{"tabId":2,"title":"b","url":"y"}],'
                  '"tabGroupId":55}')


class Parser(unittest.TestCase):
    def ids(self, resp):
        return [(g["tabGroupId"], g["availableTabs"][0]["tabId"]) for g in ct.fresh_groups(resp)]

    def test_new_group_from_tabs_context(self):
        self.assertEqual(self.ids(NEW_GROUP), [(1933887913, 940163608)])

    def test_group_already_in_use_is_left_alone(self):
        self.assertEqual(self.ids(USED_GROUP), [])
        self.assertEqual(len(ct.claude_groups_in(USED_GROUP)), 1)   # seen, just not fresh

    def test_no_group(self):
        self.assertEqual(self.ids(NO_GROUP), [])

    def test_front_loaded_navigate(self):
        self.assertEqual(self.ids(FRONT_LOADED), [(496297769, 940163184)])

    def test_browser_batch_line(self):
        self.assertEqual(self.ids(BATCH), [(14663247, 940161247)])

    def test_two_tab_group_is_not_fresh(self):
        self.assertEqual(self.ids(TWO_TABS), [])

    def test_string_response(self):
        self.assertEqual(self.ids(NEW_GROUP[0]["text"]), [(1933887913, 940163608)])

    def test_garbage(self):
        for resp in (None, 5, {}, [None, 3, {"type": "image"}], "{not json", blocks("{\"a\":1}")):
            self.assertEqual(ct.fresh_groups(resp), [])


class Decision(unittest.TestCase):
    """claim_claude_tab with the helper and Chrome faked."""

    WINDOWS = [
        {"index": 1, "id": "11", "given_name": "Happiness Study", "minimized": False, "title": "", "tabs": 4},
        {"index": 2, "id": "22", "given_name": "miscellaneous", "minimized": False, "title": "", "tabs": 19},
        {"index": 3, "id": "33", "given_name": "FE", "minimized": False, "title": "", "tabs": 9},
    ]
    EXT = [{"id": 11, "groups": []},
           {"id": 22, "groups": [{"id": 501, "title": "chrome-tab", "tabs": 2}]},
           {"id": 33, "groups": [{"id": 601, "title": "FE4", "tabs": 3}]}]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        keys = ("CHROME_TAB_HELPER_DIR", "CHROME_TAB_BROWSE_WINDOW", "CHROME_TAB_HOME_WINDOW", "CHROME_TAB_STATE_DIR")
        self.env_saved = {k: os.environ.get(k) for k in keys}
        os.environ["CHROME_TAB_HELPER_DIR"] = self.tmp.name
        os.environ["CHROME_TAB_STATE_DIR"] = os.path.join(self.tmp.name, "sessions")
        os.environ["CHROME_TAB_HOME_WINDOW"] = "miscellaneous"
        os.environ.pop("CHROME_TAB_BROWSE_WINDOW", None)
        ct.STATE_DIR = Path(os.environ["CHROME_TAB_STATE_DIR"])
        self.saved = {n: getattr(ct, n) for n in ("helper_host", "helper_call", "list_windows", "FocusGuard")}
        self.calls = []
        self.tab = {"id": 940163608, "windowId": 11, "active": False, "url": "chrome://newtab/",
                    "group": {"id": 1933887913, "title": "Claude", "color": "blue", "tabs": 1}}
        self.windows = list(self.WINDOWS)
        self.running = True
        ct.helper_host = lambda: {"pid": 1, "chrome_pid": 2} if self.running else None
        ct.list_windows = lambda pid=None: self.windows
        ct.helper_call = self.fake_call

        class NoGuard:
            def __enter__(s): return s
            def __exit__(s, *a): pass
            def done(s, tail=None): pass
            def describe(s): return None
        ct.FocusGuard = lambda *a, **k: NoGuard()

    def tearDown(self):
        for n, f in self.saved.items():
            setattr(ct, n, f)
        for k, v in self.env_saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def fake_call(self, cmd, timeout=8.0, **args):
        self.calls.append((cmd, args))
        if cmd == "tab":
            return dict(self.tab)
        if cmd == "windows":
            return [dict(w) for w in self.EXT]
        if cmd == "moveGroup":
            self.tab["windowId"] = args["windowId"]
            return {"moved": True, "events": [{"tabId": self.tab["id"], "groupId": -1}]}
        raise AssertionError(cmd)

    def claim(self, resp=NEW_GROUP, tool="mcp__claude-in-chrome__tabs_context_mcp", session="sess-1"):
        return ct.claim_claude_tab({"tool_name": tool, "tool_response": resp, "session_id": session})

    def bind(self, session, window, group):
        ct.STATE_DIR.mkdir(parents=True, exist_ok=True)
        (ct.STATE_DIR / f"{session}.json").write_text(json.dumps({"window_name": window, "group": group}))

    def moves(self):
        return [a for c, a in self.calls if c == "moveGroup"]

    def test_moves_a_fresh_group_into_the_home_window_by_default(self):
        msg = self.claim()
        self.assertEqual(self.moves(), [{"groupId": 1933887913, "windowId": 22, "afterGroupId": None}])
        self.assertIn("the “miscellaneous” window", msg)
        self.assertIn("Happiness Study", msg)

    def test_moves_beside_the_sessions_topic_group(self):
        self.bind("sess-1", "FE", "FE4")
        msg = self.claim()
        self.assertEqual(self.moves(), [{"groupId": 1933887913, "windowId": 33, "afterGroupId": 601}])
        self.assertIn("beside this session's “FE4” group", msg)

    def test_topic_group_in_a_closed_window_falls_back_to_home(self):
        self.bind("sess-1", "Wispr Flow", "Wispr Flow")
        self.claim()
        self.assertEqual(self.moves()[0]["windowId"], 22)

    def test_another_sessions_binding_is_not_used(self):
        self.bind("sess-2", "FE", "FE4")
        self.claim(session="sess-1")
        self.assertEqual(self.moves()[0]["windowId"], 22)

    def test_only_once_per_tab(self):
        self.claim()
        self.tab["windowId"] = 11                 # the user dragged it back
        self.calls.clear()
        self.assertIsNone(self.claim())
        self.assertEqual(self.moves(), [])

    def test_already_in_place(self):
        self.tab["windowId"] = 22
        self.assertIsNone(self.claim())
        self.assertEqual(self.moves(), [])

    def test_group_in_use_is_not_moved(self):
        self.assertIsNone(self.claim(USED_GROUP))
        self.assertEqual(self.calls, [])

    def test_group_grew_or_changed_is_not_moved(self):
        self.tab["group"] = dict(self.tab["group"], tabs=2)
        self.assertIsNone(self.claim())
        self.tab["group"] = dict(self.tab["group"], tabs=1, id=999)
        self.assertIsNone(self.claim())
        self.assertEqual(self.moves(), [])

    def test_active_tab_is_not_moved(self):
        self.tab["active"] = True
        self.assertIsNone(self.claim())
        self.assertEqual(self.moves(), [])

    def test_no_browse_window_says_so_and_moves_nothing(self):
        self.windows = [self.WINDOWS[0]]
        msg = self.claim()
        self.assertEqual(self.moves(), [])
        self.assertIn("No Chrome window named “miscellaneous”", msg)
        self.assertIn("Happiness Study", msg)

    def test_browse_window_is_a_setting(self):
        os.environ["CHROME_TAB_BROWSE_WINDOW"] = "happiness study"
        self.tab["windowId"] = 22
        self.claim()
        self.assertEqual(self.moves()[0]["windowId"], 11)

    def test_helper_down_says_so(self):
        self.running = False
        self.assertIn("helper isn't running", self.claim())

    def test_hook_command_ignores_other_tools_fast(self):
        out = subprocess.run([sys.executable, str(SCRIPT), "hook", "claude-in-chrome"],
                             input=json.dumps({"tool_name": "Bash", "tool_response": NEW_GROUP}),
                             capture_output=True, text=True, env=dict(os.environ, CHROME_TAB_NO_APPLESCRIPT="1"))
        self.assertEqual((out.returncode, out.stdout), (0, ""))


def find_test_browser():
    """Same search as test-helper.py: $CHROME_TAB_TEST_BROWSER, else ~/.cache/chrome-tab-test or ~/.cache/puppeteer."""
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
    """The real hook command, against a throwaway headless Chrome for Testing."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="ctc-", dir="/tmp"))
        self.env = dict(os.environ,
                        CHROME_TAB_HELPER_DIR=str(self.dir / "helper"),
                        CHROME_TAB_SOCKET=str(self.dir / "helper" / "bridge.sock"),
                        CHROME_TAB_NMH_DIR=str(self.dir / "profile" / "NativeMessagingHosts"),
                        CHROME_TAB_STATE_DIR=str(self.dir / "sessions"),
                        CHROME_TAB_HOME_WINDOW="Claude sessions",
                        CHROME_TAB_NO_APPLESCRIPT="1")
        self.saved = {k: os.environ.get(k) for k in self.env if k.startswith("CHROME_TAB_")}
        os.environ.update({k: v for k, v in self.env.items() if k.startswith("CHROME_TAB_")})
        out = subprocess.run([sys.executable, str(SCRIPT), "helper", "install"], env=self.env,
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.chrome = subprocess.Popen(
            [BROWSER, "--headless=new", f"--user-data-dir={self.dir / 'profile'}",
             f"--load-extension={self.dir / 'helper' / 'extension'}",
             f"--disable-extensions-except={self.dir / 'helper' / 'extension'}",
             "--no-first-run", "--no-default-browser-check", "--disable-background-networking",
             "--use-mock-keychain", "--password-store=basic", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        end = time.monotonic() + 30
        self.host = None
        while time.monotonic() < end and not self.host:
            self.host = ct.helper_call("host", timeout=1)
            time.sleep(0.3)
        self.assertTrue(self.host, "the helper never came up")

    def tearDown(self):
        self.chrome.terminate()
        try:
            self.chrome.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.chrome.kill()
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_hook_moves_a_new_claude_group(self):
        first = ct.helper_call("windows")[0]["id"]
        # "Claude sessions" is a second window, named the way the user names one.
        dest = ct.helper_call("createWindow", url="about:blank#dest")["windowId"]
        try:
            ct.jxa(ct.JXA_NAME, self.host["chrome_pid"], dest, "Claude sessions")
        except Exception as e:
            self.skipTest(f"can't name a window in this headless build by pid ({e})")
        # What Claude-in-Chrome does for createIfEmpty: a background New Tab in a group "Claude".
        made = ct.helper_call("open", url="chrome://newtab/", windowId=first, looking=True,
                              group="Claude", color="blue")
        resp = blocks(json.dumps({"availableTabs": [{"tabId": made["tabId"], "title": "New Tab",
                                                     "url": "chrome://newtab/"}],
                                  "tabGroupId": made["group"]["id"]}, separators=(",", ":")), REMINDER)
        out = subprocess.run([sys.executable, str(SCRIPT), "hook", "claude-in-chrome"], env=self.env,
                             input=json.dumps({"tool_name": "mcp__claude-in-chrome__tabs_context_mcp",
                                               "tool_response": resp}),
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        ctx = json.loads(out.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("into the “Claude sessions” window", ctx)
        tab = ct.helper_call("tab", tabId=made["tabId"])
        self.assertEqual(tab["windowId"], dest)
        self.assertEqual(tab["group"]["id"], made["group"]["id"])   # the session's group id still holds
        self.assertFalse(tab["active"])   # the window it lands in keeps showing its own tab
        # a second report of the same group does nothing
        again = subprocess.run([sys.executable, str(SCRIPT), "hook", "claude-in-chrome"], env=self.env,
                               input=json.dumps({"tool_name": "mcp__claude-in-chrome__tabs_context_mcp",
                                                 "tool_response": resp}),
                               capture_output=True, text=True, timeout=30)
        self.assertEqual(again.stdout, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
