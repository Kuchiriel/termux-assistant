import importlib.util
import os
import pathlib
import subprocess
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
LAB = ROOT / "bin" / "lab"
LESSON = ROOT / "bin" / "lesson"


class P0ToolingTests(unittest.TestCase):
    def test_lab_help_resolves_route_defaults_without_literal_template(self):
        env = os.environ.copy()
        env.pop("TA_LINUX_HOST6", None)
        env.pop("TA_LINUX_LAN", None)
        result = subprocess.run(
            ["bash", str(LAB), "--help"], capture_output=True, text=True, timeout=10, env=env
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("ipv6=fd7a:115c:a1e0::7f01:64bd", result.stdout)
        self.assertIn("lan=192.168.15.10", result.stdout)
        self.assertNotIn("${", result.stdout)

    def test_lab_help_resolves_route_overrides(self):
        env = os.environ.copy()
        env["TA_LINUX_HOST6"] = "2001:db8::10"
        env["TA_LINUX_LAN"] = "192.0.2.50"
        result = subprocess.run(
            ["bash", str(LAB), "--help"], capture_output=True, text=True, timeout=10, env=env
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("ipv6=2001:db8::10", result.stdout)
        self.assertIn("lan=192.0.2.50", result.stdout)
        self.assertNotIn("${", result.stdout)

    def test_lesson_help_is_read_only(self):
        home = pathlib.Path(tempfile.mkdtemp(prefix="lesson-help-"))
        env = os.environ.copy()
        env["HOME"] = str(home)
        result = subprocess.run(
            ["bash", str(LESSON), "--help"], capture_output=True, text=True, timeout=10, env=env
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("uso: lesson", result.stdout)
        self.assertNotIn("registrado em", result.stdout)
        self.assertFalse((home / "ai-mesh" / "docs" / "ARMADILHAS.md").exists())

    def test_lesson_rejects_missing_required_arguments_without_writing(self):
        home = pathlib.Path(tempfile.mkdtemp(prefix="lesson-invalid-"))
        env = os.environ.copy()
        env["HOME"] = str(home)
        result = subprocess.run(
            ["bash", str(LESSON), "somente-um-argumento"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("exige 4 argumentos", result.stderr)
        self.assertFalse((home / "ai-mesh" / "docs" / "ARMADILHAS.md").exists())

    def test_ta_status_propagates_child_failure(self):
        spec = importlib.util.spec_from_loader(
            "ta_p0_module", SourceFileLoader("ta_p0_module", str(ROOT / "ta.py"))
        )
        ta = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ta)

        with mock.patch.object(ta, "run", side_effect=[(255, "lab down"), (0, "house ok")]), \
             mock.patch("builtins.print"):
            rc = ta.status(None)
        self.assertEqual(1, rc)

        with mock.patch.object(ta, "run", side_effect=[(0, "lab ok"), (0, "house ok")]), \
             mock.patch("builtins.print"):
            rc = ta.status(None)
        self.assertEqual(0, rc)


if __name__ == "__main__":
    unittest.main()
