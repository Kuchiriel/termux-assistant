import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from importlib.machinery import SourceFileLoader


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "manifest-check"
SPEC = importlib.util.spec_from_loader(
    "manifest_check_module", SourceFileLoader("manifest_check_module", str(SCRIPT))
)
manifest_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manifest_check)


class ManifestCheckScriptsTests(unittest.TestCase):
    def test_declared_scripts_are_classified_as_present_executable_missing_or_not_executable(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="manifest-check-scripts-"))
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "ok-tool").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (bin_dir / "ok-tool").chmod(0o755)
        (bin_dir / "plain-tool").write_text("data\n", encoding="utf-8")
        (bin_dir / "plain-tool").chmod(0o644)

        report = manifest_check.check_scripts(
            ["ok-tool", "plain-tool", "missing-tool"], bin_dir=str(bin_dir)
        )

        self.assertEqual(3, report["declarados"])
        self.assertEqual(["missing-tool"], report["ausentes"])
        self.assertEqual(["plain-tool"], report["nao_executaveis"])
        rows = {item["nome"]: item for item in report["scripts"]}
        self.assertTrue(rows["ok-tool"]["executavel"])
        self.assertFalse(rows["plain-tool"]["executavel"])
        self.assertFalse(rows["missing-tool"]["existe"])

    def test_check_mode_fails_for_missing_declared_script(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="manifest-check-contract-"))
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        manifest = tmp / "termux.json"
        manifest.write_text(json.dumps({
            "host": "termux",
            "scripts": ["missing-tool"],
            "servicos": [],
        }), encoding="utf-8")

        old_manifest = manifest_check.MANIFEST
        old_bin_dir = manifest_check.BIN_DIR
        try:
            manifest_check.MANIFEST = str(manifest)
            manifest_check.BIN_DIR = str(bin_dir)
            out = StringIO()
            with redirect_stdout(out):
                rc = manifest_check.main(["--json", "--check"])
        finally:
            manifest_check.MANIFEST = old_manifest
            manifest_check.BIN_DIR = old_bin_dir

        self.assertEqual(1, rc)
        report = json.loads(out.getvalue())
        self.assertEqual(["missing-tool"], report["scripts_ausentes"])
        self.assertEqual(1, report["scripts_declarados"])

    def test_check_mode_passes_when_declared_script_is_executable(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="manifest-check-contract-ok-"))
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        tool = bin_dir / "ok-tool"
        tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        tool.chmod(0o755)
        manifest = tmp / "termux.json"
        manifest.write_text(json.dumps({
            "host": "termux",
            "scripts": ["ok-tool"],
            "servicos": [],
        }), encoding="utf-8")

        old_manifest = manifest_check.MANIFEST
        old_bin_dir = manifest_check.BIN_DIR
        try:
            manifest_check.MANIFEST = str(manifest)
            manifest_check.BIN_DIR = str(bin_dir)
            out = StringIO()
            with redirect_stdout(out):
                rc = manifest_check.main(["--json", "--check"])
        finally:
            manifest_check.MANIFEST = old_manifest
            manifest_check.BIN_DIR = old_bin_dir

        self.assertEqual(0, rc)
        report = json.loads(out.getvalue())
        self.assertEqual([], report["scripts_ausentes"])
        self.assertEqual([], report["scripts_nao_executaveis"])


if __name__ == "__main__":
    unittest.main()
