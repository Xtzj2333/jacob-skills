#!/usr/bin/env python3
"""Tests for where `chrome-tab open` puts a page (0.2.0 home window, 0.4.0 tab groups).

Background: sessions pass `--window "<topic>"`, and until 0.2.0 a topic no window had got
a brand-new window (76 of them, 14 Aug–17 Sep 2026). Since 0.2.0 such pages go to the home
window. Since 0.4.0 (the user's ideal, 17 Sep 2026) every page lands in a tab group: the matching
group if one exists, in whichever window it lives, else a new group named after the topic
in the home window. These tests pin that rule with the user's real group names as cases (personal ones renamed):

  * the loose matcher: "mail archive" → "Mail archive", "Furniture" → "Furnitures",
    "UChicago mail archive" → "Mail archive"; "Berkeley seminars" ≠ "Berkeley funding";
    "FE" only matches "FE"; Claude-in-Chrome's groups never match;
  * the topic name's sources, in order: --group, the --window name given on this call, the
    session's earlier group, the file's project folder, the current folder;
  * placement: follow a matching group into its window; else the home window, new group;
    an explicit --window keeps the page in that window; --new-window still works;
  * without the helper (no groups): the 0.2.0 behaviour, window only.

Pure logic: nothing here talks to Chrome.
Run:  python3 scripts/test-target.py
"""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "chrome-tab"


