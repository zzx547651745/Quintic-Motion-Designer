"""Piecewise minimum-jerk (quintic) motion profiles."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray


@dataclass(frozen=True)
class MotionState:
    """Position and its first two derivatives with respect to the input axis."""

    position: NDArray[np.float64]
    velocity: NDArray[np.float64]
    acceleration: NDArray[np.float64]


class PiecewiseQuinticProfile:
    """Join waypoints with quintics whose endpoint velocity/acceleration are zero.

    The input axis can be time, cam angle, or any other monotonically increasing
    coordinate. Derivative units are therefore ``output/input`` and
    ``output/input^2``.
    """

    def __init__(self, input_points: ArrayLike, output_points: ArrayLike) -> None:
        self.input_points = np.asarray(input_points, dtype=float)
        self.output_points = np.asarray(output_points, dtype=float)

        if self.input_points.ndim != 1 or self.output_points.ndim != 1:
            raise ValueError("input_points and output_points must be one-dimensional")
        if len(self.input_points) != len(self.output_points):
            raise ValueError("input_points and output_points must have equal length")
        if len(self.input_points) < 2:
            raise ValueError("at least two waypoints are required")
        if not np.all(np.isfinite(self.input_points)) or not np.all(
            np.isfinite(self.output_points)
        ):
            raise ValueError("waypoints must contain only finite values")
        if not np.all(np.diff(self.input_points) > 0.0):
            raise ValueError("input_points must be strictly increasing")

    def evaluate(self, inputs: ArrayLike) -> MotionState:
        """Evaluate position, velocity, and acceleration at one or more inputs."""
        x = np.asarray(inputs, dtype=float)
        if np.any(~np.isfinite(x)):
            raise ValueError("inputs must contain only finite values")
        if np.any(x < self.input_points[0]) or np.any(x > self.input_points[-1]):
            raise ValueError(
                f"inputs must stay in [{self.input_points[0]}, {self.input_points[-1]}]"
            )

        # A waypoint belongs to the segment on its right. Both neighbouring
        # segments have the same state there, so this only selects coefficients.
        segment = np.searchsorted(self.input_points, x, side="right") - 1
        segment = np.clip(segment, 0, len(self.input_points) - 2)

        x0 = self.input_points[segment]
        x1 = self.input_points[segment + 1]
        y0 = self.output_points[segment]
        y1 = self.output_points[segment + 1]
        width = x1 - x0
        change = y1 - y0
        u = (x - x0) / width

        # Normalized minimum-jerk polynomial and its first two derivatives.
        blend = 10.0 * u**3 - 15.0 * u**4 + 6.0 * u**5
        blend_d1 = 30.0 * u**2 - 60.0 * u**3 + 30.0 * u**4
        blend_d2 = 60.0 * u - 180.0 * u**2 + 120.0 * u**3

        return MotionState(
            position=y0 + change * blend,
            velocity=(change / width) * blend_d1,
            acceleration=(change / width**2) * blend_d2,
        )
