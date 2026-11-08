import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "merge_hermes_config.py"


class HermesConfigMergeTests(unittest.TestCase):
    def test_adds_defaults_without_overwriting_user_choices(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            config = home / "config.yaml"
            config.write_text(
                "model:\n  default: custom-model\n  provider: custom:my-model\n"
                "providers:\n  my-model:\n    api: https://example.invalid/v1\n    key_env: MY_MODEL_KEY\n"
                "skills:\n  write_approval: false\n",
                encoding="utf-8",
            )
            env = {**os.environ, "HERMES_HOME": str(home)}
            subprocess.run([sys.executable, str(SCRIPT)], env=env, check=True)
            result = yaml.safe_load(config.read_text(encoding="utf-8"))
            self.assertEqual(result["model"]["default"], "custom-model")
            self.assertEqual(result["model"]["provider"], "custom:my-model")
            self.assertEqual(result["providers"]["my-model"]["api"], "https://example.invalid/v1")
            self.assertEqual(result["providers"]["groq"]["key_env"], "GROQ_API_KEY")
            self.assertFalse(result["skills"]["write_approval"])
            self.assertTrue(result["memory"]["memory_enabled"])
            self.assertTrue(result["memory"]["user_profile_enabled"])
            self.assertFalse(result["memory"]["write_approval"])
            self.assertEqual(result["display"]["memory_notifications"], "verbose")
            self.assertTrue(result["web"]["keyless_fallback"])
            self.assertTrue(result["web"]["keyless_rescue"])
            self.assertEqual(result["agent"]["tool_use_enforcement"], "auto")



    def test_configures_free_groq_model_on_fresh_profile(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            env = {**os.environ, "HERMES_HOME": str(home)}
            subprocess.run([sys.executable, str(SCRIPT)], env=env, check=True)
            result = yaml.safe_load((home / "config.yaml").read_text(encoding="utf-8"))
            self.assertEqual(result["model"]["provider"], "custom:groq")
            self.assertEqual(result["model"]["default"], "openai/gpt-oss-120b")
            self.assertEqual(result["providers"]["groq"]["api"], "https://api.groq.com/openai/v1")
            self.assertEqual(result["providers"]["groq"]["key_env"], "GROQ_API_KEY")

if __name__ == "__main__":
    unittest.main()
