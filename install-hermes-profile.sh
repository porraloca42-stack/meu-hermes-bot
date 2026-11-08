#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

mkdir -p "$HERMES_HOME/skills"

if [[ ! -e "$HERMES_HOME/AGENTS.md" ]]; then
  cp "$REPO_DIR/AGENTS.md" "$HERMES_HOME/AGENTS.md"
  echo "Installed AGENTS.md"
else
  echo "Kept existing AGENTS.md"
fi

if [[ ! -e "$HERMES_HOME/SOUL.md" ]]; then
  cp "$REPO_DIR/SOUL.md" "$HERMES_HOME/SOUL.md"
  echo "Installed SOUL.md"
else
  echo "Kept existing SOUL.md"
fi

if [[ ! -e "$HERMES_HOME/config.yaml" ]]; then
  cp "$REPO_DIR/hermes-config.yaml.example" "$HERMES_HOME/config.yaml"
  echo "Installed config.yaml example"
else
  echo "Kept existing config.yaml; review hermes-config.yaml.example manually"
fi

cp -Rn "$REPO_DIR/.hermes/skills/." "$HERMES_HOME/skills/"
echo "Copied project skills (existing files were not overwritten)"
echo "Hermes profile prepared at: $HERMES_HOME"
echo "Next: configure a verified model provider and Telegram secrets outside Git."
