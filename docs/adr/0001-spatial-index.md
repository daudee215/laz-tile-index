# ADR 0001: JSON-sidecar uniform-grid spatial index

Status: Accepted
Date: 2026-04-26

## Context

The library needs to support out-of-core bbox queries on LAS/LAZ point clouds
without requiring a database, without re-encoding the source file, and with
no native (non-Python) dependencies.

## Decision

Build a uniform-grid spatial index whose cells are stored as a JSON sidecar
(`<file>.lzti.json`) alongside a *reordered* copy of the LAS where points
inside each cell occupy contiguous offsets. Queries open the LAS in seekable
mode, read only intersecting cells, and apply a precise bbox filter.

## Why

| Constraint | Decision satisfies it |
|---|---|
| No DB | sidecar is a flat JSON file |
| No binary deps | numpy + laspy (pure-Python wheels available) |
| Portable across languages | JSON is universal; cell ranges are integers |
| Cheap query | reads only intersecting cells |
| Cheap to build | one numpy.argsort over cell IDs |

## Rejected alternatives

### A. R-tree (rtree / libspatialindex)

A balanced R-tree gives much better worst-case behavior on non-uniform data
and supports arbitrary geometries, not just bboxes. We rejected it because
it requires the libspatialindex C library, which complicates wheels and
breaks the "no native deps" goal. R-tree files are also non-portable across
languages.

### B. KD-tree (scipy.spatial.cKDTree)

A KD-tree is the de-facto Python choice for nearest-neighbor queries on
point clouds. We rejected it for two reasons: (1) it is in-memory only — the
whole point cloud has to fit in RAM to build the tree, defeating the
out-of-core goal; (2) it does not have a portable on-disk format.

### C. LAStools `.lax`

LAStools' `lasindex` produces a binary `.lax` sidecar. We rejected it
because (1) the binary format is undocumented in detail and tied to the
LAStools licensing model, and (2) there is no maintained Python writer.

### D. COPC (Cloud-Optimized Point Cloud)

COPC is a modern hierarchical octree-in-LAZ format. We rejected it as the
*default* because it requires re-encoding the LAZ file. For users who
already have a `.las`/`.laz` they cannot re-encode (e.g. archived deliveries
with a fixed checksum), an additive sidecar is strictly more usable. A
future v0.2 milestone may emit COPC alongside the JSON sidecar.

## Consequences

- Build time is O(N log N) (one argsort) and memory is O(N).
- Query time is O(C·k) where C is the number of intersecting cells and k is
  the average cell size; for uniformly distributed points and small queries
  this is dramatically less than O(N).
- The sidecar is human-readable and inspectable. Users can copy it across
  filesystems without specialized tooling.
- Worst case for skewed distributions is poor; v0.2 introduces an adaptive
  quadtree variant guarded behind an opt-in flag.
