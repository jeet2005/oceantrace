# Threat Model

Initial risks:

- Uploaded file abuse through oversized, malformed, or path-traversal payloads.
- Secret leakage through logs or committed configuration.
- Hallucinated attribution or unsupported investigation claims.
- Untrusted datasets with malformed AIS coordinates or timestamps.

Mitigations:

- Validate uploads, sanitize filenames, restrict file size, and avoid dangerous paths.
- Keep secrets in environment variables and `.env`, never committed.
- Require evidence IDs for report claims.
- Validate all AIS and geospatial inputs before processing.

