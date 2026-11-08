#!/usr/bin/python3
"""Merge safe, non-secret Hermes defaults without overwriting user settings."""
from pathlib import Path
import os
import tempfile
import yaml

home = Path(os.environ.get("HERMES_HOME", "/opt/data"))
path = home / "config.yaml"
config = {}
if path.exists():
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is not None:
        if not isinstance(loaded, dict):
            raise SystemExit("Hermes config.yaml must contain a YAML mapping")
        config = loaded

defaults = {
    "memory": {
        "memory_enabled": True,
        "user_profile_enabled": True,
        "write_approval": False,
    },
    "skills": {"write_approval": True},
    "agent": {
        "tool_use_enforcement": "auto",
        "execution_guidance": "auto",
    },
    "display": {"memory_notifications": "verbose"},
}
for section, values in defaults.items():
    current = config.setdefault(section, {})
    if not isinstance(current, dict):
        raise SystemExit(f"Hermes config section {section!r} must be a mapping")
    for key, value in values.items():
        current.setdefault(key, value)

home.mkdir(parents=True, exist_ok=True)
fd, tmp_name = tempfile.mkstemp(prefix=".config.yaml.", dir=home, text=True)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        yaml.safe_dump(config, stream, sort_keys=False, allow_unicode=True)
    os.chmod(tmp_name, 0o600)
    os.replace(tmp_name, path)
finally:
    if os.path.exists(tmp_name):
        os.unlink(tmp_name)
