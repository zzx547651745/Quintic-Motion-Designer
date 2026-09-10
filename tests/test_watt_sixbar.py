import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from watt_sixbar import (
    WattSixBarParameters,
    export_watt_sixbar_csv,
    solve_watt_sixbar,
)


class WattSixBarTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parameters = WattSixBarParameters()
        self.theta = np.linspace(0.0, 360.0, 721)
        self.result = solve_watt_sixbar(
            self.parameters, self.theta, omega=2.0, alpha=0.0
        )

    def test_default_geometry_closes_both_loops_for_full_turn(self) -> None:
        p = self.parameters
        r = self.result
        np.testing.assert_allclose(
            np.linalg.norm(r.positions["D"] - r.positions["C"], axis=1), p.cd
        )
        np.testing.assert_allclose(
            np.linalg.norm(r.positions["D"] - np.array((p.frame, 0.0)), axis=1),
            p.df,
        )
        np.testing.assert_allclose(
            np.linalg.norm(r.positions["G"] - r.positions["B"], axis=1), p.bg
        )
        np.testing.assert_allclose(
            np.linalg.norm(r.positions["G"] - r.positions["E"], axis=1), p.ge
        )
        self.assertTrue(p.grashof_satisfied)

    def test_analytic_g_velocity_and_acceleration_match_finite_differences(
        self,
    ) -> None:
        theta = np.linspace(0.0, 360.0, 7201)
        result = solve_watt_sixbar(self.parameters, theta, omega=2.0, alpha=0.0)
        dt = np.radians(theta[1] - theta[0]) / 2.0
        numerical_velocity = np.gradient(result.positions["G"], dt, axis=0)
        numerical_acceleration = np.gradient(result.velocities["G"], dt, axis=0)
        interior = slice(3, -3)
        np.testing.assert_allclose(
            result.velocities["G"][interior],
            numerical_velocity[interior],
            rtol=5e-4,
            atol=2e-3,
        )
        np.testing.assert_allclose(
            result.accelerations["G"][interior],
            numerical_acceleration[interior],
            rtol=1e-3,
            atol=3e-2,
        )

    def test_csv_contains_every_point_and_kinematic_quantity(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = export_watt_sixbar_csv(self.result, Path(folder) / "watt_sixbar.csv")
            with path.open(encoding="utf-8-sig", newline="") as file:
                rows = list(csv.reader(file))
        self.assertEqual(len(rows), len(self.theta) + 1)
        self.assertIn("G_位置X_mm", rows[0])
        self.assertIn("G_速度Y_mm_s", rows[0])
        self.assertIn("G_加速度X_mm_s2", rows[0])
        self.assertIn("第二闭环传动角_deg", rows[0])

    def test_invalid_assembly_is_reported(self) -> None:
        parameters = WattSixBarParameters(cd=10.0, df=10.0)
        with self.assertRaisesRegex(ValueError, "不能装配"):
            solve_watt_sixbar(parameters, [0.0, 1.0])


if __name__ == "__main__":
    unittest.main()
