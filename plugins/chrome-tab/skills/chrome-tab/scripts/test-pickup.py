#!/usr/bin/env python3
"""Tests for how `chrome-tab` is picked up after a plugin update (0.1.3).

Background (2026-09-15, Tony): `claude plugin update chrome-tab@jacob-skills` drops a
new version directory into ~/.claude/plugins/cache/<marketplace>/chrome-tab/<version>/,
but ~/.local/bin/chrome-tab was a symlink into the *old* version directory, so the
old binary kept running while the update reported success. PyObjC missing degraded the
focus guard just as silently. These tests pin the fix:

  * install.sh from a plugin-cache dir installs a launcher that resolves the installed
    copy at run time (so `claude plugin update` alone is enough afterwards);
  * a copy that is not the installed one forwards to the installed one and says so;
  * `chrome-tab doctor` reports a stale PATH entry and a missing PyObjC, with the fix;
  * install.sh from a source checkout (Jacob's ~/.claude/skills) still makes a symlink.

Run:  python3 scripts/test-pickup.py      (needs macOS; never touches the real ~/.claude)
"""
import importlib.machinery
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "chrome-tab"
INSTALL = HERE / "install.sh"
PY = sys.executable


def has_appkit(python):
    return subprocess.run([python, "-c", "import AppKit"], capture_output=True).returncode == 0


class FakeHome:
    """A throwaway $HOME with a Claude plugin cache laid out like the real one."""

    def __init__(self):
        self.home = Path(tempfile.mkdtemp(prefix="chrome-tab-test-"))
        self.cache = self.home / ".claude" / "plugins" / "cache" / "jacob-skills" / "chrome-tab"
        self.bin = self.home / ".local" / "bin"

    def cleanup(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def env(self, python=PY):
        e = {
            "HOME": str(self.home),
            "PATH": f"{self.bin}:{Path(python).parent}:/usr/bin:/bin:/usr/sbin:/sbin",
            "LANG": "en_US.UTF-8",
        }
        return e

    def add_version(self, ver):
        """Drop a copy of the script under test into the cache as version `ver`."""
        d = self.cache / ver / "skills" / "chrome-tab" / "scripts"
        d.mkdir(parents=True)
        for f in HERE.iterdir():             # the cache carries every shipped script
            if f.is_file() and f.name != Path(__file__).name:
                shutil.copy(f, d / f.name)
        src = SCRIPT.read_text()
        src = re.sub(r'^__version__ = "[^"]*"', f'__version__ = "{ver}"', src, count=1, flags=re.M)
        (d / "chrome-tab").write_text(src)
        (d / "chrome-tab").chmod(0o755)
        (self.cache / ver / ".claude-plugin").mkdir()
        (self.cache / ver / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "chrome-tab", "version": ver}))
        return d

    def set_installed(self, ver):
        """What `claude plugin update` leaves behind: installed_plugins.json points at `ver`."""
        f = self.home / ".claude" / "plugins" / "installed_plugins.json"
        f.write_text(json.dumps({"version": 2, "plugins": {"chrome-tab@jacob-skills": [{
            "scope": "user", "installPath": str(self.cache / ver), "version": ver}]}}))

    def run(self, argv, python=PY, cwd=None):
        return subprocess.run(argv, capture_output=True, text=True, env=self.env(python),
                              cwd=cwd or str(self.home))


