# ADR-002: 使用语义化标签驱动 Windows Release 归档

## Status

Accepted

## Date

2026-07-23

## Context

开源仓库需要可重复、可追溯地生成 Windows 客户端。手工上传 EXE 容易遗漏依赖目录、混入本机旧文件，且无法证明二进制对应哪个源码版本。

## Decision

正式版本使用 `vMAJOR.MINOR.PATCH` 标签。GitHub Actions 在 Windows runner 上验证标签与 `pyproject.toml` 版本一致，执行测试和 PyInstaller 构建，生成包含完整运行目录的 ZIP 与 SHA-256 文件，并作为 GitHub Release assets 长期归档。

## Alternatives Considered

### 在 Git 中提交 EXE 和 ZIP

会快速膨胀仓库历史，而且二进制与源码关联依赖人工保证。

### 仅保留 Actions 临时 Artifact

适合 CI 调试，但默认有保留期限，不适合作为正式版本归档。

### 由维护者本机手工打包

操作直观，但环境不可重复，旧文件占用或全局 Python 依赖会污染结果。

## Consequences

- Git 历史只保存源码和发布脚本，Release 保存可下载二进制。
- 发布前必须同步更新 `pyproject.toml` 和 `CHANGELOG.md`。
- 删除或移动公开标签会破坏版本可追溯性，因此禁止改写已发布标签。
