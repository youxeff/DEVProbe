# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS node-tools
WORKDIR /tools
COPY tools/package*.json ./
RUN npm ci --omit=dev --no-audit --no-fund

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY tools/requirements.txt /app/tools/requirements.txt
RUN python -m venv /app/tools/.venv && /app/tools/.venv/bin/pip install --no-cache-dir -r /app/tools/requirements.txt
COPY --from=node-tools /usr/local/bin/node /usr/local/bin/node
COPY --from=node-tools /tools/node_modules /app/tools/node_modules
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY tools/eslint.config.mjs tools/semgrep-rules.yml ./tools/
RUN groupadd --gid 10001 devprobe && useradd --uid 10001 --gid 10001 --no-create-home devprobe
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
