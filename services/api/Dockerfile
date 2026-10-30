# API image (plan, section 4). In Phase 4 it carries only the database
# migrations, whose offline SQL the superuser applies inside the database
# container. Built on VM1 from the repository root.
FROM ghcr.io/astral-sh/uv:0.13.2@sha256:b9fddcde095a7aeafd499024adb8927df6619c7c5672f5ff7126474715f62ba4 AS uv

FROM python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb AS base
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_CACHE_DIR=/tmp/uv-cache
WORKDIR /src

FROM base AS api
COPY pyproject.toml uv.lock ./
COPY services/api/pyproject.toml services/api/
COPY services/worker/pyproject.toml services/worker/
RUN --mount=type=cache,target=/tmp/uv-cache \
    uv sync --frozen --no-dev --package pathsol-api --no-install-workspace
COPY services/api/src services/api/src
RUN --mount=type=cache,target=/tmp/uv-cache \
    uv sync --frozen --no-dev --package pathsol-api --no-editable
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1
USER 5433:5433

# The tests run the schema on a throwaway cluster of the same PostgreSQL as
# production (18.6-1.pgdg13+2), signed by the PGDG key checked in Phase 3.
FROM api AS teste
USER root
ARG PG_VERSION=18.6-1.pgdg13+2
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl gnupg; \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/pgdg.gpg; \
    gpg --show-keys --with-colons /usr/share/keyrings/pgdg.gpg | grep -q '^fpr:::::::::B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8:$'; \
    echo "deb [signed-by=/usr/share/keyrings/pgdg.gpg] https://apt.postgresql.org/pub/repos/apt trixie-pgdg main" > /etc/apt/sources.list.d/pgdg.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends postgresql-common; \
    sed -ri 's/#(create_main_cluster) .*$/\1 = false/' /etc/postgresql-common/createcluster.conf; \
    apt-get install -y --no-install-recommends "postgresql-18=$PG_VERSION" "postgresql-client-18=$PG_VERSION" "libpq5=$PG_VERSION"; \
    rm -rf /var/lib/apt/lists/*; \
    useradd --uid 5433 --create-home teste
COPY services/api/tests services/api/tests
USER 5433:5433
CMD ["python", "-m", "unittest", "discover", "-s", "services/api/tests"]
