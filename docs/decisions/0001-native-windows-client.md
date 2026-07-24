# ADR-001: 使用 Tkinter 与共享 Matplotlib 渲染服务

## Status

Accepted

## Date

2026-07-23

## Context

项目需要在 Windows 上提供无需浏览器的多图运动曲线编辑器，并保持五次轨迹计算、屏幕预览、图片导出和 CSV 导出结果一致。客户端还应能通过 PyInstaller 离线分发。

## Decision

使用 Python Tkinter 实现原生桌面交互，使用 Matplotlib TkAgg 嵌入预览。领域模型、数值引擎、绘图服务和 GUI 分层：GUI 编辑 `MotionProject`，预览与图片导出共同调用 `chart_renderer`，所有数据导出共同调用 `PiecewiseQuinticProfile`。

## Alternatives Considered

### Web/Electron

界面生态丰富，但运行时和打包体积更大，还会引入前后端通信或算法重写，不适合当前单机工程工具。

### Qt

组件能力更强，但增加较重的运行依赖和许可证评估成本。当前交互复杂度不需要 Qt。

### 直接从预览画布截图导出

实现简单，但输出分辨率和布局会受窗口尺寸影响，也无法可靠复用到批量导出。

## Consequences

- Windows 用户可直接运行打包目录中的 EXE。
- 数值和导出逻辑可在无 GUI 环境中测试。
- Tkinter 控件样式能力有限；复杂交互升级前应重新评估 Qt 或 Web 技术。
- Matplotlib 工具栏的用户可见文字需要由项目显式中文化。
