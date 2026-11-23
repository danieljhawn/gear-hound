FROM ghcr.io/astral-sh/uv:0.13.9 AS uv
FROM python:3.12-slim

COPY --from=uv /uv /uvx /bin/

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system gearhound \
    && useradd --system --gid gearhound --create-home gearhound \
    && mkdir -p /data \
    && chown gearhound:gearhound /data

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=gearhound:gearhound app ./app
COPY --chown=gearhound:gearhound migrations ./migrations
COPY --chown=gearhound:gearhound alembic.ini README.md ./
RUN uv sync --frozen --no-dev

USER gearhound
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
