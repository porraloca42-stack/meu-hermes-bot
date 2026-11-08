# Hermes Agent — deployment and validation plan

The existing Streamlit/Groq prototype on `main` is intentionally untouched. All Hermes work is isolated on `hermes-agent-migration`.

## Current build status

- Official Hermes Docker image and gateway command documented by Nous Research.
- A project operating charter (`AGENTS.md`), global persona template (`SOUL.md`), conservative config example, and five initial TikTok skills are included in this branch.
- `install-hermes-profile.sh` copies the persona/config/skills into a Hermes home directory without overwriting existing files.
- No API keys, Telegram tokens, or user secrets are stored in this repository.
- This branch is not deployed or production-tested yet.

## Hosting decision: no card, always-on, persistent memory

Hostless currently advertises a no-card free allowance and always-on apps/workers. Its public pricing page describes a shared allowance of 0.5 vCPU, 1 GiB RAM and 512 MiB storage. However, its filesystem documentation says that `/root`, `/tmp` and cache files are deleted on restart; only an attached volume persists. Hostless documents durable volumes as separately billed and requiring payment eligibility. Therefore, do **not** assume that a no-card Hostless deployment will preserve Hermes sessions, memories, and skills across restarts.

Hostless also offers a one-click Hermes service, but its provider-key guide documents OpenRouter, OpenAI, or Anthropic keys. OpenAI and Anthropic API use is paid; OpenRouter has some free models but their availability and limits are not guaranteed. Before creating a resource, inspect its storage, runtime, and billing screens. Do not add a card, create a paid volume, enable paid capacity, or accept a paid model.

Official references:
- Hermes Docker: https://hermes-agent.nousresearch.com/docs/user-guide/docker
- Hostless free tier/pricing: https://hostless.cloud/pricing
- Hostless filesystem: https://docs.hostless.cloud/app/filesystem
- Hostless storage settings: https://docs.hostless.cloud/app/configurations
- Hostless Hermes provider keys: https://docs.hostless.cloud/services/provider-keys

## Telegram safety

1. Create a **new, dedicated Telegram bot** for Hermes using @BotFather.
2. Do not reuse the token of the existing Telegram automation. Telegram polling/webhook ownership can conflict.
3. Keep the token in the host's secret/environment-variable manager as `TELEGRAM_BOT_TOKEN`.
4. Restrict access with `TELEGRAM_ALLOWED_USERS` set to the owner's numeric Telegram user ID. Never enable `TELEGRAM_ALLOW_ALL_USERS` for production.
5. Never paste tokens into chat or commit them to Git.

## Model selection

Hermes requires a model with at least 64K context for its agentic workflow. Free inference is not unlimited and model catalog/quotas change. Do not select a model merely because it has a free label: validate context length, tool calling, rate limits, reliability and provider terms first.

The existing Groq key may be evaluated as one candidate, but it is not automatically the best free agent model. The current Hermes provider documentation describes Groq configuration and also warns that free/provider limits may constrain long agentic conversations. Prefer a verified no-cost model/provider before setting a default.

## Local Docker path (only where durable storage exists)

The official Docker image stores Hermes home data at `/opt/data` when mounted as documented:

```bash
mkdir -p hermes-data
docker compose run --rm hermes setup
```

Install this repository's persona/config/skills into the same Hermes home, then configure provider and Telegram secrets securely. Start the gateway:

```bash
docker compose up -d
docker compose logs -f hermes
```

The volume `./hermes-data:/opt/data` must be durable and backed up. Do not use an ephemeral filesystem for the live Hermes profile.

## Quality and safety configuration

- Memory writes are enabled to support ongoing learning.
- Skill writes require approval initially, so a weak model cannot silently turn a bad guess into a permanent procedure. Review staged changes using `/skills pending`, then approve/reject.
- Non-interactive tool-loop hard stops remain enabled.
- Memory update notifications are verbose so the user can see what was learned.
- Keep the Hermes API/dashboard private unless proper authentication, TLS and access controls are configured.

## Acceptance tests before calling it ready

1. Container starts and `hermes doctor` reports no critical errors.
2. Telegram bot responds only to the authorized user.
3. Restart the service and confirm sessions, memory, skills, and configuration remain.
4. Change the model and confirm Hermes profile data remains.
5. Verify web research, file reading, terminal/sandbox tools, image/voice tools if available, subagents and scheduled tasks individually.
6. Run a TikTok research task with source citations and a script task; inspect factual accuracy and tool-use behavior.
7. Back up and restore the Hermes home successfully.

