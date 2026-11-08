# Persistence architecture for Hostless (no paid volume)

## Decision

Do not treat an external Hermes memory provider as a replacement for durable storage.

Hermes has separate persistence layers:

1. Built-in notes/profile memory under `/opt/data`.
2. Canonical conversation/session history in SQLite (`state.db`).
3. Mutable configuration, credentials, skills, plugins, cron jobs, logs, and user artifacts under `/opt/data`.

The official Docker guide identifies `/opt/data` as the single source of truth. The official session-storage guide identifies SQLite as the canonical store for session metadata and full message history. An external memory provider is additive: it syncs knowledge across sessions but does not replace the local session database.

## Hermes backup capability (verified)

The official `hermes backup -o <path>` command creates a ZIP of configuration, skills, sessions, and data. It uses SQLite's backup API, so it can safely snapshot a live WAL-mode database. `hermes import <zipfile>` restores the archive; the gateway should be stopped before import. Full backups include sensitive credentials such as `.env` and `auth.json`, so an off-host archive must be encrypted before upload and the encryption key must exist only in Hostless secrets. The CLI reports incomplete backups with a non-zero exit status; the wrapper must reject any archive unless the command exits successfully.

This is the preferred mechanism for producing consistent backup archives. It does not itself upload archives off-host or make the live filesystem persistent.

## Candidate no-volume architecture

Use an S3-compatible object store as a **backup/restore target**, not as a mounted filesystem:

- At container startup, if the local Hermes home is empty, download the newest verified backup archive.
- Restore it before starting the single Hermes gateway process.
- While running, periodically create a consistent Hermes backup using `hermes backup`.
- Upload the archive to object storage using a unique timestamp/version key.
- Keep a small rolling set of known-good backups; verify upload success and archive checksum before pruning old backups.
- On shutdown, attempt one final backup, but do not rely on shutdown hooks as the only protection because hosts may terminate containers abruptly.

This design protects the full Hermes home at backup intervals, but it is **not equivalent to a persistent mounted volume**. A crash can lose changes since the last successful backup. It also cannot safely run two gateways against the same data directory simultaneously.

## Object-store candidate: Cloudflare R2

R2 advertises a free monthly allowance for Standard storage (10 GB-month, 1 million Class A operations, 10 million Class B operations, free egress). However, Cloudflare's current getting-started instructions require completing an R2 subscription checkout. Do not assume checkout is possible without a verified payment method or that the account will remain at R$0.00. The user must inspect the checkout/payment requirement before enabling it. Do not add a card or accept charges without explicit approval.

R2 is object storage. It is not a POSIX volume and must not be mounted as `/opt/data` or used as a live SQLite database.


## Additional object-store candidate: Tigris (promising, not yet activated)

Tigris currently advertises an ongoing monthly free allowance on its pricing page:
- 5 GB Standard storage.
- 10,000 Class A requests (PUT/COPY/POST/LIST).
- 100,000 Class B requests (GET and other requests).
- No egress fees.
- No payment card required to start.

The S3-compatible endpoint is `https://t3.storage.dev`; the documented region value is `auto`. Credentials are an access-key ID and secret, and the secret is displayed only once when created.

This is a stronger candidate than R2 for the user's no-card requirement. However:
- The free allowance is a quota, not proof of a hard spending cap.
- Public pricing describes metered prices above the allowance. We have not verified whether an account without a payment method is automatically blocked at quota or simply unable to continue.
- Do not add a payment method, enable paid usage, or create any paid resource.
- Before using it for Hermes, create a test bucket and verify account billing behavior, access-key scope, upload/download, and deletion while remaining inside free limits.
- Never store Hermes backups in this public GitHub repository. The repository is currently public; backups may contain Telegram/API credentials and private conversation history. Only source code and sanitized examples belong here.

The current Tigris pricing page and S3 integration guidance:
- https://www.tigrisdata.com/pricing/
- https://www.tigrisdata.com/features/
- https://www.npmjs.com/package/@tigrisdata/cli

Tigris is still only a candidate. No account, bucket, access key, or backup integration has been created.

## Hermes external memory providers

Current Hermes docs list built-in external memory providers including RetainDB and ByteRover, plus catalog providers such as Honcho, OpenViking, Mem0, Hindsight, Holographic, and Supermemory. The built-in MEMORY.md/USER.md remains active alongside one selected external provider.

Important distinction:
- **ByteRover local mode** stores its knowledge tree under Hermes home. It is useful for retrieval/curation but does not survive loss of Hostless ephemeral storage by itself.
- **RetainDB** has conflicting current public descriptions: its website advertises a no-card free tier, while Hermes provider documentation and its plugin README describe a paid $20/month requirement. Do not choose it until its current API eligibility and Hermes plugin compatibility are verified.
- Other cloud providers must be evaluated individually for free quota, payment requirements, data retention, privacy, and API-key access.

An external memory provider is not a backup of `state.db`, config, skills, or the full Hermes home.

## Implementation gates

Before implementing a backup wrapper or selecting a provider:

1. Confirm an object-store account can be created and used with no payment method and no charge.
2. Confirm the provider offers S3-compatible credentials and bucket access.
3. Keep credentials only in Hostless secrets/environment variables; never commit them.
4. Build startup restore + periodic backup wrapper and ensure it preserves the official image's runtime assumptions.
5. Test backup/restore with a disposable profile and verify `state.db`, memories, config, skills, and cron data.
6. Test a simulated restart and a simulated abrupt termination; document the recovery-point window.
7. Only then deploy the real Telegram bot.

## Current status

- The repository contains the official Hermes Docker image deployment path and a dedicated migration branch.
- Hostless free compute has been configured by the user, but no resource has been created yet.
- No persistent volume is attached.
- No external object-store account or credentials are configured.
- No backup automation is implemented or tested.
- The GitHub repository is public; it currently contains source/configuration examples only. It must never receive real backups or secrets.
- Do not describe the system as durable or production-ready until all acceptance tests pass.

## Official references

- Hermes Docker and `/opt/data`: https://hermes-agent.nousresearch.com/docs/user-guide/docker
- Hermes memory providers: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers
- Hermes backup and restore: https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/cli-commands.md
- Cloudflare R2 free tier: https://developers.cloudflare.com/r2/pricing/
- Cloudflare R2 getting started / subscription checkout: https://developers.cloudflare.com/r2/get-started/
