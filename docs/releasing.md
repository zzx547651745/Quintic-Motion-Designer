# 发布流程

项目使用语义化版本和 GitHub Release 归档 Windows 客户端。

## 准备版本

1. 将 `pyproject.toml` 中的 `project.version` 更新为目标版本。
2. 将 `CHANGELOG.md` 的 `Unreleased` 内容移动到带日期的版本章节。
3. 执行代码质量、测试和本地打包：

```powershell
ruff check .
black --check .
python -m unittest discover -s tests -v
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\package_release.ps1 -Version v0.1.0
```

4. 从 `.artifacts/release/` 解压 ZIP 并启动 EXE，检查预览、项目保存、图片导出和 CSV 导出。

## 创建正式 Release

合并版本变更到 `main` 后创建并推送不可变标签：

```powershell
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

`.github/workflows/release.yml` 会验证版本、重新测试和构建，并归档：

- `QuinticMotionDesigner-v0.1.0-Windows-x64.zip`
- `QuinticMotionDesigner-v0.1.0-Windows-x64.zip.sha256`

GitHub 同时自动保留对应标签的源码归档。失败的工作流不得手工复用部分产物；修复后删除未发布标签并重新创建，若 Release 已公开则发布新的补丁版本。
