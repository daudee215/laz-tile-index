# laz-tile-index

Portable JSON-sidecar spatial tile index for LAS/LAZ point clouds.

## Why

Existing options leave a portable, file-based, language-agnostic spatial index
out of reach for plain Python users. PDAL's index is C++-only and tied to its
pipeline. LAStools `.lax` is undocumented and proprietary. COPC requires
re-encoding the LAZ. `laz-tile-index` is the missing piece: a small JSON
sidecar that any language can read, alongside a reordered `.las` whose points
sit contiguously per cell.

See [Quickstart](quickstart.md) for a 30-second start, [API](api.md) for the
public surface, and [ADR 0001](adr/0001-spatial-index.md) for the rationale.
