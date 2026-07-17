[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot "common.ps1")

$vswhere = Resolve-ToolPath `
    -Configured $Env:C5_VSWHERE_EXE `
    -Candidates @(
        "${Env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    ) `
    -CommandName "vswhere.exe"
$vswhere = Require-File $vswhere "Visual Studio vswhere.exe"

$vsInstall = & $vswhere `
    -latest `
    -products '*' `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath
if ([string]::IsNullOrWhiteSpace($vsInstall)) {
    throw "Visual Studio C++ build tools were not found."
}

$vsDevCmd = Require-File `
    (Join-Path $vsInstall "Common7\Tools\VsDevCmd.bat") `
    "Visual Studio developer command script"

$testBuildDir = Join-Path $BuildDir "host-tests"
New-Item -ItemType Directory -Force -Path $testBuildDir | Out-Null

$testSource = Join-Path $RepoRoot "tests\host\c5_motion_tests.c"
$appInclude = Join-Path $RepoRoot "target\c5-firmware\App\Inc"
$appSource = Join-Path $RepoRoot "target\c5-firmware\App\Src"
$testExe = Join-Path $testBuildDir "c5_motion_tests.exe"
$compileScript = Join-Path $testBuildDir "compile-c5-motion-tests.cmd"
$compileLog = Join-Path $BuildDir "host-test-compile.log"
$runLog = Join-Path $BuildDir "host-test-run.log"

$lines = @(
    '@echo off',
    "call `"$vsDevCmd`" -arch=x64 -host_arch=x64 >nul",
    'if errorlevel 1 exit /b %errorlevel%',
    ('cl.exe /nologo /W4 /WX /TC /I"{0}" "{1}" "{2}" "{3}" "{4}" "{5}" "{6}" "{7}" /Fe:"{8}"' -f `
        $appInclude,
        $testSource,
        (Join-Path $appSource 'c5_motor_protocol.c'),
        (Join-Path $appSource 'c5_mecanum.c'),
        (Join-Path $appSource 'c5_motion.c'),
        (Join-Path $appSource 'c5_ps2.c'),
        (Join-Path $appSource 'c5_remote.c'),
        (Join-Path $appSource 'c5_control.c'),
        $testExe)
)
$lines | Set-Content -LiteralPath $compileScript -Encoding ASCII

Invoke-LoggedProcess `
    -Executable "$Env:SystemRoot\System32\cmd.exe" `
    -Arguments @('/d', '/c', "`"$compileScript`"") `
    -LogPath $compileLog `
    -WorkingDirectory $testBuildDir

Invoke-LoggedProcess `
    -Executable $testExe `
    -Arguments @('--run') `
    -LogPath $runLog `
    -WorkingDirectory $testBuildDir

Write-Host "Host motion tests passed."
Write-Host "Compile log: $compileLog"
Write-Host "Run log: $runLog"
