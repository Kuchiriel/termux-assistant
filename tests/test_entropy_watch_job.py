import fcntl
import importlib.util
import os
import pathlib
import subprocess
import tempfile
import unittest
from importlib.machinery import SourceFileLoader


ROOT = pathlib.Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "bin" / "entropy-watch-job"
JOBS_AUDIT = ROOT / "bin" / "jobs-audit"
SPEC = importlib.util.spec_from_loader(
    "jobs_audit_module", SourceFileLoader("jobs_audit_module", str(JOBS_AUDIT))
)
jobs_audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(jobs_audit)


class EntropyWatchJobTests(unittest.TestCase):
    def make_fake(self, tmp, body="echo 'fake findings=1'\nexit 0\n"):
        fake = tmp / "fake-entropy-watch"
        fake.write_text(
            "#!/data/data/com.termux/files/usr/bin/bash\n" + body,
            encoding="utf-8",
        )
        fake.chmod(0o755)
        return fake

    def env_for(self, state, fake):
        env = os.environ.copy()
        env["ENTROPY_STATE_DIR"] = str(state)
        env["ENTROPY_WATCH_BIN"] = str(fake)
        env["ENTROPY_TIMEOUT"] = "5"
        return env

    def test_help_is_read_only(self):
        result = subprocess.run(
            [str(WRAPPER), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("Uso: entropy-watch-job", result.stdout)

    def test_success_writes_trace_and_output(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="entropy-watch-job-ok-"))
        state = tmp / "state"
        state.mkdir()
        fake = self.make_fake(tmp)
        env = self.env_for(state, fake)

        result = subprocess.run(
            [str(WRAPPER)],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("fake findings=1", result.stdout)
        trace = (state / "job-entropy-watch.trace").read_text(encoding="utf-8")
        self.assertIn("rc=0", trace)
        self.assertIn("fake findings=1", (state / "entropy-watch-job.out").read_text(encoding="utf-8"))

    def test_busy_lock_skips_sensor_without_failure(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="entropy-watch-job-lock-"))
        state = tmp / "state"
        state.mkdir()
        marker = tmp / "sensor-ran"
        fake = self.make_fake(tmp, f"touch '{marker}'\nexit 0\n")
        env = self.env_for(state, fake)
        lock_path = state / "entropy-watch-job.lock"
        with lock_path.open("w", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run(
                [str(WRAPPER)],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("execucao concorrente ignorada", result.stdout)
        self.assertFalse(marker.exists())
        trace = (state / "job-entropy-watch.trace").read_text(encoding="utf-8")
        self.assertIn("lock-busy", trace)

    def test_timeout_is_recorded(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="entropy-watch-job-timeout-"))
        state = tmp / "state"
        state.mkdir()
        fake = self.make_fake(tmp, "sleep 5\nexit 0\n")
        env = self.env_for(state, fake)
        env["ENTROPY_TIMEOUT"] = "1"

        result = subprocess.run(
            [str(WRAPPER)],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        self.assertEqual(124, result.returncode, result.stdout + result.stderr)
        trace = (state / "job-entropy-watch.trace").read_text(encoding="utf-8")
        self.assertIn("rc=124", trace)

    def test_jobs_audit_knows_entropy_and_existing_job_traces(self):
        self.assertIn("job-entropy-watch.trace", jobs_audit.RASTROS["entropy-watch-job"])
        self.assertIn("state:fleet-retry/retry.log", jobs_audit.RASTROS["fleet-retry"])
        self.assertIn("state:route-watch/route-watch.log", jobs_audit.RASTROS["route-watch"])
        self.assertIn("state:job-backlog-nudge.trace", jobs_audit.RASTROS["backlog-nudge"])

    def test_state_relative_log_is_not_treated_as_repo_relative(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="jobs-audit-state-path-"))
        home = tmp / "home"
        state = home / ".local" / "state"
        log = state / "fleet-retry" / "retry.log"
        trace = state / "job-fleet-retry.trace"
        log.parent.mkdir(parents=True)
        log.write_text("recent\n", encoding="utf-8")
        trace.write_text("old\n", encoding="utf-8")
        os.utime(log, (2000, 2000))
        os.utime(trace, (1000, 1000))
        old_home = jobs_audit.HOME
        try:
            jobs_audit.HOME = str(home)
            mtime, path = jobs_audit.ultimo_rastro("fleet-retry")
        finally:
            jobs_audit.HOME = old_home

        self.assertEqual(str(log), path)
        self.assertEqual(2000, int(mtime))

    def test_repo_relative_inventory_is_still_resolved_against_mesh(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="jobs-audit-repo-path-"))
        home = tmp / "home"
        state = home / ".local" / "state"
        mesh = tmp / "ai-mesh"
        state.mkdir(parents=True)
        inventory = mesh / "inventory" / "termux.json"
        inventory.parent.mkdir(parents=True)
        inventory.write_text("{}\n", encoding="utf-8")
        old_home = jobs_audit.HOME
        old_mesh = os.environ.get("AI_MESH_DIR")
        try:
            jobs_audit.HOME = str(home)
            os.environ["AI_MESH_DIR"] = str(mesh)
            mtime, path = jobs_audit.ultimo_rastro("publish-inventory")
        finally:
            jobs_audit.HOME = old_home
            if old_mesh is None:
                os.environ.pop("AI_MESH_DIR", None)
            else:
                os.environ["AI_MESH_DIR"] = old_mesh

        self.assertEqual(str(inventory), path)
        self.assertIsNotNone(mtime)


if __name__ == "__main__":
    unittest.main()
