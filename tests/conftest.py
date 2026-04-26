"""Synthetic LAS fixtures shared across tests."""

from __future__ import annotations

import pathlib
from typing import cast

import laspy
import numpy as np
import pytest


def _write_las(path: pathlib.Path, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> None:
    """Write a tiny LAS file with the given XYZ arrays."""
    header = laspy.LasHeader(point_format=0, version="1.2")
    # Pick a scale so that integer encoding is loss-free for our toy data.
    header.scales = np.array([0.001, 0.001, 0.001])
    # Offsets centered on the data so int representation fits.
    header.offsets = np.array([float(x.min()), float(y.min()), float(z.min())])
    las = laspy.LasData(header)
    las.x = x
    las.y = y
    las.z = z
    las.write(str(path))


@pytest.fixture
def grid_las(tmp_path: pathlib.Path) -> pathlib.Path:
    """A 25x25 = 625-point regular grid in [0,100]x[0,100], z=0."""
    xs, ys = np.meshgrid(np.linspace(0, 100, 25), np.linspace(0, 100, 25))
    x = cast(np.ndarray, xs.ravel())
    y = cast(np.ndarray, ys.ravel())
    z = np.zeros_like(x)
    p = tmp_path / "grid.las"
    _write_las(p, x, y, z)
    return p


@pytest.fixture
def big_las(tmp_path: pathlib.Path) -> pathlib.Path:
    """100k-point synthetic dataset for the integration + benchmark tests."""
    rng = np.random.default_rng(42)
    n = 100_000
    x = rng.uniform(0.0, 1000.0, size=n)
    y = rng.uniform(0.0, 1000.0, size=n)
    z = rng.uniform(0.0, 50.0, size=n)
    p = tmp_path / "big.las"
    _write_las(p, x, y, z)
    return p
