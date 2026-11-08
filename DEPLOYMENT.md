# Hermes Agent — deployment scaffold

This branch prepares a deployment using the **official Hermes Agent Docker image**.
The existing Streamlit/Groq prototype on `main` is intentionally left untouched.

## What this does

- Runs the official `nousresearch/hermes-agent:stable` image.
- Keeps configuration, sessions, memories, skills and workspace data in `./hermes-data`.
- Restarts the gateway automatically if the container exits.
- Does not publish a dashboard/API port to the public internet.

## Before starting the gateway

1. Provision a Linux VPS with Docker Engine and Docker Compose.
2. Create a dedicated Telegram bot for Hermes. **Do not reuse the token of the existing Telegram automation**: Telegram polling/webhook ownership can conflict.
3. SSH into the VPS and clone this repository on the `hermes-agent-migration` branch.
4. Run the official setup wizard interactively:

   ```bash
   mkdir -p hermes-data
   docker compose run --rm hermes setup
   ```

5. Complete provider and Telegram setup in the wizard/configuration flow.
6. Start the gateway:

   ```bash
   docker compose up -d
   docker compose logs -f hermes
   ```

## Important safety notes

- Never commit API keys, Telegram tokens, `.env` files, or the `hermes-data/` directory.
- Restrict SSH access, enable the VPS firewall, and keep the OS and Docker updated.
- Configure backups for `hermes-data/` before relying on persistent memory.
- Do not expose the Hermes API/dashboard publicly without authentication, TLS and firewall rules.
- The gateway has not been activated by this repository change. Telegram credentials and the existing bot integration must be handled deliberately first.

## Current status

This is deployment scaffolding, not a completed or tested production deployment. The official image, provider, Telegram integration, persistence, backup/restore, and real task quality still need to be validated on the selected host.
