# Persistence architecture for Hostless (no paid volume)

## Decision

Do not treat an external Hermes memory provider as a replacement for durable storage.

Hermes has separate persistence layers:

1. Built-in durable notes and profile memory under `/opt/data` (including memory files).
2. Canonical conversation/session history in the SQLite database `state.db`.
3. Mutable configuration, credentials, skills, plugins, cron jobs, and user artifacts under `/opt/data`.

The official Docker guide identifies `/opt/data` as the single source of truth. The official session-storage guide identifies SQLite as the canonical store for session metadata and full message history. An external memory provider is additive: it syncs knowledge across sessions but does not replace the local session database.

## Candidate no-volume architecture

Use an S3-compatible object store as a **backup/restore target**, not as a mounted filesystem:

- At container startup, if the local Hermes home is empty, download the newest verified backup archive.
- Restore it before starting the single Hermes gateway process.
- While running, periodically create a consistent Hermes backup using the official `hermes backup` command. This command uses SQLite's backup API and is safe while the gateway is running.
- Upload the archive to object storage using a unique timestamp/version key.
- Keep a small rolling set of known-good backups; verify upload success and archive checksum before pruning old backups.
- On shutdown, attempt one final backup, but do not rely on shutdown hooks as the only protection because hosts may terminate containers abruptly.

This design protects the full Hermes home at backup intervals, but it is **not equivalent to a persistent mounted volume**. A crash can lose changes since the last successful backup. It also cannot safely run two gateways against the same restored state at once.

## Candidate provider: Cloudflare R2

R2 advertises a free monthly allowance for Standard storage (10 GB-month, 1 million Class A operations, 10 million Class B operations, free egress). However, Cloudflare's current getting-started instructions require completing an R2 subscription checkout. Do not assume checkout is possible without a verified payment method or that the account will remain at R$0.00. The user must inspect the checkout/payment requirement before enabling it. Do not add a card or accept charges without explicit approval.

R2 is object storage. It is not a POSIX volume and must not be mounted as `/opt/data` or used as a live SQLite database.

## Hermes external memory provider

Hermes supports optional external memory-provider plugins. They can inject/retrieve semantic knowledge and sync conversation turns, but the built-in memory and local session database remain active. Provider availability, free quota, retention, privacy, and API-key requirements must be checked before choosing one. Do not store secrets or private conversation data with a provider without reviewing its terms and obtaining the user's approval.

## Implementation gates

Before implementing the backup wrapper or selecting a provider:

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
- Do not describe the system as durable or production-ready until all acceptance tests pass.

## Official references

- Hermes Docker and `/opt/data`: https://hermes-agent.nousresearch.com/docs/user-guide/docker
- Hermes session storage: https://hermes-agent.nousresearch.com/docs/developer-guide/session-storage
- Hermes memory providers: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers
- Hermes backup and restore: https://hermes-agent.nousresearch.com/docs/reference/cli-commands
- Cloudflare R2 free tier: https://developers.cloudflare.com/r2/pricing/
- Cloudflare R2 getting started / subscription checkout: https://developers.cloudflare.com/r2/get-started/
