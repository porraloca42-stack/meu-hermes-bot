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
as_hermes() { /command/s6-setuidgid hermes "$@"; }

# Do not chown: Hostless drops the capability required to change ownership.
# Create the home as the Hermes service user so it owns its files naturally.
as_hermes mkdir -p "$HERMES_HOME"

# Require remote persistence before starting on ephemeral storage.
if [ -z "${DBBYTE_ACCESS_KEY_ID:-}" ] || [ -z "${DBBYTE_SECRET_ACCESS_KEY:-}" ] || [ -z "${HERMES_BACKUP_ENCRYPTION_PASSPHRASE:-}" ]; then
  echo "[hostless-start] ERROR: DBByte credentials/passphrase are missing; refusing ephemeral startup" >&2
  exit 1
fi

# Prepare the standard writable layout, then restore before seeding defaults.
as_hermes mkdir -p \
  "$HERMES_HOME/backups" "$HERMES_HOME/cron" "$HERMES_HOME/sessions" \
  "$HERMES_HOME/logs/gateways" "$HERMES_HOME/hooks" "$HERMES_HOME/memories" \
  "$HERMES_HOME/skills" "$HERMES_HOME/skins" "$HERMES_HOME/plans" \
  "$HERMES_HOME/workspace" "$HERMES_HOME/home" "$HERMES_HOME/pairing" \
  "$HERMES_HOME/platforms/pairing"
as_hermes /usr/bin/python3 /opt/hermes/scripts/dbbyte_backup.py restore

# Seed upstream defaults only when absent; restored/user files always win.
if [ ! -f "$HERMES_HOME/config.yaml" ] && [ -f /opt/hermes/cli-config.yaml.example ]; then
  as_hermes cp /opt/hermes/cli-config.yaml.example "$HERMES_HOME/config.yaml"
fi
if [ ! -f "$HERMES_HOME/.env" ]; then as_hermes touch "$HERMES_HOME/.env"; fi
if [ ! -f "$HERMES_HOME/SOUL.md" ] && [ -f /opt/hermes/docker/SOUL.md ]; then
  as_hermes cp /opt/hermes/docker/SOUL.md "$HERMES_HOME/SOUL.md"
fi
as_hermes chmod 600 "$HERMES_HOME/.env"

# Ensure the local gateway control API key exists without replacing a supplied key.
if [ -z "${API_SERVER_KEY:-}" ] && ! grep -q '^API_SERVER_KEY=..*' "$HERMES_HOME/.env"; then
  key="$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  as_hermes sh -c "printf 'API_SERVER_KEY=%s\\n' '$key' >> '$HERMES_HOME/.env'"
fi

# Run the existing root bootstrap hook; it drops individual writes to hermes.
PATH="/command:$PATH" sh /etc/cont-init.d/01b-install-profile
if [ -f /opt/hermes/tools/skills_sync.py ]; then
  as_hermes /opt/hermes/.venv/bin/python /opt/hermes/tools/skills_sync.py || echo "[hostless-start] WARNING: bundled skill sync failed; continuing"
fi

# Keep encrypted backup running alongside the gateway.
as_hermes /usr/bin/python3 /opt/hermes/scripts/dbbyte_backup.py loop &
echo "[hostless-start] encrypted DBByte backup loop started"
echo "[hostless-start] starting Hermes gateway"
if [ "$#" -eq 0 ]; then set -- gateway run; fi
exec /opt/hermes/bin/hermes "$@"
