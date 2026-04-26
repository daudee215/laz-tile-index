# API reference

The library exposes five public symbols.

## `build_index(src, *, target_per_cell=5_000, sidecar_path=None, reordered_path=None) -> GridIndex`

Build a spatial tile index for a LAS/LAZ file. Reorders points so each grid
cell holds contiguous indices, writes a new LAS file alongside the source
(default `<stem>.indexed.las`), and writes a JSON sidecar (default
`<stem>.indexed.las.lzti.json`) with the cell ranges. Returns the in-memory
`GridIndex` for immediate querying.

`target_per_cell` controls grid resolution: the grid is sized so that an
average cell holds approximately this many points. A smaller value gives
faster queries at the cost of a larger sidecar.

## `load_index(sidecar_path) -> GridIndex`

Load a previously built JSON sidecar from disk.

## `query_index(index, bbox) -> SpatialQueryResult`

Return points within `bbox = (minx, miny, maxx, maxy)` (inclusive) by
reading only intersecting cells. The query is out-of-core: only the
contiguous point ranges intersecting the bbox are read from the LAS file.

## `GridIndex`, `IndexHeader`, `SpatialQueryResult`

Frozen dataclasses describing the index, its metadata, and a query result.
