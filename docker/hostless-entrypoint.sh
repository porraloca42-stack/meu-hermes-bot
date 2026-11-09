#!/bin/sh
# Hostless startup: run directly as the unprivileged Hermes account.
# No s6 init, chown, chmod, setgroups, setgid, or setuid calls.
set -eu

export PATH="/opt/hermes/.venv/bin:/opt/hermes/bin:$PATH"
umask 077

echo "[hostless-start] runtime identity: $(id)"
# Prefer Hostless's 2 GiB cache mount. If its ownership blocks UID 10000,
# use /tmp (500 MiB) rather than attempting forbidden chmod/chown operations.
candidate="${HERMES_HOME:-/app/.cache/hermes-home}"
if mkdir -p "$candidate" 2>/dev/null && [ -w "$candidate" ]; then
  HERMES_HOME="$candidate"
else
  HERMES_HOME=/tmp/hermes-home
  mkdir -p "$HERMES_HOME"
  if [ ! -w "$HERMES_HOME" ]; then
    echo "[hostless-start] ERROR: neither /app/.cache nor /tmp is writable by UID $(id -u)"
    exit 73
  fi
  echo "[hostless-start] cache mount unavailable to UID $(id -u); using /tmp (500 MiB limit)"
fi
export HERMES_HOME HOME="$HERMES_HOME" HERMES_WRITE_SAFE_ROOT="$HERMES_HOME"
echo "[hostless-start] preparing Hermes home at $HERMES_HOME"
probe="$HERMES_HOME/.write-test-$"
: > "$probe"
rm -f "$probe"
probe="$HERMES_HOME/.write-test-$$"
: > "$probe"
rm -f "$probe"

PERSISTENCE_READY=1
for name in DBBYTE_ACCESS_KEY_ID DBBYTE_SECRET_ACCESS_KEY HERMES_BACKUP_ENCRYPTION_PASSPHRASE DBBYTE_ENDPOINT DBBYTE_REGION HERMES_BACKUP_BUCKET; do
  eval 'value=${'"$name"'-}'
  if [ -z "$value" ]; then
    echo "[hostless-start] WARNING: $name is missing; DBByte restore/backup will be skipped"
    PERSISTENCE_READY=0
  fi
done

mkdir -p \
  "$HERMES_HOME/backups" "$HERMES_HOME/cron" "$HERMES_HOME/sessions" \
  "$HERMES_HOME/logs/gateways" "$HERMES_HOME/hooks" "$HERMES_HOME/memories" \
  "$HERMES_HOME/skills" "$HERMES_HOME/skins" "$HERMES_HOME/plans" \
  "$HERMES_HOME/workspace" "$HERMES_HOME/home" "$HERMES_HOME/pairing" \
  "$HERMES_HOME/platforms/pairing"

if [ "$PERSISTENCE_READY" -eq 1 ]; then
  /usr/bin/python3 /opt/hermes/scripts/dbbyte_backup.py restore
else
  echo "[hostless-start] continuing without remote persistence; data may be lost on restart"
fi

if [ ! -f "$HERMES_HOME/config.yaml" ] && [ -f /opt/hermes/cli-config.yaml.example ]; then
  cp /opt/hermes/cli-config.yaml.example "$HERMES_HOME/config.yaml"
fi
if [ ! -f "$HERMES_HOME/.env" ]; then touch "$HERMES_HOME/.env"; fi
if [ ! -f "$HERMES_HOME/SOUL.md" ] && [ -f /opt/hermes/docker/SOUL.md ]; then
  cp /opt/hermes/docker/SOUL.md "$HERMES_HOME/SOUL.md"
fi
if [ ! -f "$HERMES_HOME/AGENTS.md" ] && [ -f /opt/hermes/profile-seed/AGENTS.md ]; then
  cp /opt/hermes/profile-seed/AGENTS.md "$HERMES_HOME/AGENTS.md"
fi
if [ -d /opt/hermes/profile-seed/skills ]; then
  cp -Rn /opt/hermes/profile-seed/skills/. "$HERMES_HOME/skills/" || true
fi
chmod 600 "$HERMES_HOME/.env" 2>/dev/null || true
/usr/bin/python3 /opt/hermes/scripts/merge_hermes_config.py

if [ -z "${API_SERVER_KEY:-}" ] && ! grep -q '^API_SERVER_KEY=..*' "$HERMES_HOME/.env"; then
  key="$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  printf 'API_SERVER_KEY=%s\n' "$key" >> "$HERMES_HOME/.env"
fi

if [ "$PERSISTENCE_READY" -eq 1 ]; then
  /usr/bin/python3 /opt/hermes/scripts/dbbyte_backup.py loop &
  echo "[hostless-start] encrypted DBByte backup loop started"
fi

echo "[hostless-start] starting Hermes gateway as UID $(id -u)"
if [ "$#" -eq 0 ]; then set -- gateway run; fi
exec /opt/hermes/.venv/bin/hermes "$@"
