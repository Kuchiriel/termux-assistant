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
        self.assertIn("job-fleet-retry.trace", jobs_audit.RASTROS["fleet-retry"])
        self.assertIn("job-route-watch.trace", jobs_audit.RASTROS["route-watch"])
        self.assertIn("job-backlog-nudge.trace", jobs_audit.RASTROS["backlog-nudge"])


if __name__ == "__main__":
    unittest.main()
