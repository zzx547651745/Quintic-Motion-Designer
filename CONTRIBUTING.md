# 贡献指南

感谢参与 Quintic Motion Designer。提交代码即表示你同意贡献内容按本项目的 MIT License 发布。

## 本地开发

```powershell
git clone <repository-url>
cd quintic-motion-profile
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,build]"
python -m unittest discover -s tests -v
```

## 代码质量

提交前执行：

```powershell
ruff check .
black --check .
python -m unittest discover -s tests -v
```

- Python 代码遵循 Black 格式，行宽 88。
- 公共函数应有类型标注和简洁 docstring。
- GUI 只管理交互状态；计算、序列化和导出逻辑应保持可独立测试。
- 用户可见的 Windows 客户端文字应使用中文。
- 新增数据格式或行为时必须补充确定性测试和相应文档。

## Git 规范

- 从 `main` 创建短生命周期分支：`feat/<name>`、`fix/<name>`、`docs/<name>`、`chore/<name>`。
- 提交信息采用 Conventional Commits，例如：
  - `feat: export all motion derivatives to csv`
  - `fix: restore the default viewport from toolbar`
  - `docs: explain the release process`
- 一个提交只解决一个逻辑问题，不提交 `dist/`、`.artifacts/`、缓存或本地项目数据。
- 不改写已公开的 `main` 和 Release 标签历史。

## Pull Request

PR 应说明动机、行为变化、验证证据和兼容性影响。界面变化请附截图；发布流程变化请同步更新 `docs/releasing.md` 或 ADR。

维护者使用 squash merge 时，PR 标题也必须符合 Conventional Commits。
