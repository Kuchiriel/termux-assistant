import json
import os
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "backlog-nudge"


class BacklogNudgeTraceTests(unittest.TestCase):
    def test_every_run_writes_start_and_rc_even_when_backlog_is_empty(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="backlog-nudge-trace-"))
        home = tmp / "home"
        state = home / ".local" / "state" / "termux-assistant"
        bin_dir = home / "bin"
        state.mkdir(parents=True)
        bin_dir.mkdir()
        (state / "backlog.json").write_text(json.dumps({"items": []}), encoding="utf-8")
        fake_backlog = bin_dir / "backlog"
        fake_backlog.write_text("#!/data/data/com.termux/files/usr/bin/bash\nexit 0\n", encoding="utf-8")
        fake_backlog.chmod(0o755)
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

        for _ in range(2):
            result = subprocess.run(
                [str(SCRIPT)],
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        trace = home / ".local" / "state" / "job-backlog-nudge.trace"
        lines = trace.read_text(encoding="utf-8").splitlines()
        self.assertEqual(4, len(lines))
        self.assertTrue(lines[0].endswith(" start"))
        self.assertTrue(lines[1].endswith(" rc=0"))
        self.assertTrue(lines[2].endswith(" start"))
        self.assertTrue(lines[3].endswith(" rc=0"))


if __name__ == "__main__":
    unittest.main()
