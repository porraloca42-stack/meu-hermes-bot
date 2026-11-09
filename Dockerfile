# Extend the official Hermes image with Hostless-compatible startup and encrypted DBByte persistence.
FROM nousresearch/hermes-agent:latest

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-boto3 python3-cryptography python3-yaml && \
    rm -rf /var/lib/apt/lists/*

COPY scripts/dbbyte_backup.py /opt/hermes/scripts/dbbyte_backup.py
COPY scripts/merge_hermes_config.py /opt/hermes/scripts/merge_hermes_config.py
COPY docker/hostless-entrypoint.sh /opt/hermes/docker/hostless-entrypoint.sh
COPY docker/hermes-exec-shim.sh /opt/hermes/bin/hermes
COPY docker/profile-hermes-path.sh /etc/profile.d/hermes.sh
COPY SOUL.md /opt/hermes/docker/SOUL.md
COPY AGENTS.md /opt/hermes/profile-seed/AGENTS.md
COPY .hermes/skills/ /opt/hermes/profile-seed/skills/

RUN chmod 0755 /opt/hermes/scripts/dbbyte_backup.py /opt/hermes/scripts/merge_hermes_config.py /opt/hermes/docker/hostless-entrypoint.sh /opt/hermes/bin/hermes && \
    chmod 0644 /etc/profile.d/hermes.sh && \
    install -d -o 10000 -g 10000 -m 0700 /app/.cache/hermes-home

# Hostless exposes writable /app/.cache but read-only /run. Start the container
# directly as Hermes UID/GID 10000: no runtime setuid/setgid or s6 privilege drop.
ENV HERMES_HOME=/app/.cache/hermes-home
ENV HERMES_WRITE_SAFE_ROOT=/app/.cache/hermes-home
ENV HOME=/app/.cache/hermes-home
ENV PATH="/app/.cache/hermes-home/.local/bin:/opt/hermes/.venv/bin:/opt/hermes/bin:${PATH}"

WORKDIR /app/.cache
USER 10000:10000
ENTRYPOINT ["/opt/hermes/docker/hostless-entrypoint.sh"]
CMD ["gateway", "run"]
