[CmdletBinding()]
param(
    [string]$SshTarget = $Env:C5_RK_SSH_TARGET,
    [string]$ProjectPath = $Env:C5_RK_PROJECT_PATH,
    [string]$Python = $Env:C5_RK_PYTHON
)

$ErrorActionPreference = "Stop"

$localEnv = Join-Path $PSScriptRoot "local.env.ps1"
if (Test-Path -LiteralPath $localEnv -PathType Leaf) {
    . $localEnv
}
if ([string]::IsNullOrWhiteSpace($SshTarget)) {
    $SshTarget = $Env:C5_RK_SSH_TARGET
}
if ([string]::IsNullOrWhiteSpace($ProjectPath)) {
    $ProjectPath = $Env:C5_RK_PROJECT_PATH
}
if ([string]::IsNullOrWhiteSpace($Python)) {
    $Python = $Env:C5_RK_PYTHON
}

if ([string]::IsNullOrWhiteSpace($SshTarget)) {
    throw "Set C5_RK_SSH_TARGET in tools/local.env.ps1 (for example orangepi@192.168.1.20)."
}
if ([string]::IsNullOrWhiteSpace($ProjectPath)) {
    $ProjectPath = "/home/orangepi/c5-car-playground/target/rk3588-goalkeeper"
}
if ([string]::IsNullOrWhiteSpace($Python)) {
    $Python = "python3"
}
if ($SshTarget -notmatch '^[A-Za-z0-9_.@-]+$') {
    throw "C5_RK_SSH_TARGET contains unsupported characters."
}
if ($ProjectPath -notmatch '^/[A-Za-z0-9_./-]+$') {
    throw "C5_RK_PROJECT_PATH must be an absolute path without spaces."
}
if ($Python -notmatch '^/?[A-Za-z0-9_./-]+$') {
    throw "C5_RK_PYTHON contains unsupported characters."
}

$ssh = Get-Command ssh.exe -ErrorAction SilentlyContinue
if (-not $ssh) {
    throw "OpenSSH client ssh.exe was not found."
}

$remoteCommand = "cd '$ProjectPath' && '$Python' doctor.py"
& $ssh.Source `
    -o BatchMode=yes `
    -o ConnectTimeout=5 `
    -- $SshTarget $remoteCommand
if ($LASTEXITCODE -ne 0) {
    throw "Remote RK3588 audit failed with exit code $LASTEXITCODE."
}