A successful deploy is not production-ready until these tests pass.


## Hostless no-volume status — 2026-11-08

The user selected **No volume** in Hostless and set the application data path to `/opt/data`. This avoids creating a paid volume, but it leaves the container filesystem ephemeral. It is not safe to launch the real Telegram agent until restore-before-start and encrypted off-host backups have been implemented and tested.

### DBByte connection contract

The user reports creating a DBByte bucket intended to be named `hermes-backups`. Confirm in the dashboard that it is private. Official DBByte S3 documentation specifies:

- Endpoint: `https://s3.dbbyte.com`
- Region: `auto`
- Path-style addressing: enabled
- Environment variables: `DBBYTE_ACCESS_KEY_ID`, `DBBYTE_SECRET_ACCESS_KEY`, `HERMES_BACKUP_BUCKET`

The dashboard's API Keys flow provides the S3 access-key ID and secret access key as a pair. Both values were exposed in chat and must be rotated before use. Never put either value in this repository, logs, Telegram, or a command pasted into chat. Enter replacements directly in Hostless Secrets only.

### Required implementation before deployment

1. Add a pre-start restore hook that downloads the latest authenticated-encrypted backup into an empty `/opt/data` before the official image's `/init` / s6 supervision tree starts.
2. Preserve the official image's s6 supervision. The upstream Docker guide states that `gateway run` is managed by s6; replacing the image entrypoint or bypassing `/init` would discard that supervision.
3. Add a separately supervised periodic backup service (not an unsupervised background shell job). Use the official `hermes backup -o <path>` command, require exit code 0, encrypt with authenticated encryption, upload to the private DBByte bucket, verify the uploaded object, and only then apply retention.
4. Keep the encryption/decryption key in Hostless Secrets only. Hermes backup ZIPs include sensitive config and credentials; never upload them unencrypted.
5. Verify S3 upload/download/delete against a disposable test object, then verify encrypted backup/restore using a disposable Hermes profile before deploying the user's real profile.
6. Confirm DBByte free-plan quotas and behavior at limits in the dashboard. Do not add a payment method or enable paid usage.
7. Configure a dedicated Telegram bot token and allowed-user restriction only after the storage tests pass.

### Current hard stop

The repository currently has the official-image Dockerfile with `CMD ["gateway", "run"]`, but **does not yet contain** the pre-start restore hook or a supervised backup service. The Hostless resource has not been created. Do not click Deploy/Publish for the real agent yet. Do not claim persistence is working until the above tests pass.


## DBByte persistence wrapper added — validation pending

The current branch now includes an initial DBByte backup/restore implementation in the custom Docker image:

- The image keeps the official Hermes ENTRYPOINT and CMD; no custom entrypoint bypasses s6.
- A boot hook named `01a-dbbyte-restore` runs after the upstream setup hook and before profile reconciliation.
- An s6 longrun service creates an encrypted full Hermes backup after a 10-minute startup delay and repeats every 24 hours.
- AES-256-GCM encryption uses a passphrase supplied only through Hostless Secrets. The passphrase must be at least 32 UTF-8 bytes.
- S3 objects are split into 90 MiB parts to stay below DBByte's documented 100 MB per-object limit. A manifest is written last; part sizes and SHA-256 digests are checked before publishing it.
- Seven complete snapshots are retained by default.

Configure these Hostless secrets before deployment:

```text
DBBYTE_ACCESS_KEY_ID
DBBYTE_SECRET_ACCESS_KEY
HERMES_BACKUP_ENCRYPTION_PASSPHRASE
HERMES_BACKUP_BUCKET=hermes-backups
DBBYTE_ENDPOINT=https://s3.dbbyte.com
DBBYTE_REGION=auto
```

Do not paste any secret into chat or GitHub. Generate a unique random passphrase of at least 32 bytes and keep a recovery copy in a password manager. Rotate the DBByte credential pair previously exposed in chat; do not reuse it. Confirm the bucket is Private.

**Not yet approved for deployment:** the Docker image has not been built, the DBByte S3 round-trip has not been tested, and an actual Hermes backup/import cycle has not been tested. GitHub Actions passed Python compilation plus AES-GCM round-trip and tamper-detection tests (run 42529111417); these are unit-level checks only. The first successful remote backup occurs about 10 minutes after startup; later backups run every 24 hours, so recovery can lose up to about one day of recent changes. Do not deploy the real bot until the container build, upload, download, restore, and restart acceptance tests pass.
