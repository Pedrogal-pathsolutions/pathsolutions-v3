# Worker image (plan, sections 4 and 10): Python 3.13 by digest, every
# dependency from the workspace's single uv lockfile. The CUDA runtime comes in
# the torch wheel; VM2 provides only the driver. Built on VM1 from the
# repository root and sent to VM2 with docker save | docker load.
FROM ghcr.io/astral-sh/uv:0.13.2@sha256:b9fddcde095a7aeafd499024adb8927df6619c7c5672f5ff7126474715f62ba4 AS uv

FROM python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb AS base
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_CACHE_DIR=/tmp/uv-cache
WORKDIR /src

FROM base AS worker
COPY pyproject.toml uv.lock ./
COPY services/worker/pyproject.toml services/worker/
RUN --mount=type=cache,target=/tmp/uv-cache \
    uv sync --frozen --no-dev --package pathsol-worker --no-install-workspace
COPY services/worker/src services/worker/src
RUN --mount=type=cache,target=/tmp/uv-cache \
    uv sync --frozen --no-dev --package pathsol-worker --no-editable
# Offline at run time (plan, section 10.1): the weights and the model's code
# come from a read-only volume, and nothing is fetched from the hub.
ENV PATH=/opt/venv/bin:$PATH \
    HF_HUB_OFFLINE=1 \
    HF_HOME=/tmp/hf \
    PYTHONDONTWRITEBYTECODE=1
USER 5433:5433
ENTRYPOINT ["python", "-m"]

FROM worker AS teste
USER root
RUN --mount=type=cache,target=/tmp/uv-cache \
    uv sync --frozen --package pathsol-worker --no-editable
COPY services/worker/tests services/worker/tests
USER 5433:5433
CMD ["unittest", "discover", "-s", "services/worker/tests"]
