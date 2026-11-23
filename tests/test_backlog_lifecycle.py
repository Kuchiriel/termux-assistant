import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "backlog"


class BacklogLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="backlog-lifecycle-")
        self.home = pathlib.Path(self.tmp.name)
        self.state = self.home / ".local/state/termux-assistant/backlog.json"

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, check=True):
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if check:
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        return result

    def item(self, item_id=1):
        data = json.loads(self.state.read_text(encoding="utf-8"))
        return next(item for item in data["items"] if item["id"] == item_id)

    def test_open_blocked_requeue_done_keeps_append_only_history(self):
        self.run_cli("add", "measure task", "--owner", "tester", "--host", "termux")
        self.assertEqual("open", self.item()["status"])

        self.run_cli("block", 1, "--reason", "kernel RUNNING")
        item = self.item()
        self.assertEqual("blocked", item["status"])
        self.assertEqual("kernel RUNNING", item["reason"])
        self.assertIn("blocked_at", item)

        self.run_cli("requeue", 1, "--reason", "kernel COMPLETE")
        item = self.item()
        self.assertEqual("open", item["status"])
        self.assertIn("requeued_at", item)

        self.run_cli("done", 1, "--evidence", "PR#123")
        item = self.item()
        self.assertEqual("done", item["status"])
        self.assertEqual("PR#123", item["evidence"])
        self.assertEqual(
            ["open", "blocked", "open", "done"],
            [event["to"] for event in item["history"]],
        )

    def test_list_and_check_distinguish_open_from_blocked(self):
        self.run_cli("add", "blocked task", "--owner", "tester", "--host", "linux")
        self.run_cli("block", 1, "--reason", "waiting for official output")

        default = self.run_cli("list").stdout
        blocked = self.run_cli("list", "--blocked").stdout
        check = self.run_cli("check").stdout

        self.assertNotIn("blocked task", default)
        self.assertIn("[blocked]", blocked)
        self.assertIn("abertos=0 blocked=1 total=1", check)
        self.assertIn("waiting for official output", check)

    def test_unknown_item_fails_closed(self):
        result = self.run_cli("block", 99, "--reason", "missing", check=False)
        self.assertEqual(2, result.returncode)
        self.assertIn("não encontrado", result.stderr)


if __name__ == "__main__":
    unittest.main()
