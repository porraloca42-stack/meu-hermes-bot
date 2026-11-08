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
