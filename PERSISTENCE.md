# Hermes persistence and deployment status

## Deployment target

Use a **standalone Hostless Worker**, not an App. Telegram polling is a long-running background process and does not receive HTTP traffic. Hostless Apps must listen on `PORT` and pass a health check; Workers are designed for processes that run continuously without HTTP requests.

The user selected the Docker runtime (Hostless UI label: `Other`), repository-root `Dockerfile`, working directory `/`, one instance, 0.5 vCPU, 1,024 MB RAM, no custom start command, and no volume. The review showed R$0.00. This uses the documented free pool if no other account resources consume it; do not add capacity or a payment method. The image's official Hermes gateway command remains the default. The Hostless Worker has **not** been created or deployed; the user is paused at the final review screen. Do not deploy until the remaining validation and secret-entry steps are complete.

## Why backup/restore is required

The official Hermes Docker image defaults to `/opt/data`, but Hostless makes the root filesystem read-only. For the no-volume Hostless Worker, the custom image overrides `HERMES_HOME`, `HOME`, and `HERMES_WRITE_SAFE_ROOT` to `/app/.cache/hermes-home`. Hostless documents `/app/.cache` as a writable 2 GiB scratch area that is cleared on restart. Hermes' SQLite session history, built-in memory, configuration, credentials, skills, cron jobs, logs, and artifacts therefore live there only until a restart; DBByte is the encrypted backup/restore target, not a live-mounted filesystem or SQLite database. The upstream main wrapper, exec shim, optional dashboard runner, and login PATH helper are patched to respect the configured home instead of assuming `/opt/data`.

This is not equivalent to a persistent volume. With the current 24-hour backup interval, a crash can lose changes since the last successful backup.

## Startup sequence implemented

The custom image extends the official Hermes Docker image and preserves its ENTRYPOINT, s6 supervision, and `gateway run` CMD.

1. Upstream `01-hermes-setup` performs the official data-home setup, ownership, and first-boot seed.
2. `01a-dbbyte-restore` runs before profile reconciliation. It requires DBByte credentials and the encryption passphrase, then restores the newest complete snapshot into an empty Hermes home. It skips restore when a non-empty `/app/.cache/hermes-home/state.db` already exists.
3. `01b-install-profile` installs the project charter and TikTok skills only when missing, then merges safe configuration defaults without overwriting existing user choices.
4. Upstream `015-supervise-perms` and `02-reconcile-profiles` run in their normal order.
5. The official s6 supervision tree starts the gateway and the custom backup longrun service.

The Docker `WORKDIR` is `/app/.cache` so the Hostless mount exists before process start. The patched upstream main wrapper then enters `$HERMES_HOME` ( `/app/.cache/hermes-home` by default), ensuring the project's `AGENTS.md` is available as workspace context. The exec shim, optional dashboard service, and login PATH helper also honor `HERMES_HOME` instead of hard-coding `/opt/data`. The custom `SOUL.md` is used by the upstream first-boot seed.

## Backup implementation

- `scripts/dbbyte_backup.py` calls the official `hermes backup -o <path>` CLI and rejects non-zero exits or invalid ZIP archives.
- The ZIP is encrypted with AES-256-GCM. The key is derived from `HERMES_BACKUP_ENCRYPTION_PASSPHRASE` using PBKDF2-HMAC-SHA256 with 600,000 iterations.
- Encrypted archives are split into 90 MiB S3 objects, below DBByte's documented 100 MB per-object limit.
- Each uploaded part is checked by size and recorded SHA-256 metadata. A manifest is written last; restore downloads each part and verifies its actual SHA-256, total size, full encrypted-archive SHA-256, GCM authentication, and ZIP CRC before invoking the official Hermes import command.
- Seven complete snapshots are retained by default. Old snapshots are pruned only after the new manifest and all parts have been uploaded and checked.
- The s6 backup service waits 60 seconds after startup, then backs up every 24 hours.

The backup includes sensitive Hermes credentials and private conversation history. Encryption is mandatory. Never upload plaintext backups or commit backups/secrets to GitHub.

## Hostless environment variables

Enter values directly into Hostless Secrets. Never paste secrets into ChatGPT, Telegram, GitHub, or logs.

Required:
- `DBBYTE_ACCESS_KEY_ID`
- `DBBYTE_SECRET_ACCESS_KEY`
- `HERMES_BACKUP_ENCRYPTION_PASSPHRASE` — unique random passphrase, at least 32 UTF-8 bytes; keep a recovery copy in a password manager.
- `HERMES_BACKUP_BUCKET=hermes-backups`
- `DBBYTE_ENDPOINT=https://s3.dbbyte.com`
- `DBBYTE_REGION=auto`
- `TELEGRAM_BOT_TOKEN` — token for a new, dedicated Hermes bot, not the bot already used by Make.
- `TELEGRAM_ALLOWED_USERS` — the owner's numeric Telegram user ID. Do not enable allow-all access.

The DBByte S3 access-key pair previously pasted into chat must be rotated; do not reuse those values. Confirm the bucket is **Private** before uploading anything. The bucket already exists according to the user's report.

Do not add a payment method, create a paid Hostless volume, or enable paid inference. No Groq model key is configured as the default: the published Groq free-tier token-per-minute limit is below the default Hermes agent request size with its full toolset.

## Free inference bootstrap

The profile merger keeps Hermes' built-in Nous guest route enabled (`nous.guest: true`). With no other provider credentials, a fresh Hermes installation can bootstrap the no-sign-in free tier and use the single `nous/welcome` model. This is a limited bootstrap, not unlimited frontier inference: it has standard rate limits. Hermes' current web tooling can use managed `web_search` for a Nous guest identity and a keyless free-provider rotation for `web_search`/`web_extract`; these are rate-limited. Paid image generation, TTS, and hosted cloud-browser services are not included. If a free endpoint is closed or rate-limited, Hermes must report that honestly rather than silently using a paid provider.

## Validation status

### Passed
- AES-256-GCM encryption/decryption round-trip.
- Tampered ciphertext is rejected.
- Encrypted backup/upload/download/restore logic passed against a simulated S3 service using mocked Hermes CLI calls.
- Configuration merge test passed and confirmed existing user settings are preserved.
- Full custom Docker build and smoke tests passed (run 42531501471), including an actual Hermes CLI backup/import round-trip, wrapper syntax checks, and profile-seed/config merge into `/app/.cache/hermes-home`.
- Six Python tests passed (run 42531504083), covering AES-GCM round-trip, tamper rejection, mocked S3 backup/restore, empty-profile behavior, protection of existing state, and config-merge preservation.

### Still required
1. Live DBByte upload/download/restore with newly rotated credentials and the private bucket.
2. Restart test confirming sessions, memory, skills, and configuration are recovered.
3. Telegram bot response restricted to the allowed user.
4. TikTok research and content task acceptance tests.

A simulated S3 test is not a live DBByte test. A successful Docker build is not proof of live persistence. Do not call the agent production-ready until all remaining acceptance tests pass.

## Official references

- Hermes Docker and `/opt/data`: https://hermes-agent.nousresearch.com/docs/user-guide/docker
- Hermes backup/import CLI: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/cli-commands.md
- Hermes free tier: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/free-tier.md
- Hostless workers: https://docs.hostless.cloud/app/workers
- Hostless app vs worker lifecycle: https://docs.hostless.cloud/app/overview
- Hostless filesystem: https://docs.hostless.cloud/app/filesystem
- DBByte: https://dbbyte.com/docs
