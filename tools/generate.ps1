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

# The project intentionally remains on its 6.12.1 database. CubeMX rewrites
# this flag to true after generation; in quiet mode that leaves an invisible
# migration question and stalls before code generation. Persist the user's
# "continue with 6.12.1" choice before every unattended run.
function Disable-CubeMxMigrationPrompt {
    param([Parameter(Mandatory=$true)][string]$Path)

    $text = [System.IO.File]::ReadAllText($Path)
    $settingPattern = '(?m)^ProjectManager\.AskForMigrate=(true|false)(?=\r?$)'
    if ($text -notmatch $settingPattern) {
        throw "CubeMX migration setting was not found in $Path"
    }
    $text = [regex]::Replace(
        $text,
        $settingPattern,
        'ProjectManager.AskForMigrate=false'
    )
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $text, $utf8NoBom)
}

Disable-CubeMxMigrationPrompt -Path $IocPath

$scriptPath = Join-Path $BuildDir "cubemx-generate.txt"
@(
    "config load `"$IocPath`"",
    "project generate",
    "exit"
) | Set-Content -LiteralPath $scriptPath -Encoding ASCII

$logPath = Join-Path $BuildDir "cubemx-generate.log"
$generationStarted = Get-Date

# STM32CubeMX quiet script mode. Exact behavior can vary by installed version;
# retain the generated script and log for diagnosis.
Invoke-LoggedProcess `
    -Executable $cubeMx `
    -Arguments @("-q", $scriptPath) `
    -LogPath $logPath `
    -WorkingDirectory (Split-Path -Parent $cubeMx) `
    -Quiet

# CubeMX 6.18 re-enables the prompt while saving a 6.12.1 project.
Disable-CubeMxMigrationPrompt -Path $IocPath

$logText = Get-Content -LiteralPath $logPath -Raw
if (($logText -notmatch '(?m)^OK\r?$') -or
    ($logText -notmatch '(?m)^Bye bye\r?$')) {
    throw "CubeMX exited without its successful completion markers. See $logPath"
}

$projectName = [System.IO.Path]::GetFileNameWithoutExtension($IocPath)
$expectedProject = Join-Path (Split-Path -Parent $IocPath) "MDK-ARM\$projectName.uvprojx"
if (-not (Test-Path -LiteralPath $expectedProject -PathType Leaf)) {
    throw "CubeMX exited without producing the expected MDK project: $expectedProject. See $logPath"
}
$projectInfo = Get-Item -LiteralPath $expectedProject
if ($projectInfo.LastWriteTime -lt $generationStarted.AddSeconds(-2)) {
    throw "CubeMX success markers were present but the MDK project was not refreshed: $expectedProject"
}

& (Join-Path $PSScriptRoot "sync-keil-project.ps1") `
    -ProjectPath $expectedProject

Write-Host "CubeMX generation completed. Project: $expectedProject"
Write-Host "Log: $logPath"
