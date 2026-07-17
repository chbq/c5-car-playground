[CmdletBinding()]
param(
    [string]$ProjectPath,
    [string]$TargetName,
    [switch]$Rebuild
)

. (Join-Path $PSScriptRoot "common.ps1")

if ([string]::IsNullOrWhiteSpace($ProjectPath)) {
    $ProjectPath = $Env:C5_UVPROJX_PATH
}
if ([string]::IsNullOrWhiteSpace($TargetName)) {
    $TargetName = $Env:C5_KEIL_TARGET
}

$uv4 = Resolve-ToolPath `
    -Configured $Env:C5_UV4_EXE `
    -Candidates @(
        "C:\Keil_v5\UV4\UV4.exe",
        "$Env:ProgramFiles\Keil_v5\UV4\UV4.exe",
        "${Env:ProgramFiles(x86)}\Keil_v5\UV4\UV4.exe"
    ) `
    -CommandName "UV4.exe"

$uv4 = Require-File $uv4 "Keil UV4.exe"
$ProjectPath = Require-File $ProjectPath "Keil .uvprojx project"

& (Join-Path $PSScriptRoot "sync-keil-project.ps1") `
    -ProjectPath $ProjectPath

if ([string]::IsNullOrWhiteSpace($TargetName)) {
    throw "C5_KEIL_TARGET is not configured in tools/local.env.ps1."
}

$logPath = Join-Path $BuildDir "keil-build.log"
$action = if ($Rebuild) { "-r" } else { "-b" }

if (Test-Path -LiteralPath $logPath) {
    Remove-Item -LiteralPath $logPath -Force
}

$args = @(
    $action,
    "`"$ProjectPath`"",
    "-t$TargetName",
    "-o",
    "`"$logPath`""
)

$process = Start-Process `
    -FilePath $uv4 `
    -ArgumentList $args `
    -WorkingDirectory (Split-Path -Parent $ProjectPath) `
    -WindowStyle Hidden `
    -Wait `
    -PassThru
$exitCode = $process.ExitCode

if (-not (Test-Path -LiteralPath $logPath)) {
    throw "Keil returned success but did not create the expected build log."
}

$logText = Get-Content -LiteralPath $logPath -Raw
$summary = [regex]::Match(
    $logText,
    "(?im)(\d+)\s+Error\(s\),\s*(\d+)\s+Warning\(s\)"
)
if (-not $summary.Success) {
    throw "Keil build log has no final error/warning summary (exit code $exitCode). See $logPath"
}

$errorCount = [int]$summary.Groups[1].Value
$warningCount = [int]$summary.Groups[2].Value
if ($errorCount -gt 0 -or $exitCode -ge 2) {
    throw "Keil build failed: exit code $exitCode, $errorCount error(s), $warningCount warning(s). See $logPath"
}

if (-not [string]::IsNullOrWhiteSpace($Env:C5_FIRMWARE_IMAGE) -and
    -not (Test-Path -LiteralPath $Env:C5_FIRMWARE_IMAGE -PathType Leaf)) {
    throw "Keil reported success but did not create the configured firmware image: $Env:C5_FIRMWARE_IMAGE"
}

Write-Host "Keil build completed: $errorCount error(s), $warningCount warning(s)."
if (-not [string]::IsNullOrWhiteSpace($Env:C5_FIRMWARE_IMAGE)) {
    Write-Host "Firmware: $Env:C5_FIRMWARE_IMAGE"
}
Write-Host "Log: $logPath"
