FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/venv

WORKDIR /_lock

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY pyproject.toml /_lock/
COPY uv.lock /_lock/

RUN --mount=type=cache,target=/root/.cache <<EOT
  uv sync --frozen --no-dev
EOT


# ========================================================================
FROM python:3.12-slim-bookworm

# It is important to use the image that matches the builder, as the path to the
# Python executable must be the same, e.g., using `python:3.11-slim-bookworm`
# will fail.

# Copy the application from the builder
COPY --from=builder --chown=app:app /venv /venv
# Place executables in the environment at the front of the path
ENV PATH="/venv/bin:$PATH"

WORKDIR /app

COPY ./app /app/app

RUN echo "alias ls='ls --color=auto'" > ~/.bashrc \
    && echo "alias p='python'" >> ~/.bashrc \
    && echo "alias la='ls -a'" >> ~/.bashrc \
    && echo "alias l='ls'" >> ~/.bashrc \
    && echo "alias ll='ls -l'" >> ~/.bashrc

ENTRYPOINT []
