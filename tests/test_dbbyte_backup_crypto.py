import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "dbbyte_backup.py"
spec = importlib.util.spec_from_file_location("dbbyte_backup", MODULE_PATH)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class BackupCryptoTests(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("HERMES_BACKUP_ENCRYPTION_PASSPHRASE")
        os.environ["HERMES_BACKUP_ENCRYPTION_PASSPHRASE"] = (
            "test-only-random-passphrase-at-least-32-bytes"
        )
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("HERMES_BACKUP_ENCRYPTION_PASSPHRASE", None)
        else:
            os.environ["HERMES_BACKUP_ENCRYPTION_PASSPHRASE"] = self.previous
        self.temp.cleanup()

    def test_round_trip(self):
        original = self.root / "plain.bin"
        encrypted = self.root / "encrypted.bin"
        restored = self.root / "restored.bin"
        payload = os.urandom(2_500_000)
        original.write_bytes(payload)
        backup.encrypt(original, encrypted)
        backup.decrypt(encrypted, restored)
        self.assertEqual(restored.read_bytes(), payload)

    def test_tampering_is_rejected(self):
        original = self.root / "plain.bin"
        encrypted = self.root / "encrypted.bin"
        restored = self.root / "restored.bin"
        original.write_bytes(b"important Hermes state" * 1000)
        backup.encrypt(original, encrypted)
        damaged = bytearray(encrypted.read_bytes())
        damaged[-1] ^= 1
        encrypted.write_bytes(damaged)
        with self.assertRaises(RuntimeError):
            backup.decrypt(encrypted, restored)
        self.assertFalse(restored.exists())


if __name__ == "__main__":
    unittest.main()
