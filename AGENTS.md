# Agent repository guide

## Scope

These instructions apply to the entire repository.

## Architecture

- `quintic_profile.py`: numerical quintic trajectory engine; keep it GUI-independent.
- `motion_project.py`: serializable project and chart data model.
- `chart_renderer.py`: shared preview, image export, and CSV export service.
- `desktop_app.py`: Tkinter interaction layer only.
- `tests/`: deterministic unit and localization tests.

Preview and export must continue to share the same calculation and rendering paths. Every user-entered waypoint must be present in exported CSV data.

## Required checks

Run before handing off code changes:

```powershell
ruff check .
black --check .
python -m unittest discover -s tests -v
```

For release or packaging changes, also run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

Do not commit generated files under `.artifacts/`, `build*/`, or `dist*/`.
