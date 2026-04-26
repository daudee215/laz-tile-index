"""laz-tile-index: portable JSON sidecar spatial tile index for LAS/LAZ point clouds.

Enables out-of-core bbox queries on multi-million-point LAS/LAZ files without a
database or LAStools dependency. The sidecar is a single JSON file that lives
alongside the .las/.laz and stores a uniform-grid spatial index of point ranges.
"""

from .index import (
    GridIndex,
    IndexHeader,
    SpatialQueryResult,
    build_index,
    load_index,
    query_index,
)

__all__ = [
    "GridIndex",
    "IndexHeader",
    "SpatialQueryResult",
    "build_index",
    "load_index",
    "query_index",
]

__version__ = "0.1.0"
