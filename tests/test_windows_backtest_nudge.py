import datetime as dt
import json
import os
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "windows-backtest-nudge"


def epoch(value):
    return int(dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


class WindowsBacktestNudgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="windows-backtest-nudge-"))
        self.home = self.tmp / "home"
        self.bin = self.home / "bin"
        self.home.mkdir()
        self.bin.mkdir()
        self.page1 = self.tmp / "page1.json"
        self.page2 = self.tmp / "page2.json"
        self.posted = self.tmp / "posted"

    def write_fixture(self, actual_tatu, own_message):
        # Page 1 must contain exactly 100 rows so the script proves it reads page 2.
        rows = []
        for index in range(99):
            rows.append({
                "created_at": "2026-11-20T00:00:00Z",
                "body": f"**msg** de `crouton-alpha` → `Tatu` filler {index}",
            })
        rows.append({
            "created_at": actual_tatu,
            "body": "**msg** de `Tatu` na lane `windows/badiel`\n```coord-json\n{}\n```",
        })
        self.page1.write_text(json.dumps(rows), encoding="utf-8")
        self.page2.write_text(json.dumps([
            {
                "created_at": own_message,
                "body": "**msg** de `crouton-alpha` → `Tatu` own nudge",
            },
        ]), encoding="utf-8")

    def fake_gh(self, rc=0):
        path = self.bin / "gh"
        path.write_text(
            "#!/data/data/com.termux/files/usr/bin/bash\n"
            "case \"$*\" in\n"
            "*page=1*) cat \"$FIXTURE_PAGE1\" ;;\n"
            "*page=2*) cat \"$FIXTURE_PAGE2\" ;;\n"
            "*) exit 9 ;;\n"
            "esac\n"
            f"exit {rc}\n",
            encoding="utf-8",
        )
        path.chmod(0o755)
        return path

    def fake_bus_post(self):
        path = self.bin / "bus-post"
        path.write_text(
            "#!/data/data/com.termux/files/usr/bin/bash\n"
            "printf '%s\\n' \"$*\" >> \"$POSTED_FILE\"\n",
            encoding="utf-8",
        )
        path.chmod(0o755)
        return path

    def run_script(self, *args, now="2026-11-24T05:00:00Z"):
        env = os.environ.copy()
        env.update({
            "HOME": str(self.home),
            "GH_BIN": str(self.fake_gh()),
            "BUS_POST_BIN": str(self.fake_bus_post()),
            "FIXTURE_PAGE1": str(self.page1),
            "FIXTURE_PAGE2": str(self.page2),
            "POSTED_FILE": str(self.posted),
            "NOW_EPOCH": str(epoch(now)),
        })
        return subprocess.run(
            [str(SCRIPT), "--json", *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    def test_uses_latest_message_authored_by_tatu_not_own_mention(self):
        self.write_fixture(
            actual_tatu="2026-11-21T22:29:00Z",
            own_message="2026-11-24T04:30:00Z",
        )
        result = self.run_script("--dry-run")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        row = json.loads(result.stdout)
        self.assertEqual("2026-11-21T22:29:00Z", row["latest_tatu"])
        self.assertEqual("would_nudge", row["action"])
        self.assertEqual(
            (epoch("2026-11-24T05:00:00Z") - epoch("2026-11-21T22:29:00Z")) // 60,
            row["age_min"],
        )
        self.assertFalse(self.posted.exists())

    def test_recent_message_authored_by_tatu_suppresses_nudge(self):
        self.write_fixture(
            actual_tatu="2026-11-24T04:30:00Z",
            own_message="2026-11-24T04:45:00Z",
        )
        result = self.run_script("--dry-run")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        row = json.loads(result.stdout)
        self.assertEqual("2026-11-24T04:30:00Z", row["latest_tatu"])
        self.assertEqual("no_nudge", row["action"])
        self.assertEqual(30, row["age_min"])
        self.assertFalse(self.posted.exists())

    def test_api_failure_fails_closed_without_publishing(self):
        self.write_fixture(
            actual_tatu="2026-11-21T22:29:00Z",
            own_message="2026-11-24T04:30:00Z",
        )
        env = os.environ.copy()
        env.update({
            "HOME": str(self.home),
            "GH_BIN": str(self.fake_gh(rc=1)),
            "BUS_POST_BIN": str(self.fake_bus_post()),
            "FIXTURE_PAGE1": str(self.page1),
            "FIXTURE_PAGE2": str(self.page2),
            "POSTED_FILE": str(self.posted),
            "NOW_EPOCH": str(epoch("2026-11-24T05:00:00Z")),
        })
        result = subprocess.run(
            [str(SCRIPT), "--json"],
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("nenhum nudge publicado", result.stderr)
        self.assertFalse(self.posted.exists())

    def test_help_is_available(self):
        result = subprocess.run(
            [str(SCRIPT), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(0, result.returncode)
        self.assertIn("--dry-run", result.stdout)


if __name__ == "__main__":
    unittest.main()
