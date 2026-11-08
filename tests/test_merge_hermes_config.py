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
                "model:\n  default: custom-model\n"
                "skills:\n  write_approval: false\n",
                encoding="utf-8",
            )
            env = {**os.environ, "HERMES_HOME": str(home)}
            subprocess.run([sys.executable, str(SCRIPT)], env=env, check=True)
            result = yaml.safe_load(config.read_text(encoding="utf-8"))
            self.assertEqual(result["model"]["default"], "custom-model")
            self.assertFalse(result["skills"]["write_approval"])
            self.assertTrue(result["memory"]["memory_enabled"])
            self.assertTrue(result["memory"]["user_profile_enabled"])
            self.assertFalse(result["memory"]["write_approval"])
            self.assertEqual(result["display"]["memory_notifications"], "verbose")
            self.assertEqual(result["agent"]["tool_use_enforcement"], "auto")


if __name__ == "__main__":
    unittest.main()
