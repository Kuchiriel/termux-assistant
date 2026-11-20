import importlib.util
import json
import pathlib
import tempfile
import unittest
from importlib.machinery import SourceFileLoader


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "state-audit"
SPEC = importlib.util.spec_from_loader(
    "state_audit_module", SourceFileLoader("state_audit_module", str(SCRIPT))
)
state_audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(state_audit)


class StateAuditManifestsTests(unittest.TestCase):
    def test_maintained_file_is_not_reported_as_orphan(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="state-audit-manifest-"))
        state = tmp / ".local" / "state"
        docs = tmp / "docs"
        sources = tmp / "bin"
        state.mkdir(parents=True)
        docs.mkdir()
        sources.mkdir()
        (state / "keep.txt").write_text("live\n", encoding="utf-8")
        (state / "unknown.txt").write_text("maybe orphan\n", encoding="utf-8")
        (docs / "quarentena-state-orfaos-test.json").write_text(json.dumps({
            "id": "test",
            "mantidos": [
                {"arquivo": "keep.txt", "motivo": "marcador vivo do plugin"}
            ],
        }), encoding="utf-8")

        old_state = state_audit.STATE
        old_sources = state_audit.FONTES
        old_manifest_dir = state_audit.MANIFEST_DIR
        old_manifest_glob = state_audit.MANIFEST_GLOB
        try:
            state_audit.STATE = str(state)
            state_audit.FONTES = [str(sources)]
            state_audit.MANIFEST_DIR = str(docs)
            state_audit.MANIFEST_GLOB = "quarentena-state-orfaos-*.json"
            report = state_audit.auditor()
        finally:
            state_audit.STATE = old_state
            state_audit.FONTES = old_sources
            state_audit.MANIFEST_DIR = old_manifest_dir
            state_audit.MANIFEST_GLOB = old_manifest_glob

        self.assertEqual(1, report["orfaos"])
        self.assertEqual(["unknown.txt"], [item["arquivo"] for item in report["lista"]])
        self.assertEqual(1, report["mantidos"])
        kept = report["lista_mantidos"][0]
        self.assertEqual("keep.txt", kept["arquivo"])
        self.assertEqual("marcador vivo do plugin", kept["motivo"])
        self.assertEqual("quarentena-state-orfaos-test.json", kept["manifesto"])

    def test_active_generated_sidecar_is_not_reported_as_orphan(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="state-audit-sidecar-"))
        state = tmp / "state"
        docs = tmp / "docs"
        sources = tmp / "bin"
        state.mkdir()
        docs.mkdir()
        sources.mkdir()
        (state / "ta-state.cache").write_text("cache\n", encoding="utf-8")
        (state / "ta-state.cache.meta").write_text("fingerprint\n", encoding="utf-8")
        (sources / "ta-state.py").write_text('CACHE = "ta-state.cache"\n', encoding="utf-8")

        old_state = state_audit.STATE
        old_sources = state_audit.FONTES
        old_manifest_dir = state_audit.MANIFEST_DIR
        try:
            state_audit.STATE = str(state)
            state_audit.FONTES = [str(sources)]
            state_audit.MANIFEST_DIR = str(docs)
            report = state_audit.auditor()
        finally:
            state_audit.STATE = old_state
            state_audit.FONTES = old_sources
            state_audit.MANIFEST_DIR = old_manifest_dir

        self.assertEqual(0, report["orfaos"])
        self.assertEqual(1, report["mantidos"])
        self.assertEqual("ta-state.cache.meta", report["lista_mantidos"][0]["arquivo"])

    def test_malformed_manifest_does_not_crash_audit(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="state-audit-bad-manifest-"))
        state = tmp / "state"
        docs = tmp / "docs"
        sources = tmp / "bin"
        state.mkdir()
        docs.mkdir()
        sources.mkdir()
        (state / "unknown.txt").write_text("orphan\n", encoding="utf-8")
        (docs / "quarentena-state-orfaos-bad.json").write_text("{not-json", encoding="utf-8")

        old_state = state_audit.STATE
        old_sources = state_audit.FONTES
        old_manifest_dir = state_audit.MANIFEST_DIR
        try:
            state_audit.STATE = str(state)
            state_audit.FONTES = [str(sources)]
            state_audit.MANIFEST_DIR = str(docs)
            report = state_audit.auditor()
        finally:
            state_audit.STATE = old_state
            state_audit.FONTES = old_sources
            state_audit.MANIFEST_DIR = old_manifest_dir

        self.assertEqual(1, report["orfaos"])
        self.assertEqual(0, report["mantidos"])


if __name__ == "__main__":
    unittest.main()
