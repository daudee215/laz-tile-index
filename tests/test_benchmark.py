"""Benchmark: build + query on a 100k-point dataset.

Skipped unless ``--benchmark-only`` or ``--benchmark`` flags are present;
pytest-benchmark records runtime and memory stats to ``.benchmarks/``.
"""

from __future__ import annotations

import pathlib

import pytest

from laz_tile_index import build_index, query_index


@pytest.mark.benchmark
def test_benchmark_build(big_las: pathlib.Path, benchmark: pytest.fixture) -> None:  # type: ignore[valid-type]
    benchmark(lambda: build_index(big_las, target_per_cell=2_000))


@pytest.mark.benchmark
def test_benchmark_query(big_las: pathlib.Path, benchmark: pytest.fixture) -> None:  # type: ignore[valid-type]
    idx = build_index(big_las, target_per_cell=2_000)
    benchmark(lambda: query_index(idx, (200.0, 200.0, 600.0, 600.0)))
