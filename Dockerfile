# Use the official Hermes Agent image and its bundled runtime.
FROM nousresearch/hermes-agent:latest

# Start the persistent messaging gateway (Telegram, Discord, etc.).
CMD ["gateway", "run"]
