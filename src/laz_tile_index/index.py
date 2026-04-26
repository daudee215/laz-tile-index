"""Core spatial-index implementation.

Format
------
The sidecar is a single JSON file with the same stem as the LAS/LAZ. Keys:
- ``schema``: ``"laz-tile-index/v1"``
- ``header``: bbox, point count, grid shape, source filename, source SHA-1.
- ``cells``: dict ``"i,j" -> [start, count]`` listing inclusive point ranges
  inside each grid cell. ``start`` is the index of the first point (0-based)
  in the LAS file; ``count`` is the number of contiguous points belonging to
  that cell.

Points are reordered during build so each cell contains contiguous points,
making bbox queries simple range reads.

Design
------
Rejected alternatives (see docs/adr/0001-spatial-index.md):
1. R-tree: heavy dependency (rtree/spatialindex C lib), not pure-Python.
2. KD-tree: in-memory only; defeats out-of-core goal.
3. LAStools .lax: binary format, GPL-encumbered tooling, no Python writer.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import pathlib
from collections.abc import Iterator

import laspy  # type: ignore[import-untyped]
import numpy as np
from numpy.typing import NDArray

SCHEMA = "laz-tile-index/v1"


@dataclasses.dataclass(frozen=True)
class IndexHeader:
    """Index metadata describing the source point cloud and grid layout."""

    bbox: tuple[float, float, float, float]
    """Source bbox as ``(minx, miny, maxx, maxy)`` in source CRS units."""

    point_count: int
    """Number of points indexed (equals ``len(las)``)."""

    grid_shape: tuple[int, int]
    """``(nx, ny)`` cell counts."""

    source_filename: str
    """Basename of the LAS/LAZ file the index was built against."""

    source_sha1: str
    """SHA-1 hex digest of the source file's first MiB and tail (fast fingerprint)."""

    cell_size: tuple[float, float]
    """``(width, height)`` of each cell in source CRS units."""


@dataclasses.dataclass(frozen=True)
class SpatialQueryResult:
    """Result of a bbox query: point coordinates and original point indices."""

    xy: NDArray[np.float64]
    """``(N, 2)`` array of XY coordinates of matching points."""

    z: NDArray[np.float64]
    """``(N,)`` array of Z coordinates."""

    indices: NDArray[np.int64]
    """``(N,)`` array of original 0-based point indices in the source file."""


@dataclasses.dataclass(frozen=True)
class GridIndex:
    """In-memory representation of a built (or loaded) spatial index."""

    header: IndexHeader
    cells: dict[tuple[int, int], tuple[int, int]]
    """Mapping of ``(i, j)`` -> ``(start, count)`` ranges in the reordered file."""

    source_path: pathlib.Path
    """Path to the LAS/LAZ this index points at (after build, this is the
    *reordered* file written next to the original under ``.indexed.las``)."""


def _fast_sha1(path: pathlib.Path) -> str:
    """Cheap fingerprint: SHA-1 of first 1 MiB and last 1 MiB of the file."""
    h = hashlib.sha1()
    size = path.stat().st_size
    with path.open("rb") as f:
        h.update(f.read(min(size, 1 << 20)))
        if size > (1 << 21):
            f.seek(-(1 << 20), 2)
            h.update(f.read(1 << 20))
    return h.hexdigest()


