# Data

Use `data/raw`, `data/interim`, `data/processed`, and `data/samples` for local development artifacts. Real satellite or AIS datasets are not committed.

The backend now includes initial ingestion contracts for satellite metadata sidecars and AIS CSV files. Next work should add Sentinel-1 SAFE/GeoTIFF readers, CRS validation, Parquet AIS support, and secure upload handling.
