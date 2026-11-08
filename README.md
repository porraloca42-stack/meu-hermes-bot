# Hermes Agent — TikTok specialist

This repository keeps the original prototype on `main` untouched. The active Hermes build is on branch `hermes-agent-migration`.

## What is prepared

- Official Hermes Docker gateway scaffold, extended with an initial DBByte encrypted backup/restore implementation (validation pending).
- Operating charter and agent identity: `AGENTS.md`, `SOUL.md`.
- Initial skills for research, strategy, script production, analytics learning, and source/claim audits.
- Conservative Hermes configuration example and a non-destructive profile installer.
- Deployment notes, hosting caveats, and production acceptance tests.

## Start here

1. Read [DEPLOYMENT.md](DEPLOYMENT.md) before creating infrastructure.
2. Review [AGENTS.md](AGENTS.md) and [SOUL.md](SOUL.md).
3. On a machine/container with a durable Hermes home, run `bash install-hermes-profile.sh`.
4. Configure a verified model provider and a dedicated Telegram bot using the host's secret manager. Never commit secrets.
5. Validate persistence and all acceptance tests before treating the agent as ready.

## Important

The no-card hosting requirement is still an open engineering constraint: a free always-on process is not sufficient if its filesystem is ephemeral. The selected host must preserve the Hermes home across restarts, including sessions, memories, and skills. See [DEPLOYMENT.md](DEPLOYMENT.md).

This branch is a prepared build, not a deployed or production-tested service. The DBByte backup wrapper still requires a successful image build, rotated S3 credentials, a private bucket, a Hostless encryption secret, and live backup/restore/restart acceptance tests before deployment.
