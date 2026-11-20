import importlib.util
import json
import pathlib
import unittest
from importlib.machinery import SourceFileLoader


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "entropy-watch"
SPEC = importlib.util.spec_from_loader(
    "entropy_watch_module", SourceFileLoader("entropy_watch_module", str(SCRIPT))
)
entropy_watch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entropy_watch)


class EntropyWatchManifestTests(unittest.TestCase):
    def test_current_manifest_contract_produces_service_and_script_findings(self):
        payload = {
            "declarados": 2,
            "fora_do_ar": 1,
            "servicos": [
                {"nome": "alive-service", "vivo": True},
                {"nome": "dead-service", "vivo": False},
            ],
            "scripts_declarados": 3,
            "scripts_ausentes": ["missing-tool"],
            "scripts_nao_executaveis": ["plain-tool"],
        }

        findings = entropy_watch.manifest_findings(payload)
        keys = [item["key"] for item in findings]

        self.assertEqual([
            "service:dead-service",
            "script-ausente:missing-tool",
            "script-sem-execucao:plain-tool",
        ], keys)
        self.assertTrue(all(item["sensor"] == "manifest-check" for item in findings))
        self.assertIn("instalar do source canonico", findings[1]["fix"])
        self.assertIn("corrigir permissao", findings[2]["fix"])

    def test_legacy_down_dead_payload_remains_compatible(self):
        payload = {"down": [{"name": "legacy-dead", "port": 9999}]}

        findings = entropy_watch.manifest_findings(payload)

        self.assertEqual(["service:legacy-dead"], [item["key"] for item in findings])

    def test_findings_uses_current_manifest_contract(self):
        payload = {
            "fora_do_ar": 1,
            "servicos": [{"nome": "dead-service", "vivo": False}],
            "scripts_ausentes": ["missing-tool"],
            "scripts_nao_executaveis": [],
        }
        encoded = json.dumps(payload)
        old_run = entropy_watch.run

        def fake_run(cmd, timeout=60):
            command = " ".join(cmd)
            if "manifest-check" in command:
                return 0, encoded
            if "state-audit" in command:
                return 0, json.dumps({"orfaos": 0, "lista": []})
            if "jobs-audit" in command:
                return 0, "QUEBRADOS: 0"
            if "--is-inside-work-tree" in command:
                return 1, ""
            if "--check" in command:
                return 0, "OK"
            return 0, ""

        try:
            entropy_watch.run = fake_run
            findings = entropy_watch.findings()
        finally:
            entropy_watch.run = old_run

        manifest_findings = [item for item in findings if item["sensor"] == "manifest-check"]
        self.assertEqual([
            "service:dead-service",
            "script-ausente:missing-tool",
        ], [item["key"] for item in manifest_findings])


if __name__ == "__main__":
    unittest.main()
