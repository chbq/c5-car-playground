[CmdletBinding()]
param(
    [switch]$SkipGenerate,
    [switch]$Flash,
    [switch]$IUnderstandThisWillFlashHardware
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "doctor.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "Environment audit failed."
}

& (Join-Path $PSScriptRoot "test-host.ps1")

if (-not $SkipGenerate) {
    & (Join-Path $PSScriptRoot "generate.ps1")
}

& (Join-Path $PSScriptRoot "build.ps1")

if ($Flash) {
    if (-not $IUnderstandThisWillFlashHardware) {
        throw "Use -IUnderstandThisWillFlashHardware together with -Flash."
    }
    & (Join-Path $PSScriptRoot "flash.ps1") `
        -IUnderstandThisWillFlashHardware
}

Write-Host "Verification pipeline completed."
