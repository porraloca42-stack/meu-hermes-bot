# Hermes Agent — TikTok specialist

This repository keeps the original prototype on `main` untouched. The active Hermes build is on branch `hermes-agent-migration`.

## What is prepared

- Custom Docker image extends the official Hermes gateway, keeps s6 supervision, seeds the TikTok operating charter and skills, and includes encrypted DBByte backup/restore. Docker build, actual Hermes CLI backup/import, and profile-seed smoke tests passed (run 42531501471); live DBByte round-trip remains pending.
- Operating charter and agent identity: `AGENTS.md`, `SOUL.md`.
- Initial skills for research, strategy, script production, analytics learning, and source/claim audits.
- Conservative Hermes configuration example and a non-destructive profile installer.
- Deployment notes, hosting caveats, and production acceptance tests.

## Start here

1. Read [DEPLOYMENT.md](DEPLOYMENT.md) before creating infrastructure.
2. Review [AGENTS.md](AGENTS.md) and [SOUL.md](SOUL.md).
3. On a machine/container with a durable Hermes home, run `bash install-hermes-profile.sh`.
4. Add `GROQ_API_KEY` (for the $0 Groq Free Plan) and a new dedicated Telegram bot token plus allowed-user ID directly to the host's secret manager. Never commit secrets.
5. Validate persistence and all acceptance tests before treating the agent as ready.

## Important

Deploy as a standalone Hostless Worker (Telegram polling does not serve HTTP). The Hostless resource has not been created or deployed yet; the user is paused at the final review screen. No paid volume or payment method is required or authorized.

The selected Hostless filesystem is ephemeral, so the custom image restores the latest encrypted snapshot before starting Hermes and periodically backs up the complete Hermes home to DBByte. This is not equivalent to a mounted persistent volume; the current recovery window is up to 24 hours. The default inference route is Groq `openai/gpt-oss-120b` on its $0 Free Plan (8,000 tokens/minute and 200,000 tokens/day). It is rate-limited, not unlimited. Hermes' keyless web search/extract providers are separate and also rate-limited.

The full Docker build and smoke tests passed (run 42531501471), including the actual Hermes CLI backup/import round-trip, wrapper checks, and profile seeding in the Hostless writable cache path. All seven Python persistence tests passed (run 42532049364), including the fresh-profile Groq model configuration. Live DBByte upload/download/restore and restart tests remain mandatory. Rotate the exposed S3 credential pair, confirm the bucket is Private, and keep all replacement secrets outside GitHub and chat.
