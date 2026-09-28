FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /workspace

COPY pyproject.toml uv.lock README.md ./
COPY app/pyproject.toml app/README.md ./app/
RUN uv sync --frozen --no-dev --all-packages --no-install-workspace

COPY src ./src
COPY app/src ./app/src
RUN uv sync --frozen --no-dev --all-packages

EXPOSE 8000

CMD ["/workspace/.venv/bin/app"]