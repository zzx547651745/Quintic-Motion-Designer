"""Project data model for the Windows motion-profile designer."""

from __future__ import annotations

import json
import math
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from quintic_profile import PiecewiseQuinticProfile
from watt_sixbar import WattSixBarParameters

CurveKind = Literal["position", "velocity", "acceleration"]
AlgorithmKind = Literal["quintic", "watt_sixbar"]
PROJECT_VERSION = 2


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
    algorithm: AlgorithmKind = "quintic"
    show_original: bool = True
    show_grid: bool = True
    points: list[Waypoint] = field(
        default_factory=lambda: [Waypoint(0.0, 0.0), Waypoint(360.0, 45.0)]
    )
    watt_parameters: WattSixBarParameters = field(default_factory=WattSixBarParameters)
    watt_output: str = "G_x"
    watt_start_deg: float = 0.0
    watt_end_deg: float = 360.0
    watt_samples: int = 361
    watt_omega: float = 1.0
    watt_alpha: float = 0.0
    chart_id: str = field(default_factory=lambda: uuid4().hex)

    def validate(self) -> None:
        if self.algorithm not in {"quintic", "watt_sixbar"}:
            raise ValueError(f"不支持的算法：{self.algorithm}")
        if self.curve_kind not in {"position", "velocity", "acceleration"}:
            raise ValueError(f"不支持的曲线类型：{self.curve_kind}")
        if self.algorithm == "quintic":
            if len(self.points) < 2:
                raise ValueError("每张五次多项式图至少需要两个拐点")
            PiecewiseQuinticProfile(self.input_values, self.output_values)
            return
        self.watt_parameters.validate()
        if self.watt_output not in {
            "B_x",
            "B_y",
            "C_x",
            "C_y",
            "D_x",
            "D_y",
            "E_x",
            "E_y",
            "G_x",
            "G_y",
            "psi",
        }:
            raise ValueError(f"不支持的 Watt 输出：{self.watt_output}")
        if self.watt_end_deg <= self.watt_start_deg:
            raise ValueError("Watt 终止角必须大于起始角")
        if not 2 <= self.watt_samples <= 10001:
            raise ValueError("Watt 采样点数必须在 2～10001 之间")
        if not all(
            math.isfinite(value)
            for value in (
                self.watt_start_deg,
                self.watt_end_deg,
                self.watt_omega,
                self.watt_alpha,
            )
        ):
            raise ValueError("Watt 输入角和角速度参数必须是有限数值")

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
        watt_data = data.get("watt_parameters", {})
        chart = cls(
            name=str(data.get("name", "新图")),
            title=str(data.get("title", "五次多项式运动曲线")),
            x_label=str(data.get("x_label", "输入角度 (°)")),
            y_label=str(data.get("y_label", "位移 (°)")),
            curve_kind=data.get("curve_kind", "position"),
            algorithm=data.get("algorithm", "quintic"),
            show_original=bool(data.get("show_original", True)),
            show_grid=bool(data.get("show_grid", True)),
            points=points,
            watt_parameters=WattSixBarParameters(**watt_data),
            watt_output=str(data.get("watt_output", "G_x")),
            watt_start_deg=float(data.get("watt_start_deg", 0.0)),
            watt_end_deg=float(data.get("watt_end_deg", 360.0)),
            watt_samples=int(data.get("watt_samples", 361)),
            watt_omega=float(data.get("watt_omega", 1.0)),
            watt_alpha=float(data.get("watt_alpha", 0.0)),
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
        if data.get("version") not in {1, PROJECT_VERSION}:
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
