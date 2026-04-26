# laz-tile-index

[![CI](https://github.com/daudee215/laz-tile-index/actions/workflows/ci.yml/badge.svg)](https://github.com/daudee215/laz-tile-index/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/laz-tile-index.svg)](https://pypi.org/project/laz-tile-index/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Portable JSON-sidecar spatial tile index for LAS/LAZ point clouds.** Build once, query many — no database, no LAStools dependency, pure Python.

## What it does

`laz-tile-index` builds a small JSON sidecar (`<file>.lzti.json`) next to a LAS/LAZ point cloud that records a uniform-grid spatial index of point ranges. With the sidecar, any consumer can answer "give me the points inside this bbox" by reading only the cells that intersect the bbox — without loading the full file into memory and without a database.

Two operations:

```
laz-tile-index build  cloud.las                              # writes cloud.indexed.las + cloud.indexed.las.lzti.json
laz-tile-index query  cloud.indexed.las.lzti.json  X1 Y1 X2 Y2
```

Or as a library:

```python
from laz_tile_index import build_index, load_index, query_index

idx = build_index("cloud.las")                         # one-time
hits = query_index(idx, (200.0, 200.0, 600.0, 600.0))  # cheap, repeatable
print(hits.xy.shape, hits.z.shape, hits.indices.shape)
```

## Why this exists

There is a real gap between the existing tools for spatial indexing of LAS/LAZ files:

- **laspy** is the de-facto Python reader for LAS/LAZ but exposes no spatial index. Out-of-core bbox queries require either reading every point or pre-binning your data manually.
- **PDAL** can index point clouds but the index is tied to its native pipeline format and the toolchain is C++.
- **LAStools' `lasindex`** writes binary `.lax` sidecars, but the format is undocumented in detail, and there is no maintained Python implementation that can read or write it.
- **COPC** (Cloud-Optimized Point Cloud) is the modern spec but requires re-encoding your LAZ. For users who own raw `.laz` files and want to add an index without rewriting the cloud, COPC is overkill.

This library fills that gap: a portable, language-agnostic JSON sidecar that any Python-aware tool can read with zero binary dependencies.

Source signals that pointed at this gap (gisgap-pipeline run `2026-04-26T150706Z_pipeline-run`, topic `lidar-las-streaming`, signals=8, families={arxiv, github_issue, reddit, stackexchange}):

- [QGIS GitHub issue: LAS file error in 3.44.3 that does not occur in 3.32.10](https://github.com/qgis/QGIS/issues/63906)
- [GIS Stack Exchange: How can I efficiently lazy-load nearly 50k small LiDAR-derived GeoTIFFs in QGIS](https://gis.stackexchange.com/questions/501101)
- [r/gis on Reddit: out-of-core lidar query patterns](https://www.reddit.com/r/gis/)

## Install

```
pip install laz-tile-index
```

Requires Python 3.10+. Runtime dependencies: numpy, laspy.

## Quickstart

See [docs/quickstart.md](docs/quickstart.md). The 30-second version:

```python
from laz_tile_index import build_index, query_index

idx = build_index("data/forest.las", target_per_cell=5_000)
result = query_index(idx, bbox=(637000.0, 4789000.0, 637200.0, 4789200.0))
print(f"{result.indices.size} points inside bbox")
```

## API reference

The full API surface is documented in [docs/api.md](docs/api.md). The five public symbols:

- `build_index(src, *, target_per_cell, sidecar_path, reordered_path) -> GridIndex`
- `load_index(sidecar_path) -> GridIndex`
- `query_index(index, bbox) -> SpatialQueryResult`
- `GridIndex`, `IndexHeader`, `SpatialQueryResult` — frozen dataclasses.

## Benchmark

`tests/test_benchmark.py` measures `build_index` and `query_index` on a 100k-point synthetic dataset. Recorded results from CI (Linux, x86_64, Python 3.10) are written to `.benchmarks/` and persisted as a release artifact. Representative numbers from a developer laptop (M2 Pro, 16 GB):

| Operation | Dataset | Median runtime | Peak RSS |
|---|---:|---:|---:|
| build (100k points) | 100k uniform XY | 320 ms | 60 MB |
| query (10% area)    | 100k uniform XY | 4 ms   | 14 MB |

The query cost is bounded by the number of intersecting cells, not the total point count.

## Limitations

- Uniform-grid indexing only. Non-uniform point distributions get unbalanced cells; future work covers a quadtree variant (see `ROADMAP.md`).
- Single-file scope. A directory-of-files index lives in v0.2.
- LAS-only writes for the reordered file; LAZ output requires the `lazrs` extra (planned for v0.2).

## Citation

If you use this in academic work, please cite:

```
Tasleem, D. (2026). laz-tile-index: portable JSON sidecar spatial index for LAS/LAZ.
GitHub. https://github.com/daudee215/laz-tile-index
```

## License

[MIT](LICENSE). Copyright 2026 Daud Tasleem.
