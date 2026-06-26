from pathlib import Path

from navida_vehicle.csv_to_pcd import iter_points, write_pcd


def test_iter_points_filters_invalid_rows_and_applies_limit(tmp_path: Path):
    csv_path = tmp_path / "points.csv"
    csv_path.write_text(
        "\n".join(
            [
                "x,y,z,reflectivity",
                "0,0,0,1",
                "1,2,3,4",
                "bad,2,3,4",
                "5,6,7,8",
            ]
        ),
        encoding="utf-8",
    )

    points = list(
        iter_points(
            csv_path,
            sample_limit=1,
            drop_zero_points=True,
            z_offset=0.5,
        )
    )

    assert points == [(1.0, 2.0, 3.5, 4.0)]


def test_write_pcd_emits_ascii_point_cloud(tmp_path: Path):
    output_path = tmp_path / "map.pcd"

    count = write_pcd(output_path, [(1.0, 2.0, 3.0, 4.0)])

    assert count == 1
    text = output_path.read_text(encoding="ascii")
    assert "FIELDS x y z intensity" in text
    assert "POINTS 1" in text
    assert "1.000000 2.000000 3.000000 4.000000" in text
