# OCEANTRACE Production Backlog

This project is no longer managed as milestone slices. The target is a complete real-world backend system for SIH 26143.

## Backend Core

- [x] Modular FastAPI application
- [x] Typed domain models
- [x] Investigation orchestration service
- [x] Candidate scoring service
- [x] Evidence-linked report service
- [x] In-memory repository and job contracts
- [x] AIS CSV ingestion service
- [x] Satellite metadata ingestion service
- [x] PostgreSQL persistence for all case metadata
- [x] Alembic migrations
- [x] Durable job queue and worker (RQ + Redis, with in-memory fallback for testing)
- [ ] Request IDs and structured logging middleware
- [ ] API error envelope and validation diagnostics

## Satellite System

- [x] Satellite observation data contract
- [x] Metadata sidecar ingestion
- [ ] Sentinel-1 SAFE/GeoTIFF reader
- [ ] CRS and transform validation
- [ ] Raster tiling pipeline
- [ ] SAR normalization and preprocessing
- [ ] Model registry and checkpoint loader
- [ ] U-Net/SegFormer inference adapter
- [ ] Mask stitching and post-processing
- [ ] GeoJSON polygon extraction from raster masks
- [ ] Area/perimeter/length/width from CRS-aware geometry

## Drift System

- [x] Drift simulation data contract
- [x] Baseline origin/forecast result model
- [ ] Wind/current data adapters
- [ ] Particle advection-diffusion engine
- [ ] Monte Carlo perturbation engine
- [ ] Probability corridor raster/vector output
- [ ] Backward release-window estimator
- [ ] Forward slick movement forecast

## AIS Attribution

- [x] AIS CSV parser
- [x] AIS point validation
- [x] Track reconstruction
- [x] Transparent candidate scoring formula
- [ ] Parquet ingestion
- [ ] Deduplication and gap detection
- [ ] Temporal/spatial index
- [ ] Interpolation service
- [ ] Route anomaly features
- [ ] Configurable score weights in database
- [ ] Evaluation over labeled scenario sets

## RAG And Reporting

- [x] Evidence and claim data contracts
- [x] Evidence-grounded report shape
- [ ] Document ingestion pipeline
- [ ] Local embedding provider
- [ ] BM25 keyword retrieval
- [ ] Vector retrieval
- [ ] Reranker adapter
- [ ] Citation verification
- [ ] Critic workflow for unsupported or contradicted claims
- [ ] Local Ollama report generation adapter

## Frontend

- [x] Basic investigation dashboard
- [ ] Real map with Leaflet/OpenStreetMap
- [ ] Upload screens for raster metadata and AIS
- [ ] Job progress view
- [ ] Evidence explorer
- [ ] Report export

## Operations

- [x] Docker Compose draft
- [x] Python tests/lint/type checks
- [x] Frontend build/test setup
- [ ] Docker build verification on a machine with Docker engine
- [ ] CI on GitHub
- [ ] Seed data command
- [ ] Production deployment profile
