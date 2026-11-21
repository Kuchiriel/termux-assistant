import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "memory-termux.js"


class MemoryTermuxAutoWakePromptTests(unittest.TestCase):
    def test_canonical_contains_runtime_idle_observability_features(self):
        text = PLUGIN.read_text(encoding="utf-8")
        self.assertIn("function traceIdle(data)", text)
        self.assertIn('auto-improve`, "--once"', text)
        self.assertIn('auto-improve`, "--snapshot"', text)
        self.assertIn('"peek"', text)
        self.assertIn('"budget"', text)
        self.assertLess(text.index('"peek"'), text.index('"budget"'))

    def test_synthetic_prompt_closes_claim_lifecycle(self):
        text = PLUGIN.read_text(encoding="utf-8")
        self.assertIn('auto-wake complete \\"<a mesma tarefa>\\" --reason \\"<evidencia>\\"', text)
        self.assertIn('auto-wake requeue \\"<a mesma tarefa>\\" --reason \\"<motivo>\\"', text)
        self.assertIn("auto-wake enqueue", text)

    def test_plugin_does_not_embed_public_ip_or_token(self):
        text = PLUGIN.read_text(encoding="utf-8")
        self.assertNotIn("100.121.100.103", text)
        self.assertNotIn("187.106.139.139", text)
        self.assertNotIn("Bearer ", text)


if __name__ == "__main__":
    unittest.main()
