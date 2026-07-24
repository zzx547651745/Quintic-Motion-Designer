import unittest

import numpy as np

from quintic_profile import PiecewiseQuinticProfile


class PiecewiseQuinticProfileTests(unittest.TestCase):
    def test_waypoints_have_exact_position_and_zero_derivatives(self) -> None:
        inputs = np.array([0.0, 150.0, 260.0, 360.0])
        outputs = np.array([0.0, 15.0, 15.0, 0.0])

        state = PiecewiseQuinticProfile(inputs, outputs).evaluate(inputs)

        np.testing.assert_allclose(state.position, outputs, atol=1e-12)
        np.testing.assert_allclose(state.velocity, 0.0, atol=1e-12)
        np.testing.assert_allclose(state.acceleration, 0.0, atol=1e-12)

    def test_both_sides_of_internal_waypoint_are_smooth(self) -> None:
        profile = PiecewiseQuinticProfile([0, 150, 260], [0, 15, 15])
        epsilon = 1e-4

        left = profile.evaluate(150.0 - epsilon)
        right = profile.evaluate(150.0 + epsilon)

        self.assertAlmostEqual(float(left.position), float(right.position), places=8)
        self.assertAlmostEqual(float(left.velocity), float(right.velocity), places=8)
        self.assertAlmostEqual(
            float(left.acceleration), float(right.acceleration), places=6
        )

    def test_rising_segment_is_monotonic_and_dwell_is_constant(self) -> None:
        profile = PiecewiseQuinticProfile([0, 150, 360], [0, 45, 45])

        rising = profile.evaluate(np.linspace(0, 150, 501))
        dwell = profile.evaluate(np.linspace(150, 360, 501))

        self.assertTrue(np.all(np.diff(rising.position) >= 0.0))
        np.testing.assert_allclose(dwell.position, 45.0, atol=1e-12)
        np.testing.assert_allclose(dwell.velocity, 0.0, atol=1e-12)
        np.testing.assert_allclose(dwell.acceleration, 0.0, atol=1e-12)

    def test_rejects_non_increasing_input_points(self) -> None:
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            PiecewiseQuinticProfile([0, 150, 150], [0, 10, 20])


if __name__ == "__main__":
    unittest.main()
