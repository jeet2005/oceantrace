# Development

OCEANTRACE is now treated as one complete product, not a sequence of demo milestones.

Development rules:

- Build real backend capability first.
- Keep fixtures only for tests and local smoke checks.
- Do not report scientific performance until measured on real or controlled evaluation data.
- Do not claim a vessel caused a spill; report investigative ranking and uncertainty.
- Every important report claim must reference evidence IDs.
- Every external dependency must be replaceable through a local interface.

Current backend priority:

1. Persistent PostgreSQL schema and Alembic migrations.
2. Real AIS/raster ingestion from files.
3. CRS-aware geospatial calculations.
4. Real drift simulation with current/wind inputs.
5. RAG ingestion and citation verification.

No paid APIs are required for local development.
