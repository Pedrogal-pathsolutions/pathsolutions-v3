# Plan 7 (pattern 8): the official PostgreSQL 18 image plus pgBackRest, because
# archive_command runs inside the database container.
FROM postgres:18.6-trixie@sha256:979bccfde35445db618c65107d27d08c6c21339d8dc3ad4c830c6633947be0e4

# On VM1, UID 999 is the monitor agent's collector and GID 999 is
# systemd-journal, so the database files take an ID that is free on the host.
# The base image has no CA bundle, which pgBackRest needs to verify Azure.
ARG POSTGRES_ID=5432
ARG PGBACKREST_VERSION=2.60.0-1.pgdg13+1
ARG PGBACKREST_SHA256=609dae5ee9c413e25fde3bd0fc2fd2140cb93d137baeedf152ffa1998786ab60

RUN set -eux; \
    groupmod -g "$POSTGRES_ID" postgres; \
    usermod -u "$POSTGRES_ID" -g "$POSTGRES_ID" postgres; \
    find / -xdev -uid 999 -exec chown -h postgres '{}' +; \
    find / -xdev -gid 999 -exec chgrp -h postgres '{}' +; \
    apt-get update; \
    cd /tmp; \
    apt-get download "pgbackrest=$PGBACKREST_VERSION"; \
    echo "$PGBACKREST_SHA256  pgbackrest_${PGBACKREST_VERSION}_amd64.deb" | sha256sum -c -; \
    apt-get install -y --no-install-recommends ca-certificates "./pgbackrest_${PGBACKREST_VERSION}_amd64.deb"; \
    rm "pgbackrest_${PGBACKREST_VERSION}_amd64.deb"; \
    rm -rf /var/lib/apt/lists/*; \
    test -z "$(find / -xdev \( -uid 999 -o -gid 999 \) -print -quit)"; \
    pgbackrest version
