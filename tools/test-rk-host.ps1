[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot "common.ps1")

$python = Resolve-ToolPath `
    -Configured $Env:C5_PYTHON_EXE `
    -Candidates @("D:\anaconda3\python.exe") `
    -CommandName "python.exe"
$python = Require-File $python "Python 3"

$project = Join-Path $RepoRoot "target\rk3588-goalkeeper"
$testLog = Join-Path $BuildDir "rk-host-test.log"
$compileLog = Join-Path $BuildDir "rk-python-compile.log"

Invoke-LoggedProcess `
    -Executable $python `
    -Arguments @("-m", "unittest", "discover", "-s", (Join-Path $project "tests"), "-v") `
    -LogPath $testLog `
    -Quiet

Invoke-LoggedProcess `
    -Executable $python `
    -Arguments @("-m", "compileall", "-q", $project) `
    -LogPath $compileLog `
    -Quiet

Write-Host "RK3588 HOST protocol tests passed."
Write-Host "Test log: $testLog"
Write-Host "Compile log: $compileLog"
