Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$script:BuildDir = Join-Path $script:RepoRoot "build"
New-Item -ItemType Directory -Force -Path $script:BuildDir | Out-Null

$localEnv = Join-Path $PSScriptRoot "local.env.ps1"
if (Test-Path $localEnv) {
    . $localEnv
}

function Get-FirstExistingPath {
    param([string[]]$Candidates)

    foreach ($candidate in $Candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        $expanded = [Environment]::ExpandEnvironmentVariables($candidate)
        if (Test-Path -LiteralPath $expanded -PathType Leaf) {
            return (Resolve-Path -LiteralPath $expanded).Path
        }
    }
    return $null
}

function Resolve-ToolPath {
    param(
        [string]$Configured,
        [string[]]$Candidates,
        [string]$CommandName
    )

    $path = Get-FirstExistingPath (@($Configured) + $Candidates)
    if ($path) { return $path }

    if (-not [string]::IsNullOrWhiteSpace($CommandName)) {
        $command = Get-Command $CommandName -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
    }
    return $null
}

function Require-File {
    param([string]$Path, [string]$Description)

    if ([string]::IsNullOrWhiteSpace($Path) -or
        -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Description was not found. Configure it in tools/local.env.ps1."
    }
    return (Resolve-Path -LiteralPath $Path).Path
}

function Invoke-LoggedProcess {
    param(
        [Parameter(Mandatory=$true)][string]$Executable,
        [Parameter(Mandatory=$true)][string[]]$Arguments,
        [Parameter(Mandatory=$true)][string]$LogPath,
        [string]$WorkingDirectory = $script:RepoRoot,
        [switch]$Quiet
    )

    $Executable = Require-File $Executable "Executable"
    $logDir = Split-Path -Parent $LogPath
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null

    $previousErrorActionPreference = $ErrorActionPreference
    $exitCode = $null
    Push-Location $WorkingDirectory
    try {
        # Windows PowerShell 5.1 wraps native stderr as ErrorRecord objects.
        # Keep capturing stderr in the log without treating ordinary tool
        # diagnostics as terminating PowerShell exceptions.
        $ErrorActionPreference = "Continue"
        if ($Quiet) {
            # Keep a pipeline attached so GUI-subsystem launchers such as
            # STM32CubeMX remain awaited, but do not stream their verbose log
            # into the Codex/tool console.
            & $Executable @Arguments 2>&1 |
                Tee-Object -FilePath $LogPath |
                Out-Null
        }
        else {
            & $Executable @Arguments 2>&1 | Tee-Object -FilePath $LogPath
        }
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
        Pop-Location
    }

    if ($exitCode -ne 0) {
        throw "Process failed with exit code $exitCode. See $LogPath"
    }
}

function Write-Utf8Json {
    param([object]$InputObject, [string]$Path)
    $InputObject | ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath $Path -Encoding UTF8
}
