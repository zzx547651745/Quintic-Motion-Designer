param(
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"
$RepoDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ArtifactDir = Join-Path $RepoDir ".artifacts"
$AppDir = Join-Path $ArtifactDir "windows\QuinticMotionDesigner"
$ReleaseDir = Join-Path $ArtifactDir "release"

if ($Version -notmatch "^v?\d+\.\d+\.\d+([-.][0-9A-Za-z.]+)?$") {
    throw "Version must use semantic versioning, for example v0.1.0."
}
if (-not (Test-Path -LiteralPath (Join-Path $AppDir "QuinticMotionDesigner.exe"))) {
    throw "Windows build not found. Run scripts\build_windows.ps1 first."
}

$NormalizedVersion = if ($Version.StartsWith("v")) { $Version } else { "v$Version" }
$ArchiveName = "QuinticMotionDesigner-$NormalizedVersion-Windows-x64.zip"
$ArchivePath = Join-Path $ReleaseDir $ArchiveName
$ChecksumPath = "$ArchivePath.sha256"

New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
Compress-Archive `
    -LiteralPath $AppDir `
    -DestinationPath $ArchivePath `
    -CompressionLevel Optimal `
    -Force

$Hash = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
"$Hash  $ArchiveName" | Set-Content -LiteralPath $ChecksumPath -Encoding ascii

Write-Host "Release archive: $ArchivePath"
Write-Host "SHA-256 file: $ChecksumPath"