def _choose_grid(
    bbox: tuple[float, float, float, float], points: int, target_per_cell: int = 5_000
) -> tuple[int, int]:
    """Choose a square-ish grid such that average cell holds ~target_per_cell points."""
    cells_total = max(1, points // target_per_cell)
    side = max(1, int(math.sqrt(cells_total)))
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    if width == 0 or height == 0:
        return (1, 1)
    aspect = width / height
    nx = max(1, int(round(side * math.sqrt(aspect))))
    ny = max(1, int(round(side / math.sqrt(aspect))))
    return (nx, ny)


def _cell_indices(
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    bbox: tuple[float, float, float, float],
    nx: int,
    ny: int,
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Return ``(i, j)`` cell index per point, clamped to ``[0, nx-1]`` / ``[0, ny-1]``."""
    minx, miny, maxx, maxy = bbox
    cw = (maxx - minx) / nx
    ch = (maxy - miny) / ny
    if cw == 0 or ch == 0:
        return (np.zeros_like(x, dtype=np.int64), np.zeros_like(y, dtype=np.int64))
    i = np.clip(((x - minx) / cw).astype(np.int64), 0, nx - 1)
    j = np.clip(((y - miny) / ch).astype(np.int64), 0, ny - 1)
    return i, j


def build_index(
    src: pathlib.Path | str,
    *,
    target_per_cell: int = 5_000,
    sidecar_path: pathlib.Path | str | None = None,
    reordered_path: pathlib.Path | str | None = None,
) -> GridIndex:
    """Build a spatial tile index for a LAS/LAZ file.

    Reorders points so each grid cell holds contiguous indices, writes a new
    LAS file alongside the source (``<stem>.indexed.las``), and writes a JSON
    sidecar (``<stem>.indexed.las.lzti.json``) with the cell ranges.
    """
    src = pathlib.Path(src)
    las = laspy.read(str(src))
    x = np.asarray(las.x, dtype=np.float64)
    y = np.asarray(las.y, dtype=np.float64)
    n = int(len(x))
    if n == 0:
        raise ValueError(f"empty LAS file: {src}")

    bbox = (float(x.min()), float(y.min()), float(x.max()), float(y.max()))
    nx, ny = _choose_grid(bbox, n, target_per_cell=target_per_cell)
    cw = (bbox[2] - bbox[0]) / nx if nx else 1.0
    ch = (bbox[3] - bbox[1]) / ny if ny else 1.0

    i, j = _cell_indices(x, y, bbox, nx, ny)
    cell_id = i * ny + j
    order = np.argsort(cell_id, kind="stable")

    # Reorder LAS arrays in place
    las.points = las.points[order]
    if reordered_path is None:
        reordered = src.with_suffix(".indexed.las")
    else:
        reordered = pathlib.Path(reordered_path)
    las.write(str(reordered))

    # Compute cell ranges from the now-sorted cell_id
    sorted_cell = cell_id[order]
    cells: dict[tuple[int, int], tuple[int, int]] = {}
    if n > 0:
        # find run boundaries
        change = np.concatenate(([0], 1 + np.flatnonzero(sorted_cell[1:] != sorted_cell[:-1]), [n]))
        for k in range(len(change) - 1):
            start = int(change[k])
            count = int(change[k + 1] - change[k])
            cv = int(sorted_cell[start])
            cells[(cv // ny, cv % ny)] = (start, count)

    header = IndexHeader(
        bbox=bbox,
        point_count=n,
        grid_shape=(nx, ny),
        source_filename=reordered.name,
        source_sha1=_fast_sha1(reordered),
        cell_size=(cw, ch),
    )
    if sidecar_path is None:
        sidecar = reordered.with_suffix(reordered.suffix + ".lzti.json")
    else:
        sidecar = pathlib.Path(sidecar_path)
    sidecar.write_text(
        json.dumps(
            {
                "schema": SCHEMA,
                "header": dataclasses.asdict(header),
                "cells": {f"{i},{j}": [s, c] for (i, j), (s, c) in cells.items()},
            },
            indent=2,
        )
    )
    return GridIndex(header=header, cells=cells, source_path=reordered)


def load_index(sidecar_path: pathlib.Path | str) -> GridIndex:
    """Load a previously built JSON sidecar index."""
    sidecar = pathlib.Path(sidecar_path)
    blob = json.loads(sidecar.read_text())
    if blob.get("schema") != SCHEMA:
        raise ValueError(f"unsupported sidecar schema: {blob.get('schema')!r}")
    h = blob["header"]
    header = IndexHeader(
        bbox=tuple(h["bbox"]),
        point_count=int(h["point_count"]),
        grid_shape=tuple(h["grid_shape"]),
        source_filename=str(h["source_filename"]),
        source_sha1=str(h["source_sha1"]),
        cell_size=tuple(h["cell_size"]),
    )
    cells: dict[tuple[int, int], tuple[int, int]] = {}
    for k, v in blob.get("cells", {}).items():
        i_s, j_s = k.split(",")
        cells[(int(i_s), int(j_s))] = (int(v[0]), int(v[1]))
    src = sidecar.parent / header.source_filename
    return GridIndex(header=header, cells=cells, source_path=src)


def _intersecting_cells(
    bbox_query: tuple[float, float, float, float], header: IndexHeader
) -> Iterator[tuple[int, int]]:
    minx, miny, maxx, maxy = bbox_query
    h_minx, h_miny, h_maxx, h_maxy = header.bbox
    if maxx < h_minx or minx > h_maxx or maxy < h_miny or miny > h_maxy:
        return
    nx, ny = header.grid_shape
    cw, ch = header.cell_size
    if cw <= 0 or ch <= 0:
        yield (0, 0)
        return
    i0 = max(0, int((minx - h_minx) / cw))
    i1 = min(nx - 1, int((maxx - h_minx) / cw))
    j0 = max(0, int((miny - h_miny) / ch))
    j1 = min(ny - 1, int((maxy - h_miny) / ch))
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            yield (i, j)


def query_index(
    index: GridIndex,
    bbox: tuple[float, float, float, float],
) -> SpatialQueryResult:
    """Return points within ``bbox`` (inclusive) by reading only intersecting cells.

    Out-of-core: opens the LAS file, reads only the contiguous point ranges
    matching intersecting cells, and applies the precise bbox filter to each.
    """
    minx, miny, maxx, maxy = bbox
    xs: list[NDArray[np.float64]] = []
    ys: list[NDArray[np.float64]] = []
    zs: list[NDArray[np.float64]] = []
    idxs: list[NDArray[np.int64]] = []

    with laspy.open(str(index.source_path)) as reader:
        for ij in _intersecting_cells(bbox, index.header):
            r = index.cells.get(ij)
            if r is None:
                continue
            start, count = r
            reader.seek(start)
            points = reader.read_points(count)
            x = np.asarray(points.x, dtype=np.float64)
            y = np.asarray(points.y, dtype=np.float64)
            z = np.asarray(points.z, dtype=np.float64)
            mask = (x >= minx) & (x <= maxx) & (y >= miny) & (y <= maxy)
            if mask.any():
                xs.append(x[mask])
                ys.append(y[mask])
                zs.append(z[mask])
                idxs.append(np.flatnonzero(mask).astype(np.int64) + start)

    if not xs:
        return SpatialQueryResult(
            xy=np.empty((0, 2), dtype=np.float64),
            z=np.empty((0,), dtype=np.float64),
            indices=np.empty((0,), dtype=np.int64),
        )
    xy = np.column_stack([np.concatenate(xs), np.concatenate(ys)])
    return SpatialQueryResult(xy=xy, z=np.concatenate(zs), indices=np.concatenate(idxs))
