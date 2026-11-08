# Extend the official image without replacing its ENTRYPOINT or s6 init chain.
FROM nousresearch/hermes-agent:latest

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-boto3 python3-cryptography && \
    rm -rf /var/lib/apt/lists/*

COPY scripts/dbbyte_backup.py /opt/hermes/scripts/dbbyte_backup.py
COPY docker/cont-init.d/01a-dbbyte-restore /etc/cont-init.d/01a-dbbyte-restore
COPY docker/s6-rc.d/hermes-backup/type /etc/s6-overlay/s6-rc.d/hermes-backup/type
COPY docker/s6-rc.d/hermes-backup/run /etc/s6-overlay/s6-rc.d/hermes-backup/run
COPY docker/s6-rc.d/hermes-backup/dependencies.d/base /etc/s6-overlay/s6-rc.d/hermes-backup/dependencies.d/base
COPY docker/s6-rc.d/user/contents.d/hermes-backup /etc/s6-overlay/s6-rc.d/user/contents.d/hermes-backup

RUN chmod 0755 /opt/hermes/scripts/dbbyte_backup.py /etc/cont-init.d/01a-dbbyte-restore /etc/s6-overlay/s6-rc.d/hermes-backup/run

# Preserve upstream ENTRYPOINT and gateway command.
CMD ["gateway", "run"]
