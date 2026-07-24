"""Project data model for the Windows motion-profile designer."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from quintic_profile import PiecewiseQuinticProfile

CurveKind = Literal["position", "velocity", "acceleration"]
PROJECT_VERSION = 1


@dataclass
class Waypoint:
    input_value: float
    output_value: float


@dataclass
class ChartConfig:
    name: str = "新图"
    title: str = "五次多项式运动曲线"
    x_label: str = "输入角度 (°)"
    y_label: str = "位移 (°)"
    curve_kind: CurveKind = "position"
    show_original: bool = True
    show_grid: bool = True
    points: list[Waypoint] = field(
        default_factory=lambda: [Waypoint(0.0, 0.0), Waypoint(360.0, 45.0)]
    )
    chart_id: str = field(default_factory=lambda: uuid4().hex)

    def validate(self) -> None:
        if self.curve_kind not in {"position", "velocity", "acceleration"}:
            raise ValueError(f"不支持的曲线类型：{self.curve_kind}")
        if len(self.points) < 2:
            raise ValueError("每张图至少需要两个拐点")
        # Reuse the numerical engine as the single source of point validation.
        PiecewiseQuinticProfile(self.input_values, self.output_values)

    @property
    def input_values(self) -> list[float]:
        return [point.input_value for point in self.points]

    @property
    def output_values(self) -> list[float]:
        return [point.output_value for point in self.points]

    def sort_points(self) -> None:
        self.points.sort(key=lambda point: point.input_value)

    def duplicate(self) -> ChartConfig:
        result = deepcopy(self)
        result.chart_id = uuid4().hex
        result.name = f"{self.name} - 副本"
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChartConfig:
        points = [Waypoint(**point) for point in data.get("points", [])]
        chart = cls(
            name=str(data.get("name", "新图")),
            title=str(data.get("title", "五次多项式运动曲线")),
            x_label=str(data.get("x_label", "输入角度 (°)")),
            y_label=str(data.get("y_label", "位移 (°)")),
            curve_kind=data.get("curve_kind", "position"),
            show_original=bool(data.get("show_original", True)),
            show_grid=bool(data.get("show_grid", True)),
            points=points,
            chart_id=str(data.get("chart_id") or uuid4().hex),
        )
        chart.validate()
        return chart


@dataclass
class MotionProject:
    name: str = "未命名项目"
    charts: list[ChartConfig] = field(default_factory=lambda: [ChartConfig()])

    def validate(self) -> None:
        if not self.charts:
            raise ValueError("项目至少需要一张图")
        for chart in self.charts:
            chart.validate()

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "version": PROJECT_VERSION,
            "name": self.name,
            "charts": [asdict(chart) for chart in self.charts],
        }

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> MotionProject:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("version") != PROJECT_VERSION:
            raise ValueError(f"不支持的项目文件版本：{data.get('version')}")
        project = cls(
            name=str(data.get("name", "未命名项目")),
            charts=[ChartConfig.from_dict(chart) for chart in data.get("charts", [])],
        )
        project.validate()
        return project


def handdrawn_example_project() -> MotionProject:
    """Return the four profiles transcribed from the supplied sketch."""
    values = (
        ("升程并停歇", "样例 1：升程与停歇", [0, 150, 360], [0, 45, 45]),
        (
            "升程停歇回程",
            "样例 2：升程、停歇与回程",
            [0, 150, 260, 360],
            [0, 15, 15, 0],
        ),
        (
            "小幅升程回程",
            "样例 3：小幅升程、停歇与回程",
            [0, 150, 260, 360],
            [0, 7, 7, 0],
        ),
        ("停歇升程回程", "样例 4：停歇、升程与回程", [0, 150, 260, 360], [0, 0, 40, 0]),
    )
    charts = []
    for name, title, inputs, outputs in values:
        charts.append(
            ChartConfig(
                name=name,
                title=title,
                points=[
                    Waypoint(float(x), float(y))
                    for x, y in zip(inputs, outputs, strict=True)
                ],
            )
        )
    return MotionProject(name="手绘运动规律样例", charts=charts)
