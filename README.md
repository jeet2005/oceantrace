# OCEANTRACE

OCEANTRACE is a backend-first oil-spill investigation system for SIH Problem Statement 26143: leveraging satellite imagery to detect oil spills at sea and correlating AIS data to rank possible source vessels.

The system is designed for zero paid API cost during development. Local/open-source providers are the default, including FastAPI, React, PostgreSQL, Qdrant, Ollama, Hugging Face models, PyTorch, and geospatial Python libraries.

## Current System Scope

The current local system includes:

- Modular monorepo structure for backend, frontend, scientific packages, docs, data, and tests.
- FastAPI skeleton with versioned routes and typed Pydantic domain models.
- Provider interfaces for satellite models, drift simulation, AIS processing, attribution scoring, LLMs, embeddings, reranking, and RAG retrieval.
- PostgreSQL metadata schema foundation through SQLAlchemy models.
- React + TypeScript operational dashboard shell.
- Docker development services for PostgreSQL, Qdrant, and the API.
- Unit and API tests plus Ruff, mypy, and frontend build configuration.
- Development fixture pipeline exposed under `/api/v1/dev/fixtures`.
- Structured real-workflow endpoints for satellite metadata ingestion, AIS CSV ingestion, and investigation execution.
- Candidate scores with feature breakdowns and evidence IDs.

It does not yet train a satellite ML model, ingest Sentinel-1 SAFE products, run production drift physics, or run a local LLM. Those are intentionally left behind replaceable interfaces so the system does not fabricate scientific performance.

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e packages/common -e packages/vision -e packages/drift -e packages/ais -e packages/attribution -e packages/rag -e packages/geospatial -e packages/knowledge -e packages/agents -e packages/evaluation -e apps/api
pip install -e ".[dev]"
```

Run the API:

```bash
uvicorn oceantrace_api.main:app --reload --app-dir apps/api/src
```

Development fixture API:

```bash
curl http://localhost:8000/api/v1/dev/fixtures/investigations
```

Real workflow shape:

```bash
curl -X POST http://localhost:8000/api/v1/satellite-observations
curl -X POST http://localhost:8000/api/v1/ais/datasets
curl -X POST http://localhost:8000/api/v1/investigations/run
```

Run the web app:

```bash
cd apps/web
npm install
npm run dev
```

Run development services:

```bash
docker compose up --build
```

## Verification

```bash
pytest
ruff check .
mypy apps/api/src packages tests
cd apps/web && npm test && npm run build
docker build -f docker/api.Dockerfile -t oceantrace-api:dev .
```

Backend status details are tracked in [docs/backend-report.md](docs/backend-report.md).

## Scientific Disclaimer

OCEANTRACE must never claim that a ranked vessel definitively caused an oil spill. Candidate scores are investigative rankings based on available evidence, uncertainty, and reproducible calculations.