class PickupTests(unittest.TestCase):
    def setUp(self):
        self.h = FakeHome()

    def tearDown(self):
        self.h.cleanup()

    def test_launcher_follows_plugin_update(self):
        """After install.sh once, `claude plugin update` alone must switch the PATH command."""
        d1 = self.h.add_version("0.1.1")
        self.h.set_installed("0.1.1")
        r = self.h.run(["sh", str(d1 / "install.sh")])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.h.add_version("0.1.2")
        self.h.set_installed("0.1.2")          # the update; nobody re-runs install.sh
        r = self.h.run([str(self.h.bin / "chrome-tab"), "--version"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("0.1.2", r.stdout)

    def test_stale_symlink_forwards_to_installed_copy(self):
        """Tony's state: ~/.local/bin/chrome-tab -> old version dir. The old copy must not run."""
        d1 = self.h.add_version("0.1.1")
        self.h.add_version("0.1.2")
        self.h.set_installed("0.1.2")
        self.h.bin.mkdir(parents=True)
        (self.h.bin / "chrome-tab").symlink_to(d1 / "chrome-tab")
        r = self.h.run([str(self.h.bin / "chrome-tab"), "--version"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("0.1.2", r.stdout)
        self.assertIn("install.sh", r.stderr)   # it says how to make the PATH entry current

    def test_doctor_flags_stale_path_entry(self):
        d1 = self.h.add_version("0.1.1")
        d2 = self.h.add_version("0.1.2")
        self.h.set_installed("0.1.2")
        self.h.bin.mkdir(parents=True)
        (self.h.bin / "chrome-tab").symlink_to(d1 / "chrome-tab")
        r = self.h.run([str(d2 / "chrome-tab"), "doctor"])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"(?i)stale")
        self.assertIn("0.1.1", r.stdout)
        self.assertIn("install.sh", r.stdout)

    def test_doctor_clean_after_install(self):
        d2 = self.h.add_version("0.1.2")
        self.h.set_installed("0.1.2")
        r = self.h.run(["sh", str(d2 / "install.sh")])
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.h.run([str(self.h.bin / "chrome-tab"), "doctor"])
        self.assertNotRegex(r.stdout, r"(?i)stale")
        if has_appkit(PY):
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_doctor_reports_missing_pyobjc_with_the_fix(self):
        apple = "/usr/bin/python3"
        if not Path(apple).exists() or has_appkit(apple):
            self.skipTest("no interpreter without PyObjC to test against")
        d2 = self.h.add_version("0.1.2")
        self.h.set_installed("0.1.2")
        r = self.h.run([apple, str(d2 / "chrome-tab"), "doctor"], python=apple)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("PyObjC", r.stdout)
        self.assertIn("pip install", r.stdout)
        self.assertIn("pyobjc-framework-Cocoa", r.stdout)
        self.assertIn(apple, r.stdout)          # the fix names the interpreter that needs it

    def test_install_from_source_checkout_keeps_symlink(self):
        """Jacob's case: install.sh run from ~/.claude/skills (not a plugin cache) -> plain symlink."""
        src = self.h.home / "skills" / "chrome-tab" / "scripts"
        src.mkdir(parents=True)
        shutil.copy(SCRIPT, src / "chrome-tab")
        shutil.copy(INSTALL, src / "install.sh")
        for f in ("block-bare-open.sh", "block-bare-open.py", "install-hook.py"):
            shutil.copy(HERE / f, src / f)
        r = self.h.run(["sh", str(src / "install.sh")])
        self.assertEqual(r.returncode, 0, r.stderr)
        link = self.h.bin / "chrome-tab"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), (src / "chrome-tab").resolve())

    def test_open_reports_slow_focus_path_when_pyobjc_missing(self):
        """The note `open` prints when the guard had to poll with lsappinfo/open -b."""
        loader = importlib.machinery.SourceFileLoader("chrometab_under_test", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        mod._APPKIT = False
        note = mod.slow_path_note()
        self.assertIn("PyObjC", note)
        self.assertIn("pyobjc-framework-Cocoa", note)
        self.assertIn(sys.executable, note)
        mod._APPKIT = ("fake", "fake")
        self.assertIsNone(mod.slow_path_note())


class SessionCheckTests(unittest.TestCase):
    """scripts/session-check.sh — the plugin's SessionStart hook (never runs for a source checkout)."""

    def setUp(self):
        self.h = FakeHome()

    def tearDown(self):
        self.h.cleanup()

    def hook(self, ver):
        return self.h.cache / ver / "skills" / "chrome-tab" / "scripts" / "session-check.sh"

    def test_replaces_a_stale_cache_symlink_with_the_launcher(self):
        """Tony's state at the moment 0.1.3 lands: no re-run of install.sh needed at all."""
        d1 = self.h.add_version("0.1.1")
        self.h.add_version("0.1.3")
        self.h.set_installed("0.1.3")
        self.h.bin.mkdir(parents=True)
        (self.h.bin / "chrome-tab").symlink_to(d1 / "chrome-tab")
        r = self.h.run(["sh", str(self.hook("0.1.3"))])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("launcher", r.stdout)
        self.assertFalse((self.h.bin / "chrome-tab").is_symlink())
        r = self.h.run([str(self.h.bin / "chrome-tab"), "--version"])
        self.assertIn("0.1.3", r.stdout)

    def test_installs_when_nothing_is_on_path_yet(self):
        self.h.add_version("0.1.3")
        self.h.set_installed("0.1.3")
        r = self.h.run(["sh", str(self.hook("0.1.3"))])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.h.bin / "chrome-tab").exists())

    def test_leaves_a_source_checkout_symlink_alone(self):
        """A symlink to ~/.claude/skills (Jacob's) is deliberate; the hook must not replace it."""
        src = self.h.home / "skills" / "chrome-tab" / "scripts"
        src.mkdir(parents=True)
        shutil.copy(SCRIPT, src / "chrome-tab")
        self.h.add_version("0.1.3")
        self.h.set_installed("0.1.3")
        self.h.bin.mkdir(parents=True)
        (self.h.bin / "chrome-tab").symlink_to(src / "chrome-tab")
        r = self.h.run(["sh", str(self.hook("0.1.3"))])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.h.bin / "chrome-tab").is_symlink())
        self.assertEqual((self.h.bin / "chrome-tab").resolve(), (src / "chrome-tab").resolve())
        self.assertNotIn("launcher", r.stdout)

    def test_quiet_when_everything_is_fine(self):
        d = self.h.add_version("0.1.3")
        self.h.set_installed("0.1.3")
        self.h.run(["sh", str(d / "install.sh")])
        r = self.h.run(["sh", str(self.hook("0.1.3"))])
        self.assertEqual(r.returncode, 0, r.stderr)
        if has_appkit(PY):
            self.assertEqual(r.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
