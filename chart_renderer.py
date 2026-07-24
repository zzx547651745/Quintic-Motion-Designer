"""Shared Matplotlib rendering used by both preview and file export."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import numpy as np
from matplotlib import rcParams
from matplotlib.figure import Figure

from motion_project import ChartConfig
from quintic_profile import PiecewiseQuinticProfile

CURVE_COLORS = {
    "position": "#2563eb",
    "velocity": "#059669",
    "acceleration": "#dc2626",
}

# Prefer fonts normally present on Chinese Windows installations. DejaVu Sans
# remains the final fallback for non-CJK text and packaged environments.
rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "Microsoft JhengHei",
    "SimHei",
    "Arial Unicode MS",
    "DejaVu Sans",
]
rcParams["axes.unicode_minus"] = False


def calculate_all_series(
    chart: ChartConfig, sample_count: int = 1601
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    chart.validate()
    # Always include every user-entered waypoint even when it does not fall on
    # the uniform sampling grid used between waypoints.
    uniform_inputs = np.linspace(
        chart.input_values[0], chart.input_values[-1], sample_count
    )
    inputs = np.unique(np.concatenate((uniform_inputs, chart.input_values)))
    state = PiecewiseQuinticProfile(chart.input_values, chart.output_values).evaluate(
        inputs
    )
    return inputs, state.position, state.velocity, state.acceleration


def calculate_series(
    chart: ChartConfig, sample_count: int = 1601
) -> tuple[np.ndarray, np.ndarray]:
    inputs, position, velocity, acceleration = calculate_all_series(chart, sample_count)
    state_values = {
        "position": position,
        "velocity": velocity,
        "acceleration": acceleration,
    }
    return inputs, state_values[chart.curve_kind]


def render_chart(chart: ChartConfig, figure: Figure | None = None) -> Figure:
    """Render a chart into a new or supplied figure."""
    inputs, values = calculate_series(chart)
    if figure is None:
        figure = Figure(figsize=(9, 5.6), dpi=100)
    figure.clear()
    axis = figure.add_subplot(111)

    if chart.show_original and chart.curve_kind == "position":
        axis.plot(
            chart.input_values,
            chart.output_values,
            color="#6b7280",
            linestyle="--",
            linewidth=1.5,
            marker="o",
            markersize=4,
            label="原始折线",
        )

    axis.plot(
        inputs,
        values,
        color=CURVE_COLORS[chart.curve_kind],
        linewidth=2.4,
        label="五次多项式",
    )
    for point in chart.points:
        axis.axvline(
            point.input_value,
            color="#9ca3af",
            linestyle=":",
            linewidth=0.8,
            alpha=0.8,
        )
    axis.axhline(0.0, color="#111827", linewidth=0.8)
    axis.set_title(chart.title, fontsize=14, pad=12)
    axis.set_xlabel(chart.x_label)
    axis.set_ylabel(chart.y_label)
    axis.format_coord = lambda x, y: f"横轴 = {x:.4g}，纵轴 = {y:.4g}"
    axis.grid(chart.show_grid, alpha=0.25)
    if chart.show_original and chart.curve_kind == "position":
        axis.legend(loc="best")
    figure.tight_layout()
    return figure


def export_chart(chart: ChartConfig, path: str | Path, dpi: int = 180) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    figure = render_chart(chart)
    figure.savefig(target, dpi=dpi, bbox_inches="tight")
    return target


def export_chart_csv(
    chart: ChartConfig, path: str | Path, sample_count: int = 1601
) -> Path:
    """Export input, position, velocity and acceleration as Excel-friendly CSV."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    inputs, position, velocity, acceleration = calculate_all_series(chart, sample_count)
    with target.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("横轴值", "位移", "速度", "加速度"))
        for row in zip(inputs, position, velocity, acceleration, strict=True):
            writer.writerow(f"{float(value):.12g}" for value in row)
    return target


def safe_filename(value: str, fallback: str = "motion_chart") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    return cleaned or fallback
