import importlib.util
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import boto3
from moto import mock_aws

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "dbbyte_backup.py"
spec = importlib.util.spec_from_file_location("dbbyte_backup_s3", MODULE_PATH)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class BackupS3RoundTripTests(unittest.TestCase):
    @mock_aws
    def test_backup_and_restore_round_trip_against_s3_compatible_mock(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            home = root / "hermes-home"
            home.mkdir()
            os.environ.update({
                "HERMES_HOME": str(home),
                "HOME": str(home),
                "DBBYTE_ACCESS_KEY_ID": "test-access",
                "DBBYTE_SECRET_ACCESS_KEY": "test-secret",
                "DBBYTE_ENDPOINT": "https://s3.amazonaws.com",
                "DBBYTE_REGION": "us-east-1",
                "HERMES_BACKUP_BUCKET": "hermes-backups",
                "HERMES_BACKUP_ENCRYPTION_PASSPHRASE":
                    "test-only-random-passphrase-at-least-32-bytes",
                "HERMES_BACKUP_RETENTION": "7",
            })
            s3 = boto3.client(
                "s3", region_name="us-east-1",
                aws_access_key_id="test-access",
                aws_secret_access_key="test-secret",
            )
            s3.create_bucket(Bucket="hermes-backups")

            def fake_hermes(args, cwd=None, env=None):
                if args[1] == "backup":
                    target = Path(args[args.index("-o") + 1])
                    with zipfile.ZipFile(target, "w") as archive:
                        archive.writestr("state.db", "sample-session-state")
                        archive.writestr("memories/learned.md", "sample memory")
                    return type("Result", (), {"returncode": 0})()
                if args[1] == "import":
                    with zipfile.ZipFile(args[2]) as archive:
                        archive.extractall(cwd)
                    return type("Result", (), {"returncode": 0})()
                raise AssertionError(f"unexpected Hermes command: {args}")

            with patch.object(backup.subprocess, "run", side_effect=fake_hermes):
                backup.backup_once()
                self.assertTrue(list(s3.list_objects_v2(
                    Bucket="hermes-backups", Prefix="backups/"
                ).get("Contents", [])))
                (home / "state.db").unlink(missing_ok=True)
                (home / "memories").mkdir(exist_ok=True)
                (home / "memories" / "learned.md").unlink(missing_ok=True)
                backup.restore_latest()

            self.assertEqual((home / "state.db").read_text(), "sample-session-state")
            self.assertEqual(
                (home / "memories" / "learned.md").read_text(), "sample memory"
            )


if __name__ == "__main__":
    unittest.main()
