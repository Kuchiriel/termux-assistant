import json
import os
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SHIM = ROOT / "bin" / "manifest-check"


class ManifestCheckShimTests(unittest.TestCase):
    def test_shim_uses_absolute_termux_interpreter_and_points_to_canonical(self):
        text = SHIM.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/data/data/com.termux/files/usr/bin/bash\n"))
        self.assertIn("shared/scripts/manifest-check", text)
        self.assertIn("exec ", text)
        self.assertIn("shim", text.lower())

    def test_shim_forwards_arguments_and_exit_code(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="manifest-check-shim-"))
        canonical = tmp / "shared" / "scripts" / "manifest-check"
        canonical.parent.mkdir(parents=True)
        canonical.write_text(
            "#!/data/data/com.termux/files/usr/bin/python3\n"
            "import json,sys\n"
            "print(json.dumps({'argv': sys.argv[1:]}))\n"
            "sys.exit(7)\n",
            encoding="utf-8",
        )
        canonical.chmod(0o755)
        env = os.environ.copy()
        env["AI_MESH_DIR"] = str(tmp)

        result = subprocess.run(
            [str(SHIM), "--check", "--json"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        self.assertEqual(7, result.returncode, result.stdout + result.stderr)
        self.assertEqual(["--check", "--json"], json.loads(result.stdout)["argv"])

    def test_missing_canonical_fails_closed(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="manifest-check-missing-"))
        env = os.environ.copy()
        env["AI_MESH_DIR"] = str(tmp)

        result = subprocess.run(
            [str(SHIM), "--check"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn("canonical ausente", result.stderr)


if __name__ == "__main__":
    unittest.main()
