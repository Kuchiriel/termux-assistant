import os
import pathlib
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
TERMUX_BIN = pathlib.Path("/data/data/com.termux/files/usr/bin")


class RuntimeShebangTests(unittest.TestCase):
    def test_every_executable_has_a_valid_termux_absolute_shebang(self):
        broken = []
        checked = 0
        for path in sorted(BIN.iterdir()):
            if not path.is_file() or not (path.stat().st_mode & 0o111):
                continue
            first = path.read_bytes().splitlines()[0].decode("utf-8", "replace").strip() if path.stat().st_size else ""
            if not first.startswith("#!"):
                continue
            checked += 1
            if first.startswith("#!/usr/bin/env"):
                broken.append(f"{path.name}: /usr/bin/env nao existe no Termux")
                continue
            interpreter = first[2:].split()[0]
            if not interpreter.startswith(str(TERMUX_BIN)):
                broken.append(f"{path.name}: interpretador nao absoluto do Termux: {interpreter}")
            elif not pathlib.Path(interpreter).exists():
                broken.append(f"{path.name}: interpretador ausente: {interpreter}")
        self.assertEqual([], broken)
        self.assertGreater(checked, 20)

    def test_sync_status_executes_directly_with_its_shebang(self):
        result = subprocess.run(
            [str(BIN / "sync-status"), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("usage:", result.stdout)


if __name__ == "__main__":
    unittest.main()
