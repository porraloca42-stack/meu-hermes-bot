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
COPY docker/cont-init.d/01b-install-profile /etc/cont-init.d/01b-install-profile

RUN chmod 0755 /opt/hermes/scripts/dbbyte_backup.py /opt/hermes/scripts/merge_hermes_config.py /opt/hermes/docker/hostless-entrypoint.sh /opt/hermes/bin/hermes /etc/cont-init.d/01b-install-profile && chmod 0644 /etc/profile.d/hermes.sh

# Hostless exposes writable /app/.cache but read-only /run. Bypass upstream
# /init/s6 startup, keep the gateway as PID 1, and run DBByte backup alongside it.
ENV HERMES_HOME=/app/.cache/hermes-home
ENV HERMES_WRITE_SAFE_ROOT=/app/.cache/hermes-home
ENV HOME=/app/.cache/hermes-home
ENV PATH="/app/.cache/hermes-home/.local/bin:${PATH}"

WORKDIR /app/.cache
ENTRYPOINT ["/opt/hermes/docker/hostless-entrypoint.sh"]
CMD ["gateway", "run"]
