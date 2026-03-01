FROM oven/bun:latest AS web-build

WORKDIR /app/web
COPY web/ ./

RUN bun install
RUN bun run build


FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY cards.jsonl ./cards.jsonl

RUN pip install --no-cache-dir .

COPY --from=web-build /app/web/dist ./web/dist

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
