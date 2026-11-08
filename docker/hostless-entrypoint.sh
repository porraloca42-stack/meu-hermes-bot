#!/bin/sh
# Hostless startup: bypass /init because this runtime exposes /run read-only,
# while s6-overlay requires a writable/executable /run tmpfs.
set -eu

export HERMES_HOME="${HERMES_HOME:-/app/.cache/hermes-home}"
export HOME="$HERMES_HOME"
export HERMES_WRITE_SAFE_ROOT="$HERMES_HOME"
export PATH="/command:/opt/hermes/bin:/opt/hermes/.venv/bin:$HERMES_HOME/.local/bin:$PATH"
umask 077

echo "[hostless-start] preparing writable Hermes home at $HERMES_HOME"
# Hostless runs this container as its restricted root user. Keep files owned
# by that runtime UID; do not chown or attempt s6-setuidgid (both need extra caps).
mkdir -p "$HERMES_HOME"

# Remote persistence is optional for boot, but required for durable memory.
# Missing variables must not prevent the Telegram gateway from starting.
PERSISTENCE_READY=1
for name in DBBYTE_ACCESS_KEY_ID DBBYTE_SECRET_ACCESS_KEY HERMES_BACKUP_ENCRYPTION_PASSPHRASE DBBYTE_ENDPOINT DBBYTE_REGION HERMES_BACKUP_BUCKET; do
  eval 'value=${'"$name"'-}'
  if [ -z "$value" ]; then
    echo "[hostless-start] WARNING: $name is missing; DBByte restore/backup will be skipped"
    PERSISTENCE_READY=0
  fi
done

# Prepare the standard writable layout.
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

# Seed upstream defaults only when absent; restored/user files always win.
if [ ! -f "$HERMES_HOME/config.yaml" ] && [ -f /opt/hermes/cli-config.yaml.example ]; then
  cp /opt/hermes/cli-config.yaml.example "$HERMES_HOME/config.yaml"
fi
if [ ! -f "$HERMES_HOME/.env" ]; then touch "$HERMES_HOME/.env"; fi
if [ ! -f "$HERMES_HOME/SOUL.md" ] && [ -f /opt/hermes/docker/SOUL.md ]; then
  cp /opt/hermes/docker/SOUL.md "$HERMES_HOME/SOUL.md"
fi
chmod 600 "$HERMES_HOME/.env"

# Ensure the local gateway control API key exists without replacing a supplied key.
if [ -z "${API_SERVER_KEY:-}" ] && ! grep -q '^API_SERVER_KEY=..*' "$HERMES_HOME/.env"; then
  key="$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  sh -c "printf 'API_SERVER_KEY=%s\\n' '$key' >> '$HERMES_HOME/.env'"
fi

# Run the existing root bootstrap hook; it drops individual writes to hermes.
PATH="/command:$PATH" sh /etc/cont-init.d/01b-install-profile
if [ -f /opt/hermes/tools/skills_sync.py ]; then
  /opt/hermes/.venv/bin/python /opt/hermes/tools/skills_sync.py || echo "[hostless-start] WARNING: bundled skill sync failed; continuing"
fi

# Keep encrypted backup running alongside the gateway when configured.
if [ "$PERSISTENCE_READY" -eq 1 ]; then
  /usr/bin/python3 /opt/hermes/scripts/dbbyte_backup.py loop &
  echo "[hostless-start] encrypted DBByte backup loop started"
fi
echo "[hostless-start] starting Hermes gateway"
if [ "$#" -eq 0 ]; then set -- gateway run; fi
exec /opt/hermes/bin/hermes "$@"
