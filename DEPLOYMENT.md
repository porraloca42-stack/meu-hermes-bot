# Hermes Agent — deployment and validation plan

All Hermes work is isolated on `hermes-agent-migration`. The `main` branch remains untouched.

## Hostless resource

Deploy as a **standalone Worker**, not an App. Telegram uses long polling and does not serve HTTP traffic; Hostless Workers are intended for long-running background processes.

The user has selected:
- Runtime: `Other` / Docker
- Repository-root Dockerfile: `Dockerfile`
- Working directory: `/`
- Start command: blank (preserves the image's `gateway run` CMD)
- Replicas: 1
- CPU: 0.5 vCPU
- Memory: 1,024 MB
- Storage: No volume
- Review estimate: R$0.00

This uses the documented free allowance if no other resources consume the account-wide pool. Do not add a payment method, increase capacity, create a paid volume, or accept charges. The Worker has not been created or deployed; the user is paused at the final review screen.

## Hostless filesystem compatibility

Hostless runs workloads with a read-only root filesystem. Without an attached volume, the official Hermes default `/opt/data` is not a safe writable path. The custom image therefore overrides:

- `HERMES_HOME=/app/.cache/hermes-home`
- `HOME=/app/.cache/hermes-home`
- `HERMES_WRITE_SAFE_ROOT=/app/.cache/hermes-home`
- Working directory: `/app/.cache/hermes-home`

Hostless documents `/app/.cache` as writable scratch storage (2 GiB) and deletes it on restart. This is intentionally ephemeral. The custom image restores the newest encrypted DBByte snapshot before starting Hermes and backs up the full Hermes home every 24 hours. Monitor home size; do not assume this scratch directory is durable.

The image preserves the official Hermes ENTRYPOINT, s6 supervision, and `gateway run` command. Startup order:
1. Upstream `01-hermes-setup` prepares the configured Hermes home and seeds the custom SOUL.
2. `01a-dbbyte-restore` restores the latest complete snapshot into an empty home.
3. `01b-install-profile` adds `AGENTS.md` and TikTok skills only when missing, then merges safe defaults without overwriting user settings.
4. Upstream supervision-permissions and profile-reconciliation hooks run.
5. The gateway and encrypted backup longrun service start.

## Hermes project profile

- `SOUL.md`: Brazilian Portuguese, evidence-led strategic partner, direct and practical.
- `AGENTS.md`: research rigor, source verification, project separation, quality control, and learning loop.
- `.hermes/skills/`: TikTok research, strategy, script doctor, analytics learning, and source audit.
- Memory capture is enabled without approval; skill changes require approval initially.
- The Hostless image seeds these files on first boot and preserves user edits after restore.

The user's current TikTok Shop project (books around law of attraction and quantum physics, including Oráculo 369) is separate from the older `O Sobrevivente Consciente` self-development project. Do not merge the two.

## Free inference bootstrap

The profile merger keeps Hermes' built-in Nous guest route enabled (`nous.guest: true`). With no other provider credentials, a fresh installation can create a no-sign-in free-tier identity and use the single `nous/welcome` model. It has standard rate limits and is not unlimited frontier inference. Paid Tool Gateway features such as hosted web search, image generation, TTS, and cloud browser are not included in this free tier.

The Groq key is intentionally not selected as the default provider. Groq's free-tier 8,000-token-per-minute limit is below the normal Hermes request size with its default toolset; using it as the main provider would cause failed agent turns unless the account is upgraded. Do not upgrade or enable billing. If the Nous free endpoint is unavailable or rate-limited, Hermes must report that accurately rather than silently switching to a paid provider.

## DBByte backup and restore

DBByte is used as encrypted backup storage, not as a mounted filesystem or live SQLite database.

- `scripts/dbbyte_backup.py` runs the official `hermes backup -o <path>` command and rejects failed or invalid ZIP archives.
- AES-256-GCM encryption; PBKDF2-HMAC-SHA256 with 600,000 iterations derives the key from a passphrase.
- Encrypted archive split into 90 MiB S3 objects, below DBByte's documented 100 MB object limit.
- Each part is recorded with size and SHA-256; restore downloads and checks the actual part hashes, full archive hash, GCM authentication, and ZIP CRC before import.
- Manifest is published last; seven complete snapshots are retained.
- First backup is scheduled 60 seconds after startup; subsequent backups every 24 hours. Recovery can lose up to one day of recent changes.

Required Hostless Secrets (enter values directly in Hostless; never send them in chat or GitHub):
- `DBBYTE_ACCESS_KEY_ID`
- `DBBYTE_SECRET_ACCESS_KEY`
- `HERMES_BACKUP_ENCRYPTION_PASSPHRASE` — unique random value, at least 32 UTF-8 bytes; keep a recovery copy in a password manager.
- `HERMES_BACKUP_BUCKET=hermes-backups`
- `DBBYTE_ENDPOINT=https://s3.dbbyte.com`
- `DBBYTE_REGION=auto`

The DBByte bucket already exists according to the user. Confirm it is **Private** before uploading. The S3 credential pair previously pasted into chat must be rotated; never reuse those values.

## Telegram safety

Before deployment:
1. Create a new dedicated bot with @BotFather. Do not reuse the bot already connected to Make.
2. Add `TELEGRAM_BOT_TOKEN` directly to Hostless Secrets.
3. Add `TELEGRAM_ALLOWED_USERS` with the owner's numeric Telegram user ID. Do not enable allow-all access.
4. Never paste tokens into chat or commit them to Git.

## Validation status

### Passed
- Six Python tests: AES-GCM round-trip, tamper rejection, mocked S3 backup/restore, empty-profile behavior, protection of existing state, and config-merge preservation (GitHub Actions run 42530752212).
- The actual Hermes CLI backup/import round-trip succeeded in Docker CI run 42531234012: it created a ZIP and restored all four fixture files. The overall job then failed only at the profile-seed hook invocation in the test harness.

### In progress / failed earlier attempts corrected
- The complete Docker smoke test is being re-run after correcting the harness to invoke the s6 profile-seed hook with the expected command path. The real Hermes backup/import portion has already passed.
- Earlier smoke-test attempts exposed fixture and test-harness issues; do not count those failed attempts as product failures or as passed full-image tests.

### Still required before production
1. Latest full Docker build and profile-seed smoke test must pass. The actual Hermes backup/import CLI round-trip is already verified.
2. Live DBByte upload/download/restore using newly rotated credentials.
3. Restart test proving sessions, memories, skills, and configuration are recovered from DBByte.
4. Dedicated Telegram bot responds only to the allowed user.
5. TikTok research and content task acceptance tests.

A mocked S3 test is not a live DBByte test. A Docker build is not proof of live persistence. Do not deploy the real Telegram bot until all remaining acceptance tests pass.

## Local Docker development

For local Docker Compose only, the default Hermes path `/opt/data` remains mounted to `./hermes-data` as a local persistent directory. The Hostless override to `/app/.cache/hermes-home` is for the no-volume Hostless Worker only.

## Official references

- Hermes Docker and `/opt/data`: https://hermes-agent.nousresearch.com/docs/user-guide/docker
- Hermes backup/import CLI: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/cli-commands.md
- Hermes free tier: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/free-tier.md
- Hostless workers: https://docs.hostless.cloud/app/workers
- Hostless filesystem: https://docs.hostless.cloud/app/filesystem
- Hostless free entitlement: https://docs.hostless.cloud/plans/limits
- DBByte S3 docs: https://dbbyte.com/docs
