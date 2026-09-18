FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY apps/api ./apps/api
COPY packages ./packages

RUN pip install --no-cache-dir -e packages/common -e packages/vision -e packages/drift -e packages/ais -e packages/attribution -e packages/rag -e packages/geospatial -e packages/knowledge -e packages/agents -e packages/evaluation -e apps/api

CMD ["uvicorn", "oceantrace_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

