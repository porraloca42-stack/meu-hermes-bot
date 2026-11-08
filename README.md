# Hermes Agent — TikTok specialist

This repository keeps the original prototype on `main` untouched. The active Hermes build is on branch `hermes-agent-migration`.

## What is prepared

- Custom Docker image extends the official Hermes gateway, keeps s6 supervision, seeds the TikTok operating charter and skills, and includes encrypted DBByte backup/restore. Latest image build and actual Hermes backup/import smoke test are still running; live DBByte round-trip remains pending.
- Operating charter and agent identity: `AGENTS.md`, `SOUL.md`.
- Initial skills for research, strategy, script production, analytics learning, and source/claim audits.
- Conservative Hermes configuration example and a non-destructive profile installer.
- Deployment notes, hosting caveats, and production acceptance tests.

## Start here

1. Read [DEPLOYMENT.md](DEPLOYMENT.md) before creating infrastructure.
2. Review [AGENTS.md](AGENTS.md) and [SOUL.md](SOUL.md).
3. On a machine/container with a durable Hermes home, run `bash install-hermes-profile.sh`.
4. For the no-card bootstrap, Hermes uses its built-in Nous guest model; no model API key is needed initially. Add a new dedicated Telegram bot token and allowed-user ID directly to the host's secret manager. Never commit secrets.
5. Validate persistence and all acceptance tests before treating the agent as ready.

## Important

Deploy as a standalone Hostless Worker (Telegram polling does not serve HTTP). The Hostless resource has not been created or deployed yet; the user is paused at the final review screen. No paid volume or payment method is required or authorized.

The selected Hostless filesystem is ephemeral, so the custom image restores the latest encrypted snapshot before starting Hermes and periodically backs up the complete Hermes home to DBByte. This is not equivalent to a mounted persistent volume; the current recovery window is up to 24 hours. The built-in Nous guest inference route is enabled as a no-card bootstrap, but it is a limited free model with standard rate limits, not unlimited frontier inference.

The Python test workflow passed all six tests: AES-GCM round-trip, tamper rejection, mocked S3 backup/restore, empty-profile behavior, protection of existing state, and config-merge preservation (run 42530752212). The actual Hermes CLI backup/import round-trip passed (run 42531234012). The full Docker smoke test then failed only when the test harness invoked the s6 profile-seed hook outside its normal init context; the harness has been corrected and the complete check is being rerun. Live DBByte upload/download/restore and restart tests are still mandatory. Rotate the exposed S3 credential pair, confirm the bucket is Private, and keep all replacement secrets outside GitHub and chat.
