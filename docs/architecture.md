# Architecture

OCEANTRACE separates scientific computation from language generation.

- Computer vision packages detect and characterize slicks.
- Geospatial and drift packages calculate regions, trajectories, and uncertainty.
- AIS and attribution packages normalize tracks, filter candidates, and calculate scores.
- RAG and knowledge packages retrieve contextual evidence with citations.
- Agent packages orchestrate evidence-grounded reports without inventing facts.

The backend exposes versioned FastAPI endpoints and stores structured metadata in PostgreSQL. Large rasters, masks, and model checkpoints are referenced by path/object identifier, not stored directly in the database.

## Development Fixture Slice

`oceantrace_api.pipeline.build_demo_investigation` runs the current end-to-end local fixture:

1. Create a fixture satellite observation.
2. Return a fixture spill detection and geometry.
3. Estimate a probable origin region and future corridor.
4. Generate fixture AIS tracks.
5. Score candidate vessels with deterministic feature weights.
6. Attach evidence records with provenance.
7. Generate a report with claim-level evidence IDs and disclaimers.

This slice is suitable for local integration testing. It is not a scientific benchmark and is not the production path.
