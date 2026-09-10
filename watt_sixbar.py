"""Kinematics for a one-degree-of-freedom Watt six-bar mechanism."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import ArrayLike, NDArray

Vector = NDArray[np.float64]


@dataclass(frozen=True)
class WattSixBarParameters:
    """Geometry defined in the local frames of the two ternary links."""

    frame: float = 100.0  # AF = L0
    ac: float = 30.0  # AC = a
    ab: float = 16.0  # AB = b
    beta_deg: float = 112.0
    cd: float = 90.0  # L2
    bg: float = 127.0  # L3
    df: float = 80.0  # L4
    ge: float = 127.0  # L5
    fe: float = 95.0  # e
    delta_deg: float = 194.0
    branch_d: int = 1
    branch_g: int = 1

    def validate(self) -> None:
        lengths = (
            self.frame,
            self.ac,
            self.ab,
            self.cd,
            self.bg,
            self.df,
            self.ge,
            self.fe,
        )
        if not all(np.isfinite(length) and length > 0.0 for length in lengths):
            raise ValueError("所有杆长必须是大于 0 的有限数值")
        if not np.isfinite(self.beta_deg) or not np.isfinite(self.delta_deg):
            raise ValueError("β 和 δ 必须是有限角度")
        if self.branch_d not in {-1, 1} or self.branch_g not in {-1, 1}:
            raise ValueError("装配分支只能取 +1 或 -1")

    @property
    def grashof_satisfied(self) -> bool:
        longest = max(self.frame, self.cd, self.df)
        return self.ac <= min(self.frame, self.cd, self.df) and (
            self.ac + longest <= self.frame + self.cd + self.df - longest
        )


@dataclass(frozen=True)
class WattSixBarResult:
    theta_deg: Vector
    psi_deg: Vector
    psi_velocity_deg_s: Vector
    psi_acceleration_deg_s2: Vector
    transmission_1_deg: Vector
    transmission_2_deg: Vector
    positions: dict[str, Vector]
    velocities: dict[str, Vector]
    accelerations: dict[str, Vector]

    def point_series(self, point: str, axis: str) -> tuple[Vector, Vector, Vector]:
        if point not in {"B", "C", "D", "E", "G"} or axis not in {"x", "y"}:
            raise ValueError("点只能为 B/C/D/E/G，方向只能为 x/y")
        index = 0 if axis == "x" else 1
        return (
            self.positions[point][:, index],
            self.velocities[point][:, index],
            self.accelerations[point][:, index],
        )


def _perpendicular(vector: Vector) -> Vector:
    return np.array((-vector[1], vector[0]), dtype=float)


def _circle_intersection(
    center_1: Vector,
    radius_1: float,
    center_2: Vector,
    radius_2: float,
    branch: int,
    label: str,
) -> Vector:
    offset = center_2 - center_1
    distance = float(np.linalg.norm(offset))
    tolerance = 1e-10 * max(radius_1, radius_2, distance, 1.0)
    if distance <= tolerance:
        raise ValueError(f"{label} 两圆圆心重合，位置不能唯一确定")
    if (
        distance > radius_1 + radius_2 + tolerance
        or distance < abs(radius_1 - radius_2) - tolerance
    ):
        raise ValueError(f"{label} 两圆无交点，当前输入角下机构不能装配")
    direction = offset / distance
    along = (radius_1**2 - radius_2**2 + distance**2) / (2.0 * distance)
    height_squared = radius_1**2 - along**2
    if height_squared < -tolerance:
        raise ValueError(f"{label} 圆交点计算失败")
    height = np.sqrt(max(0.0, height_squared))
    return center_1 + along * direction + branch * height * _perpendicular(direction)


def _acute_angle_deg(cosine: float) -> float:
    angle = np.arccos(np.clip(cosine, -1.0, 1.0))
    return float(np.degrees(min(angle, np.pi - angle)))


def solve_watt_sixbar(
    parameters: WattSixBarParameters,
    theta_deg: ArrayLike,
    omega: float = 1.0,
    alpha: float = 0.0,
) -> WattSixBarResult:
    """Solve position, velocity and acceleration on a fixed assembly branch."""

    parameters.validate()
    theta_values = np.asarray(theta_deg, dtype=float)
    if theta_values.ndim != 1 or theta_values.size < 2:
        raise ValueError("输入角序列至少需要两个采样点")
    if not np.all(np.isfinite(theta_values)):
        raise ValueError("输入角必须是有限数值")
    if not np.isfinite(omega) or not np.isfinite(alpha):
        raise ValueError("输入角速度和角加速度必须是有限数值")

    point_names = ("B", "C", "D", "E", "G")
    positions = {name: np.empty((theta_values.size, 2)) for name in point_names}
    velocities = {name: np.empty((theta_values.size, 2)) for name in point_names}
    accelerations = {name: np.empty((theta_values.size, 2)) for name in point_names}
    psi = np.empty(theta_values.size)
    psi_velocity = np.empty(theta_values.size)
    psi_acceleration = np.empty(theta_values.size)
    transmission_1 = np.empty(theta_values.size)
    transmission_2 = np.empty(theta_values.size)

    p = parameters
    fixed_f = np.array((p.frame, 0.0))
    beta = np.radians(p.beta_deg)
    delta = np.radians(p.delta_deg)
    b_local = p.ab * np.array((np.cos(beta), np.sin(beta)))
    c_local = np.array((p.ac, 0.0))
    e_local = p.fe * np.array((np.cos(delta), np.sin(delta)))

    for index, angle_deg in enumerate(theta_values):
        theta = np.radians(angle_deg)
        rotation = np.array(
            ((np.cos(theta), -np.sin(theta)), (np.sin(theta), np.cos(theta)))
        )
        point_b = rotation @ b_local
        point_c = rotation @ c_local
        point_d = _circle_intersection(
            point_c, p.cd, fixed_f, p.df, p.branch_d, "C-D-F"
        )
        psi_value = np.arctan2(point_d[1], point_d[0] - p.frame)
        psi_rotation = np.array(
            (
                (np.cos(psi_value), -np.sin(psi_value)),
                (np.sin(psi_value), np.cos(psi_value)),
            )
        )
        point_e = fixed_f + psi_rotation @ e_local
        point_g = _circle_intersection(
            point_b, p.bg, point_e, p.ge, p.branch_g, "B-G-E"
        )

        r_df = point_d - fixed_f
        r_ef = point_e - fixed_f
        u2 = point_d - point_c
        u3 = point_g - point_b
        u5 = point_g - point_e
        velocity_b = omega * _perpendicular(point_b)
        velocity_c = omega * _perpendicular(point_c)
        jacobian = np.array(
            (
                (u2 @ _perpendicular(r_df), 0.0, 0.0),
                (0.0, u3[0], u3[1]),
                (-u5 @ _perpendicular(r_ef), u5[0], u5[1]),
            )
        )
        if np.linalg.cond(jacobian) > 1e12:
            raise ValueError(f"输入角 {angle_deg:g}° 附近机构处于奇异位置")
        speed_rhs = np.array((u2 @ velocity_c, u3 @ velocity_b, 0.0))
        psi_dot, velocity_g_x, velocity_g_y = np.linalg.solve(jacobian, speed_rhs)
        velocity_g = np.array((velocity_g_x, velocity_g_y))
        velocity_d = psi_dot * _perpendicular(r_df)
        velocity_e = psi_dot * _perpendicular(r_ef)

        acceleration_b = alpha * _perpendicular(point_b) - omega**2 * point_b
        acceleration_c = alpha * _perpendicular(point_c) - omega**2 * point_c
        acceleration_rhs = np.array(
            (
                u2 @ acceleration_c
                + psi_dot**2 * (u2 @ r_df)
                - np.dot(velocity_d - velocity_c, velocity_d - velocity_c),
                u3 @ acceleration_b
                - np.dot(velocity_g - velocity_b, velocity_g - velocity_b),
                -(psi_dot**2) * (u5 @ r_ef)
                - np.dot(velocity_g - velocity_e, velocity_g - velocity_e),
            )
        )
        psi_ddot, acceleration_g_x, acceleration_g_y = np.linalg.solve(
            jacobian, acceleration_rhs
        )
        acceleration_g = np.array((acceleration_g_x, acceleration_g_y))
        acceleration_d = psi_ddot * _perpendicular(r_df) - psi_dot**2 * r_df
        acceleration_e = psi_ddot * _perpendicular(r_ef) - psi_dot**2 * r_ef

        rho_cf_squared = float(np.dot(fixed_f - point_c, fixed_f - point_c))
        rho_be_squared = float(np.dot(point_e - point_b, point_e - point_b))
        transmission_1[index] = _acute_angle_deg(
            (p.cd**2 + p.df**2 - rho_cf_squared) / (2.0 * p.cd * p.df)
        )
        transmission_2[index] = _acute_angle_deg(
            (p.bg**2 + p.ge**2 - rho_be_squared) / (2.0 * p.bg * p.ge)
        )
        psi[index] = psi_value
        psi_velocity[index] = psi_dot
        psi_acceleration[index] = psi_ddot
        for name, position, velocity, acceleration in (
            ("B", point_b, velocity_b, acceleration_b),
            ("C", point_c, velocity_c, acceleration_c),
            ("D", point_d, velocity_d, acceleration_d),
            ("E", point_e, velocity_e, acceleration_e),
            ("G", point_g, velocity_g, acceleration_g),
        ):
            positions[name][index] = position
            velocities[name][index] = velocity
            accelerations[name][index] = acceleration

    return WattSixBarResult(
        theta_deg=theta_values,
        psi_deg=np.degrees(np.unwrap(psi)),
        psi_velocity_deg_s=np.degrees(psi_velocity),
        psi_acceleration_deg_s2=np.degrees(psi_acceleration),
        transmission_1_deg=transmission_1,
        transmission_2_deg=transmission_2,
        positions=positions,
        velocities=velocities,
        accelerations=accelerations,
    )


def export_watt_sixbar_csv(result: WattSixBarResult, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    headers = ["输入角度_deg"]
    for point in ("B", "C", "D", "E", "G"):
        for quantity, unit in (("位置", "mm"), ("速度", "mm_s"), ("加速度", "mm_s2")):
            headers.extend(
                (f"{point}_{quantity}X_{unit}", f"{point}_{quantity}Y_{unit}")
            )
    headers.extend(
        (
            "摇杆角_deg",
            "摇杆角速度_deg_s",
            "摇杆角加速度_deg_s2",
            "第一闭环传动角_deg",
            "第二闭环传动角_deg",
        )
    )
    with target.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        for index, theta in enumerate(result.theta_deg):
            row: list[float] = [float(theta)]
            for point in ("B", "C", "D", "E", "G"):
                for values in (
                    result.positions[point],
                    result.velocities[point],
                    result.accelerations[point],
                ):
                    row.extend(float(value) for value in values[index])
            row.extend(
                (
                    float(result.psi_deg[index]),
                    float(result.psi_velocity_deg_s[index]),
                    float(result.psi_acceleration_deg_s2[index]),
                    float(result.transmission_1_deg[index]),
                    float(result.transmission_2_deg[index]),
                )
            )
            writer.writerow(f"{value:.12g}" for value in row)
    return target
