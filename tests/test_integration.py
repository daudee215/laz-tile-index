"""End-to-end integration test on a 100k-point synthetic dataset.

Verifies query correctness against an in-memory ground-truth bbox filter
on the same data.
"""

from __future__ import annotations

import pathlib

import laspy
import numpy as np

from laz_tile_index import build_index, query_index


def test_100k_bbox_matches_ground_truth(big_las: pathlib.Path) -> None:
    idx = build_index(big_las, target_per_cell=2_000)
    bbox = (200.0, 200.0, 600.0, 600.0)
    res = query_index(idx, bbox)
    las = laspy.read(str(idx.source_path))
    x = np.asarray(las.x)
    y = np.asarray(las.y)
    truth = np.sum((x >= bbox[0]) & (x <= bbox[2]) & (y >= bbox[1]) & (y <= bbox[3]))
    assert int(res.indices.size) == int(truth)


def test_disjoint_queries_partition_points(big_las: pathlib.Path) -> None:
    idx = build_index(big_las, target_per_cell=2_000)
    bbox_a = (0.0, 0.0, 500.0, 1000.0)
    bbox_b = (500.000001, 0.0, 1000.0, 1000.0)
    res_a = query_index(idx, bbox_a)
    res_b = query_index(idx, bbox_b)
    assert int(res_a.indices.size) + int(res_b.indices.size) == idx.header.point_count
