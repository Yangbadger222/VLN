from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def iter_points(csv_path: Path, sample_limit: int, drop_zero_points: bool, z_offset: float):
    count = 0
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                x = float(row["x"])
                y = float(row["y"])
                z = float(row["z"]) + z_offset
                intensity = float(row.get("reflectivity", 0.0))
            except Exception:
                continue
            if any(math.isnan(v) or math.isinf(v) for v in (x, y, z, intensity)):
                continue
            if drop_zero_points and x == 0.0 and y == 0.0 and z == z_offset:
                continue
            yield (x, y, z, intensity)
            count += 1
            if sample_limit > 0 and count >= sample_limit:
                return


def write_pcd(output_path: Path, points) -> int:
    point_list = list(points)
    with output_path.open("w", encoding="ascii") as f:
        f.write("# .PCD v0.7 - Point Cloud Data file format\n")
        f.write("VERSION 0.7\n")
        f.write("FIELDS x y z intensity\n")
        f.write("SIZE 4 4 4 4\n")
        f.write("TYPE F F F F\n")
        f.write("COUNT 1 1 1 1\n")
        f.write(f"WIDTH {len(point_list)}\n")
        f.write("HEIGHT 1\n")
        f.write("VIEWPOINT 0 0 0 1 0 0 0\n")
        f.write(f"POINTS {len(point_list)}\n")
        f.write("DATA ascii\n")
        for x, y, z, intensity in point_list:
            f.write(f"{x:.6f} {y:.6f} {z:.6f} {intensity:.6f}\n")
    return len(point_list)


def parse_args():
    parser = argparse.ArgumentParser(description="Convert Livox CSV point cloud logs to ASCII PCD.")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("output_path", type=Path)
    parser.add_argument("--sample-limit", type=int, default=300000)
    parser.add_argument("--keep-zero-points", action="store_true")
    parser.add_argument("--z-offset", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    count = write_pcd(
        args.output_path,
        iter_points(
            args.csv_path.expanduser(),
            args.sample_limit,
            not args.keep_zero_points,
            args.z_offset,
        ),
    )
    print(f"Wrote {count:,} points to {args.output_path}")


if __name__ == "__main__":
    main()
