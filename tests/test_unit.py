"""Unit tests for build/load/query."""

from __future__ import annotations

import pathlib

import numpy as np

from laz_tile_index import build_index, load_index, query_index


def test_build_creates_sidecar_and_indexed_las(grid_las: pathlib.Path) -> None:
    idx = build_index(grid_las, target_per_cell=64)
    assert idx.source_path.exists(), "indexed LAS file should exist"
    sidecar = idx.source_path.with_suffix(idx.source_path.suffix + ".lzti.json")
    assert sidecar.exists(), "sidecar JSON should exist"
    assert idx.header.point_count == 625
    assert idx.header.grid_shape[0] >= 1 and idx.header.grid_shape[1] >= 1


def test_load_round_trip(grid_las: pathlib.Path) -> None:
    idx = build_index(grid_las, target_per_cell=64)
    sidecar = idx.source_path.with_suffix(idx.source_path.suffix + ".lzti.json")
    loaded = load_index(sidecar)
    assert loaded.header.point_count == idx.header.point_count
    assert loaded.header.grid_shape == idx.header.grid_shape
    assert loaded.cells == idx.cells


def test_query_full_bbox_returns_all_points(grid_las: pathlib.Path) -> None:
    idx = build_index(grid_las, target_per_cell=64)
    res = query_index(idx, (-1.0, -1.0, 101.0, 101.0))
    assert res.indices.size == 625


def test_query_subbbox_returns_subset(grid_las: pathlib.Path) -> None:
    idx = build_index(grid_las, target_per_cell=64)
    # 10x10 cell of the grid: x in [0, 36], y in [0, 36] -> 9x9 grid points = 81
    res = query_index(idx, (0.0, 0.0, 36.0, 36.0))
    # Each axis has points at multiples of 100/24 = ~4.166; values <=36 -> 10 per axis
    expected = np.sum(np.linspace(0, 100, 25) <= 36) ** 2
    assert int(res.indices.size) == int(expected)


def test_query_outside_bbox_is_empty(grid_las: pathlib.Path) -> None:
    idx = build_index(grid_las, target_per_cell=64)
    res = query_index(idx, (200.0, 200.0, 300.0, 300.0))
    assert res.indices.size == 0


def test_indices_match_xy(grid_las: pathlib.Path) -> None:
    """Returned indices must be valid offsets into the indexed LAS, and the
    XY values at those offsets must match the returned xy array."""
    import laspy

    idx = build_index(grid_las, target_per_cell=64)
    res = query_index(idx, (10.0, 10.0, 50.0, 50.0))
    las = laspy.read(str(idx.source_path))
    np.testing.assert_allclose(np.asarray(las.x)[res.indices], res.xy[:, 0], atol=1e-6)
    np.testing.assert_allclose(np.asarray(las.y)[res.indices], res.xy[:, 1], atol=1e-6)