def load():
    loader = importlib.machinery.SourceFileLoader("chrome_tab_under_test", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


ct = load()


def win(i, name, title=None, minimized=False):
    return {"index": i, "id": str(940000000 + i), "given_name": name, "tabs": 1,
            "minimized": minimized, "title": title if title is not None else name}


# The user's windows and groups as `chrome-tab list` showed them on 2026-09-17 21:12 (personal
# names swapped for neutral ones with the same shape), plus an
# unnamed window whose active-tab title carries a topic word.
WINDOWS = [
    win(1, "bottom-up app", minimized=True),
    win(2, "LLM and Culture", minimized=True),
    win(3, "FE"),
    win(4, "Happiness Study"),
    win(5, "miscellaneous"),
    win(7, "", title="Furniture deals - Google Search"),
]
GROUPS = {
    "bottom-up app": ["Application", "Method", "August's"],
    "LLM and Culture": ["LLM", "Age"],
    "FE": ["pre-reg", "FE4", "FE4 prescreen", "✅Claude"],
    "Happiness Study": [],
    "miscellaneous": ["Tax", "Furnitures", "Urgent", "lease renewal", "Choir", "Dentist", "orientation",
                      "backup", "Mail archive", "music", "talks", "air", "chrome-tab"],
    "": [],
}
EXT = [{"id": int(w["id"]), "groups": [{"id": 1000 + i, "title": t, "color": "blue", "tabs": 1}
                                        for i, t in enumerate(GROUPS[w["given_name"]])]} for w in WINDOWS]
HOME = "miscellaneous"


class Matcher(unittest.TestCase):
    def test_same_name_any_case_or_punctuation(self):
        self.assertEqual(ct.group_score("mail archive", "Mail archive"), 2)
        self.assertEqual(ct.group_score("chrome tab", "chrome-tab"), 2)
        self.assertEqual(ct.group_score("FE", "FE"), 2)

    def test_loose_matches_the_user_wanted(self):
        self.assertEqual(ct.group_score("Furniture", "Furnitures"), 1)
        self.assertEqual(ct.group_score("UChicago mail archive", "Mail archive"), 1)
        self.assertEqual(ct.group_score("lease", "lease renewal"), 1)

    def test_no_false_friends(self):
        self.assertEqual(ct.group_score("Berkeley seminars", "Berkeley funding"), 0)
        self.assertEqual(ct.group_score("FE", "FE4"), 0)              # short names: exact only
        self.assertEqual(ct.group_score("air", "Mail archive"), 0)
        self.assertEqual(ct.group_score("to do", "todo"), 0)
        self.assertEqual(ct.group_score("Home Office", "Furnitures"), 0)

    def test_claude_in_chrome_groups_never_match(self):
        for title in ("Claude", "✅Claude", "⌛Claude", "Claude (MCP)"):
            self.assertEqual(ct.group_score("Claude", title), 0)
            self.assertEqual(ct.group_score("Claude sessions", title), 0)

    def test_find_group_prefers_exact_then_home(self):
        ext = [{"id": 1, "groups": [{"id": 11, "title": "Furnitures"}]},
               {"id": 2, "groups": [{"id": 22, "title": "Furniture"}]}]
        self.assertEqual(ct.find_group("furniture", ext)[:2], ("2", "Furniture"))
        ext = [{"id": 1, "groups": [{"id": 11, "title": "music"}]},
               {"id": 2, "groups": [{"id": 22, "title": "Music"}]}]
        self.assertEqual(ct.find_group("music", ext, prefer=["2"])[0], "2")
        self.assertEqual(ct.find_group("music", ext)[0], "1")
        self.assertIsNone(ct.find_group("nothing like it", ext))


class Topic(unittest.TestCase):
    def test_project_folder_from_reports_folder(self):
        h = Path.home()
        self.assertEqual(ct.project_of(str(h / "Claude/Personal/Furniture/reports (claude)/s1.v1_x.html")), "Furniture")
        self.assertEqual(ct.project_of(str(h / "Claude/UChicago account backup/reports (claude)/plan.html")),
                         "UChicago account backup")
        self.assertEqual(ct.project_of(str(h / "Claude/reports/claude-code-ux/page.html")), "claude-code-ux")
        self.assertEqual(ct.project_of(str(h / "Claude/Relist (claude)/catalog.html")), "Relist")
        self.assertEqual(ct.project_of("file://" + str(h / "Claude/Personal/Audio/reports%20(claude)/x.html")), "Audio")

    def test_unhelpful_places_give_nothing(self):
        self.assertIsNone(ct.project_of("https://example.com/x"))
        self.assertIsNone(ct.project_of(str(Path.home() / "Claude/x.html")))
        self.assertIsNone(ct.project_of("/tmp/x.html"))

    def test_source_order(self):
        t = lambda **k: ct.topic_name(k.get("explicit"), k.get("remembered"), k.get("wanted"),
                                      k.get("fell_back", False), k.get("targets", []), cwd=k.get("cwd", "/x/Berkeley"))
        self.assertEqual(t(explicit="FE4", remembered="chrome-tab", wanted="Wispr Flow", fell_back=True)[0], "FE4")
        self.assertEqual(t(remembered="chrome-tab", wanted="Wispr Flow", fell_back=True)[0], "Wispr Flow")
        self.assertEqual(t(remembered="chrome-tab")[0], "chrome-tab")
        self.assertEqual(t(wanted="Wispr Flow", fell_back=True)[0], "Wispr Flow")
        self.assertEqual(t(targets=[str(Path.home() / "Claude/Personal/Audio/reports (claude)/x.html")])[0], "Audio")
        self.assertEqual(t()[0], "Berkeley")
        self.assertEqual(t(cwd=str(Path.home() / "Claude"))[0], "Claude pages")


class Placement(unittest.TestCase):
    def plan(self, wanted=None, group=None, binding=None, targets=(), ext=EXT, new_window=False,
             windows=WINDOWS, home=HOME):
        return ct.plan_placement(windows, ext, wanted, group, binding, list(targets), home, new_window,
                                 cwd="/x/somewhere")

    def test_topic_with_no_window_becomes_a_group_in_home(self):
        # The 17 Sep pattern: "Wispr Flow" made four windows in 80 minutes.
        p = self.plan(wanted="Wispr Flow")
        self.assertEqual((p["window"]["given_name"], p["group"], p["group_new"], p["fell_back"]),
                         ("miscellaneous", "Wispr Flow", True, True))
        self.assertIn("Mail archive", p["others"])

    def test_topic_matches_an_existing_group_loosely(self):
        p = self.plan(wanted="mail archive")
        self.assertEqual((p["window"]["given_name"], p["group"], p["group_new"]), ("miscellaneous", "Mail archive", False))
        p = self.plan(group="Furniture")
        self.assertEqual((p["group"], p["group_new"]), ("Furnitures", False))

    def test_group_in_another_window_wins(self):
        p = self.plan(group="FE4")
        self.assertEqual((p["window"]["given_name"], p["group"], p["followed"]), ("FE", "FE4", True))

    def test_explicit_window_keeps_the_page_there(self):
        p = self.plan(wanted="FE", group="mail archive")
        self.assertEqual((p["window"]["given_name"], p["group"], p["group_new"]), ("FE", "mail archive", True))

    def test_named_window_with_no_group_gets_a_group_named_after_it(self):
        p = self.plan(wanted="Happiness Study")
        self.assertEqual((p["window"]["given_name"], p["group"], p["group_new"]), ("Happiness Study", "Happiness Study", True))

    def test_session_memory_reuses_the_group(self):
        b = {"window_name": "miscellaneous", "group": "chrome-tab"}
        p = self.plan(binding=b, targets=[str(Path.home() / "Claude/Personal/Audio/reports (claude)/x.html")])
        self.assertEqual((p["window"]["given_name"], p["group"], p["group_new"]), ("miscellaneous", "chrome-tab", False))
        # ...but an explicit --window elsewhere makes the earlier group irrelevant
        p = self.plan(binding=b, wanted="FE")
        self.assertEqual((p["window"]["given_name"], p["group"]), ("FE", "FE"))

    def test_folder_names_the_group_when_nothing_else_does(self):
        p = self.plan(targets=[str(Path.home() / "Claude/Personal/Audio/reports (claude)/x.html")])
        self.assertEqual((p["window"]["given_name"], p["group"], p["topic_source"]),
                         ("miscellaneous", "Audio", "the file's folder"))

    def test_claude_in_chrome_groups_are_never_used(self):
        p = self.plan(group="Claude")
        self.assertEqual((p["window"]["given_name"], p["group_new"]), ("miscellaneous", True))

    def test_topic_never_matches_an_unnamed_windows_tab_title(self):
        p = self.plan(wanted="Furniture deals")
        self.assertEqual(p["window"]["given_name"], "miscellaneous")

    def test_missing_home_is_created_by_name(self):
        wins = [w for w in WINDOWS if w["given_name"] != HOME]
        ext = [e for e in EXT if str(e["id"]) != "940000005"]
        p = self.plan(wanted="Wispr Flow", windows=wins, ext=ext)
        self.assertEqual((p["window"], p["create_name"], p["group"]), (None, HOME, "Wispr Flow"))

    def test_new_window_only_when_asked(self):
        p = self.plan(wanted="FE", new_window=True)
        self.assertEqual((p["window"], p["create_name"], p["group"]), (None, "FE", "FE"))

    def test_without_the_helper_it_is_windows_only(self):
        p = self.plan(wanted="Wispr Flow", ext=None)
        self.assertEqual((p["window"]["given_name"], p["group"], p["fell_back"]), ("miscellaneous", None, True))
        p = self.plan(wanted="FE", ext=None)
        self.assertEqual((p["window"]["given_name"], p["group"]), ("FE", None))
        p = self.plan(ext=None, windows=[], home=HOME)
        self.assertEqual((p["window"], p["create_name"]), (None, HOME))


class ResolveWindow(unittest.TestCase):
    def test_title_fallback_still_serves_the_name_command(self):
        self.assertEqual(ct.resolve_window("Furniture deals", WINDOWS)["index"], 7)

    def test_title_fallback_off_for_open(self):
        self.assertIsNone(ct.resolve_window("Furniture deals", WINDOWS, titles=False))

    def test_index_and_id_still_work(self):
        self.assertEqual(ct.resolve_window("#3", WINDOWS, titles=False)["given_name"], "FE")
        self.assertEqual(ct.resolve_window("940000004", WINDOWS, titles=False)["given_name"], "Happiness Study")


class HomeName(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = dict(os.environ, XDG_CONFIG_HOME=self.tmp.name)
        self.env.pop("CHROME_TAB_HOME_WINDOW", None)
        self._saved = {k: os.environ.get(k) for k in ("XDG_CONFIG_HOME", "CHROME_TAB_HOME_WINDOW")}
        os.environ["XDG_CONFIG_HOME"] = self.tmp.name
        os.environ.pop("CHROME_TAB_HOME_WINDOW", None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def run_cli(self, *args, env=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                              env=env or self.env)

    def test_default(self):
        self.assertEqual(ct.home_window_name(), "Claude sessions")

    def test_config_file_then_env(self):
        cfg = Path(self.tmp.name) / "chrome-tab" / "config.json"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(json.dumps({"home_window": "miscellaneous"}))
        self.assertEqual(ct.home_window_name(), "miscellaneous")
        os.environ["CHROME_TAB_HOME_WINDOW"] = "FE"
        self.assertEqual(ct.home_window_name(), "FE")

    def test_unreadable_config_falls_back_to_default(self):
        cfg = Path(self.tmp.name) / "chrome-tab" / "config.json"
        cfg.parent.mkdir(parents=True)
        cfg.write_text("{not json")
        self.assertEqual(ct.home_window_name(), "Claude sessions")

    def test_home_command_shows_and_sets(self):
        out = self.run_cli("home")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("Claude sessions", out.stdout)
        self.assertIn("default", out.stdout)
        out = self.run_cli("home", "miscellaneous")
        self.assertEqual(out.returncode, 0, out.stderr)
        cfg = json.loads((Path(self.tmp.name) / "chrome-tab" / "config.json").read_text())
        self.assertEqual(cfg, {"home_window": "miscellaneous"})
        self.assertIn("miscellaneous", self.run_cli("home").stdout)

    def test_new_window_needs_a_name(self):
        out = self.run_cli("open", "x.html", "--new-window")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("--new-window needs --window", out.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
