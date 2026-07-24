param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$RepoDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ArtifactDir = Join-Path $RepoDir ".artifacts"
$DistDir = Join-Path $ArtifactDir "windows"
$WorkDir = Join-Path $ArtifactDir "build"
$AppDir = Join-Path $DistDir "QuinticMotionDesigner"
Set-Location -LiteralPath $RepoDir

if (-not $SkipInstall) {
    python -m pip install -e ".[build]"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install build dependencies (exit code $LASTEXITCODE)."
    }
}

python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --distpath $DistDir `
    --workpath $WorkDir `
    --name QuinticMotionDesigner `
    --exclude-module pandas `
    --exclude-module scipy `
    --exclude-module pyarrow `
    --exclude-module numba `
    --exclude-module llvmlite `
    --exclude-module pytest `
    --exclude-module IPython `
    --exclude-module jupyter `
    --exclude-module openpyxl `
    --exclude-module sqlalchemy `
    --exclude-module pydantic `
    --exclude-module rich `
    desktop_app.py
if ($LASTEXITCODE -ne 0) {
    throw "Windows client build failed (exit code $LASTEXITCODE)."
}

Copy-Item -LiteralPath (Join-Path $RepoDir "LICENSE") -Destination $AppDir -Force
Copy-Item -LiteralPath (Join-Path $RepoDir "README.md") -Destination $AppDir -Force
Copy-Item -LiteralPath (Join-Path $RepoDir "CHANGELOG.md") -Destination $AppDir -Force
Copy-Item `
    -LiteralPath (Join-Path $RepoDir "docs") `
    -Destination $AppDir `
    -Recurse `
    -Force

Write-Host "Build complete: $AppDir\QuinticMotionDesigner.exe"
