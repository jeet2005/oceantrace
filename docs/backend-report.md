# Backend Report

## Current Location

The active project is in `D:\oceantrace`.

## What Is Done

- FastAPI application with versioned `/api/v1` routes.
- Typed Pydantic domain models for investigations, satellite observations, detections, drift simulations, AIS points, vessel tracks, candidate scores, evidence, reports, and pipeline steps.
- Modular backend service layer:
  - `services/detection.py`: satellite observation and detection service contract implementation.
  - `services/drift.py`: baseline Monte Carlo-style drift result contract.
  - `services/ais.py`: development AIS fixture track generation.
  - `services/ais_ingestion.py`: AIS CSV ingestion, validation, rejection accounting, and track reconstruction.
  - `services/observation_ingestion.py`: satellite observation metadata sidecar ingestion.
  - `services/scoring.py`: transparent candidate scoring from deterministic features.
  - `services/evidence.py`: provenance-preserving evidence collection.
  - `services/reporting.py`: evidence-linked report generation.
  - `services/pipeline_service.py`: orchestration of the end-to-end investigation flow.
  - `services/geospatial.py`: distance, bearing, centroid, and polygon helpers.
- Local in-memory backend infrastructure:
  - `storage/repository.py`: investigation result repository.
  - `storage/jobs.py`: job record store for async-compatible workflow shape.
- API endpoints:
  - `GET /api/v1/health`
  - `POST /api/v1/investigations`
  - `GET /api/v1/investigations`
  - `POST /api/v1/investigations/run`
  - `POST /api/v1/satellite-observations`
  - `POST /api/v1/ais/datasets`
  - `GET /api/v1/dev/fixtures/investigations`
  - `POST /api/v1/dev/fixtures/investigations`
  - `POST /api/v1/dev/fixtures/investigations/jobs`
  - `GET /api/v1/investigations/{case_id}`
  - `GET /api/v1/investigations/{case_id}/report`
  - `GET /api/v1/investigations/{case_id}/candidates/{mmsi}`
  - `POST /api/v1/investigations/{case_id}/ask`
  - `GET /api/v1/jobs/{job_id}`
- Backend tests covering API routes, service composition, model validation, fixture pipeline behavior, and evidence/report integrity.

## Verification

Latest backend checks:

- `python -m pytest`: 12 passed.
- `python -m ruff check . --no-cache`: passed.
- `python -m mypy apps/api/src packages tests --cache-dir C:\Users\jeets\AppData\Local\Temp\oceantrace-mypy-cache`: passed.

The normal Ruff/mypy cache directories inside `D:\oceantrace` had permission issues, so cache-free/temp-cache commands were used.

## What Remains

- Replace in-memory repository/job stores with PostgreSQL tables and migrations.
- Add real background execution through a worker abstraction.
- Implement real raster ingestion, metadata validation, and safe upload handling.
- Implement actual satellite segmentation model loading/inference behind the existing interface.
- Implement real ocean/wind field ingestion and numerical particle simulation.
- Implement CSV/Parquet AIS ingestion and validation from user-provided datasets.
- Add a production RAG index with local embeddings, keyword retrieval, reranking, and citation verification.
- Add claim critic workflow that checks unsupported and contradictory claims.
- Add authentication/authorization if this becomes a shared deployed service.
- Add Docker verification after Docker Desktop/Linux engine is available.

## Scientific Boundary

The current backend has real service boundaries and ingestion contracts, with development fixtures for repeatable testing. It demonstrates architecture, orchestration, scoring transparency, evidence references, and report discipline. It does not claim real-world detection accuracy or vessel attribution accuracy until real datasets and evaluations are added.
