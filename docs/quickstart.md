# Quickstart

## Install

```
pip install laz-tile-index
```

## Build an index

```python
from laz_tile_index import build_index

idx = build_index("data/forest.las", target_per_cell=5_000)
print(idx.header.bbox, idx.header.point_count, idx.header.grid_shape)
```

This writes two files next to the source:

- `forest.indexed.las` — point order rearranged so each grid cell is contiguous.
- `forest.indexed.las.lzti.json` — the JSON sidecar with the cell ranges.

## Query a bbox

```python
from laz_tile_index import load_index, query_index

idx = load_index("data/forest.indexed.las.lzti.json")
hits = query_index(idx, (637000.0, 4789000.0, 637200.0, 4789200.0))
print(hits.indices.size, "points inside bbox")
```

## CLI

```
laz-tile-index build data/forest.las
laz-tile-index query data/forest.indexed.las.lzti.json 637000 4789000 637200 4789200
```
