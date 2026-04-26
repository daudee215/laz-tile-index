"""Command-line entry point: ``laz-tile-index build|query <input>``."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from .index import build_index, load_index, query_index


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="laz-tile-index",
        description="Build or query a portable spatial tile index for LAS/LAZ files.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="Build a sidecar index for a LAS/LAZ file.")
    b.add_argument("input", type=pathlib.Path, help="Input LAS/LAZ path.")
    b.add_argument(
        "--target-per-cell",
        type=int,
        default=5_000,
        help="Average points per grid cell (default: 5000).",
    )

    q = sub.add_parser("query", help="Query a sidecar index for points in a bbox.")
    q.add_argument("sidecar", type=pathlib.Path, help="Sidecar JSON file.")
    q.add_argument("minx", type=float)
    q.add_argument("miny", type=float)
    q.add_argument("maxx", type=float)
    q.add_argument("maxy", type=float)

    args = parser.parse_args(argv)
    if args.cmd == "build":
        idx = build_index(args.input, target_per_cell=args.target_per_cell)
        print(
            json.dumps(
                {
                    "indexed_las": str(idx.source_path),
                    "grid_shape": idx.header.grid_shape,
                    "point_count": idx.header.point_count,
                    "cells": len(idx.cells),
                }
            )
        )
        return 0
    if args.cmd == "query":
        idx = load_index(args.sidecar)
        res = query_index(idx, (args.minx, args.miny, args.maxx, args.maxy))
        print(json.dumps({"matched": int(res.indices.size)}))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
