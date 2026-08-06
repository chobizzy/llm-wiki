"""Tests for agent skills-dir resolution.

Reporting (`doctor`, `info`) must agree with installing about where each agent's
skills live. They drifted once: Hermes on Windows installs to %LOCALAPPDATA%\\hermes
via HERMES_HOME, but reporting only ever looked at ~/.hermes, so a fully installed
Hermes was labelled "not installed".

Stdlib unittest only — the repo has no runtime dependencies and the test
suite keeps it that way. Run: python -m unittest discover tests -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from llm_wiki import cli


class AgentInstallDirsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "home"
        self.home.mkdir()
        self.addCleanup(self._tmp.cleanup)
        patcher = mock.patch.object(cli, "HOME", self.home)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _resolve(self, hermes_home: str | None):
        env = {"HERMES_HOME": hermes_home} if hermes_home else {}
        with mock.patch.dict(cli.os.environ, env, clear=True):
            with mock.patch.object(cli, "_read_config_value", return_value=""):
                return cli._agent_install_dirs()

    def test_hermes_follows_hermes_home_when_relocated(self):
        relocated = Path(self._tmp.name) / "AppData" / "Local" / "hermes"
        dirs = self._resolve(str(relocated))

        self.assertIn(
            (relocated / "skills", f"{relocated}/skills/ (Hermes active profile)"),
            dirs,
        )
        # The stale ~/.hermes entry must not also be reported, or `info` lists
        # Hermes twice — once installed, once "not installed".
        self.assertNotIn(self.home / ".hermes" / "skills", [d for d, _ in dirs])

    def test_hermes_falls_back_to_home_when_unset(self):
        dirs = self._resolve(None)
        self.assertIn(self.home / ".hermes" / "skills", [d for d, _ in dirs])

    def test_hermes_home_pointing_at_default_is_not_duplicated(self):
        dirs = self._resolve(str(self.home / ".hermes"))
        hermes = [d for d, _ in dirs if "hermes" in str(d).lower()]
        self.assertEqual(hermes, [self.home / ".hermes" / "skills"])

    def test_every_bundled_agent_is_still_reported(self):
        dirs = self._resolve(None)
        self.assertEqual(len(dirs), len(cli.GLOBAL_AGENT_DIRS))

    def test_named_profiles_are_appended(self):
        profiles = self.home / ".hermes" / "profiles"
        (profiles / "work").mkdir(parents=True)
        dirs = self._resolve(None)
        self.assertIn(profiles / "work" / "skills", [d for d, _ in dirs])


if __name__ == "__main__":
    unittest.main()
