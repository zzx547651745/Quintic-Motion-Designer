import json
import tempfile
import unittest
from pathlib import Path

from chart_renderer import (
    calculate_all_series,
    calculate_series,
    export_chart,
    export_chart_csv,
    safe_filename,
)
from motion_project import (
    ChartConfig,
    MotionProject,
    Waypoint,
    handdrawn_example_project,
)


class MotionProjectTests(unittest.TestCase):
    def test_project_round_trip_preserves_multiple_charts_and_metadata(self) -> None:
        project = handdrawn_example_project()
        project.charts[0].title = "自定义标题"
        project.charts[0].x_label = "主动轴角度"
        project.charts[0].y_label = "从动件位移"

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.qmp.json"
            project.save(path)
            loaded = MotionProject.load(path)

        self.assertEqual(len(loaded.charts), 4)
        self.assertEqual(loaded.charts[0].title, "自定义标题")
        self.assertEqual(loaded.charts[0].x_label, "主动轴角度")
        self.assertEqual(loaded.charts[0].y_label, "从动件位移")

    def test_curve_kind_selects_position_velocity_or_acceleration(self) -> None:
        chart = ChartConfig(points=[Waypoint(0, 0), Waypoint(100, 10)])
        expected_lengths = []
        for kind in ("position", "velocity", "acceleration"):
            chart.curve_kind = kind
            inputs, values = calculate_series(chart, sample_count=101)
            expected_lengths.append((len(inputs), len(values)))
        self.assertEqual(expected_lengths, [(101, 101), (101, 101), (101, 101)])

    def test_chart_export_creates_nonempty_png(self) -> None:
        chart = handdrawn_example_project().charts[0]
        with tempfile.TemporaryDirectory() as folder:
            path = export_chart(chart, Path(folder) / "chart.png", dpi=90)
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 1000)

    def test_csv_export_contains_all_curve_types_and_exact_waypoints(self) -> None:
        chart = handdrawn_example_project().charts[1]
        with tempfile.TemporaryDirectory() as folder:
            path = export_chart_csv(chart, Path(folder) / "data.csv", sample_count=101)
            lines = path.read_text(encoding="utf-8-sig").splitlines()

        self.assertEqual(lines[0], "横轴值,位移,速度,加速度")
        exported_inputs = {float(line.split(",", 1)[0]) for line in lines[1:]}
        self.assertTrue(set(chart.input_values).issubset(exported_inputs))
        self.assertGreater(len(lines), 101)

    def test_all_series_share_the_same_sampling_axis(self) -> None:
        chart = handdrawn_example_project().charts[0]
        inputs, position, velocity, acceleration = calculate_all_series(
            chart, sample_count=51
        )
        self.assertEqual(len(inputs), len(position))
        self.assertEqual(len(inputs), len(velocity))
        self.assertEqual(len(inputs), len(acceleration))

    def test_invalid_project_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text(
                json.dumps({"version": 999, "charts": []}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "版本"):
                MotionProject.load(path)

    def test_safe_filename_removes_windows_reserved_characters(self) -> None:
        self.assertEqual(safe_filename("图<1>:测试/曲线?*"), "图_1__测试_曲线__")


if __name__ == "__main__":
    unittest.main()
