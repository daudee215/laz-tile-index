# Roadmap

## v0.1 (now)

- Uniform-grid JSON sidecar over LAS files.
- `build_index`, `load_index`, `query_index`.
- CLI: `laz-tile-index build|query`.
- Reference dataset + integration test on 100k synthetic points.
- Benchmark suite via pytest-benchmark.

## v0.2 (next)

- Adaptive quadtree index for skewed distributions; opt-in `--mode quadtree`.
- LAZ output (via `lazrs`) so the reordered file stays compressed.
- Directory-of-files index that aggregates sidecars across many `.las` chunks.
- COPC emit-along-side mode for downstream tools that prefer COPC.

## v1.0 (stable goal)

- Streaming build mode (no reorder pass: scan once, mmap output).
- Optional R-tree backend behind a feature flag.
- Concurrent query support (read-only sidecar, multi-process safe).
- Full conformance tests against PDAL and LAStools-indexed inputs.
