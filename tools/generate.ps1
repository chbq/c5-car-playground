[CmdletBinding()]
param(
    [string]$IocPath
)

. (Join-Path $PSScriptRoot "common.ps1")

if ([string]::IsNullOrWhiteSpace($IocPath)) {
    $IocPath = $Env:C5_IOC_PATH
}

$cubeMx = Resolve-ToolPath `
    -Configured $Env:C5_CUBEMX_EXE `
    -Candidates @(
        "D:\Program Files\STMicroelectronics\STM32Cube\STM32CubeMX\STM32CubeMX.exe",
        "$Env:ProgramFiles\STMicroelectronics\STM32Cube\STM32CubeMX\STM32CubeMX.exe",
        "${Env:ProgramFiles(x86)}\STMicroelectronics\STM32Cube\STM32CubeMX\STM32CubeMX.exe"
    ) `
    -CommandName "STM32CubeMX.exe"

$cubeMx = Require-File $cubeMx "STM32CubeMX"
$IocPath = Require-File $IocPath "CubeMX .ioc file"
$IocPath = (Resolve-Path -LiteralPath $IocPath).Path

$scriptPath = Join-Path $BuildDir "cubemx-generate.txt"
@(
    "config load `"$IocPath`"",
    "project generate",
    "exit"
) | Set-Content -LiteralPath $scriptPath -Encoding ASCII

$logPath = Join-Path $BuildDir "cubemx-generate.log"

# STM32CubeMX quiet script mode. Exact behavior can vary by installed version;
# retain the generated script and log for diagnosis.
Invoke-LoggedProcess `
    -Executable $cubeMx `
    -Arguments @("-q", $scriptPath) `
    -LogPath $logPath `
    -WorkingDirectory (Split-Path -Parent $cubeMx)

$projectName = [System.IO.Path]::GetFileNameWithoutExtension($IocPath)
$expectedProject = Join-Path (Split-Path -Parent $IocPath) "MDK-ARM\$projectName.uvprojx"
if (-not (Test-Path -LiteralPath $expectedProject -PathType Leaf)) {
    throw "CubeMX exited without producing the expected MDK project: $expectedProject. See $logPath"
}

Write-Host "CubeMX generation completed. Project: $expectedProject"
Write-Host "Log: $logPath"
