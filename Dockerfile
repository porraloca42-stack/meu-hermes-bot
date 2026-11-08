# Extend the official image without replacing its ENTRYPOINT or s6 init chain.
FROM nousresearch/hermes-agent:latest

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-boto3 python3-cryptography python3-yaml && \
    rm -rf /var/lib/apt/lists/*

COPY scripts/dbbyte_backup.py /opt/hermes/scripts/dbbyte_backup.py
COPY scripts/merge_hermes_config.py /opt/hermes/scripts/merge_hermes_config.py
COPY SOUL.md /opt/hermes/docker/SOUL.md
COPY AGENTS.md /opt/hermes/profile-seed/AGENTS.md
COPY .hermes/skills/ /opt/hermes/profile-seed/skills/
COPY docker/cont-init.d/01b-install-profile /etc/cont-init.d/01b-install-profile
COPY docker/cont-init.d/01a-dbbyte-restore /etc/cont-init.d/01a-dbbyte-restore
COPY docker/s6-rc.d/hermes-backup/type /etc/s6-overlay/s6-rc.d/hermes-backup/type
COPY docker/s6-rc.d/hermes-backup/run /etc/s6-overlay/s6-rc.d/hermes-backup/run
COPY docker/s6-rc.d/hermes-backup/dependencies.d/base /etc/s6-overlay/s6-rc.d/hermes-backup/dependencies.d/base
COPY docker/s6-rc.d/user/contents.d/hermes-backup /etc/s6-overlay/s6-rc.d/user/contents.d/hermes-backup

RUN chmod 0755 /opt/hermes/scripts/dbbyte_backup.py /opt/hermes/scripts/merge_hermes_config.py /etc/cont-init.d/01a-dbbyte-restore /etc/cont-init.d/01b-install-profile /etc/s6-overlay/s6-rc.d/hermes-backup/run

# Hostless mounts /app/.cache as a writable, ephemeral 2 GiB path. Hermes state is
# restored from DBByte before gateway startup; do not write into the read-only root.
ENV HERMES_HOME=/app/.cache/hermes-home
ENV HERMES_WRITE_SAFE_ROOT=/app/.cache/hermes-home
ENV HOME=/app/.cache/hermes-home
ENV PATH="/app/.cache/hermes-home/.local/bin:${PATH}"

# Preserve upstream ENTRYPOINT and gateway command.
WORKDIR /app/.cache/hermes-home
CMD ["gateway", "run"]
