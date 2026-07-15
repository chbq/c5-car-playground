[CmdletBinding()]
param(
    [switch]$ProbeProgrammer,
    [switch]$IncludeSerialPorts
)

. (Join-Path $PSScriptRoot "common.ps1")

function Get-ProductVersion {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path) -or
        -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }
    $version = (Get-Item -LiteralPath $Path).VersionInfo.ProductVersion
    if ([string]::IsNullOrWhiteSpace($version)) {
        $version = (Get-Item -LiteralPath $Path).VersionInfo.FileVersion
    }
    if ($version) { return $version.Trim().TrimStart(">") }
    return $null
}

function Get-CompilerVersion {
    param([string]$Path, [string]$Argument)

    if ([string]::IsNullOrWhiteSpace($Path) -or
        -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }
    try {
        $output = @(& $Path $Argument 2>&1)
        $component = $output | Where-Object { $_ -match "^Component:" } |
            Select-Object -First 1
        if ($component) { return ($component -replace "^Component:\s*", "").Trim() }
        return ($output | Select-Object -First 1).ToString().Trim()
    }
    catch {
        return "VERSION QUERY FAILED: $($_.Exception.Message)"
    }
}

function Get-InstalledVersions {
    param([string]$Root)

    if ([string]::IsNullOrWhiteSpace($Root) -or
        -not (Test-Path -LiteralPath $Root -PathType Container)) {
        return @()
    }
    return @(Get-ChildItem -LiteralPath $Root -Directory |
        Sort-Object Name | Select-Object -ExpandProperty Name)
}

$cubeMx = Resolve-ToolPath `
    -Configured $Env:C5_CUBEMX_EXE `
    -Candidates @(
        "D:\Program Files\STMicroelectronics\STM32Cube\STM32CubeMX\STM32CubeMX.exe",
        "$Env:ProgramFiles\STMicroelectronics\STM32Cube\STM32CubeMX\STM32CubeMX.exe",
        "${Env:ProgramFiles(x86)}\STMicroelectronics\STM32Cube\STM32CubeMX\STM32CubeMX.exe"
    ) `
    -CommandName "STM32CubeMX.exe"

$uv4 = Resolve-ToolPath `
    -Configured $Env:C5_UV4_EXE `
    -Candidates @(
        "C:\Keil_v5\UV4\UV4.exe",
        "$Env:ProgramFiles\Keil_v5\UV4\UV4.exe",
        "${Env:ProgramFiles(x86)}\Keil_v5\UV4\UV4.exe"
    ) `
    -CommandName "UV4.exe"

$cubeProgrammer = Resolve-ToolPath `
    -Configured $Env:C5_CUBE_PROGRAMMER_EXE `
    -Candidates @(
        "D:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe",
        "$Env:ProgramFiles\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe",
        "${Env:ProgramFiles(x86)}\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"
    ) `
    -CommandName "STM32_Programmer_CLI.exe"

$armcc = Resolve-ToolPath `
    -Configured $Env:C5_ARMCC_EXE `
    -Candidates @("C:\Keil_v5\ARM\ARMCC\bin\armcc.exe") `
    -CommandName "armcc.exe"

$armclang = Resolve-ToolPath `
    -Configured $Env:C5_ARMCLANG_EXE `
    -Candidates @("C:\Keil_v5\ARM\ARMCLANG\bin\armclang.exe") `
    -CommandName "armclang.exe"

$python = Resolve-ToolPath `
    -Configured $Env:C5_PYTHON_EXE `
    -Candidates @("D:\anaconda3\python.exe") `
    -CommandName "python.exe"

$git = Resolve-ToolPath `
    -Configured $Env:C5_GIT_EXE `
    -Candidates @("C:\Program Files\Git\cmd\git.exe") `
    -CommandName "git.exe"

$java = Resolve-ToolPath `
    -Configured $Env:C5_JAVA_EXE `
    -Candidates @("C:\Program Files\Java\jdk-11\bin\java.exe") `
    -CommandName "java.exe"

$codex = Get-Command codex -ErrorAction SilentlyContinue

$cubeRepository = if (-not [string]::IsNullOrWhiteSpace($Env:C5_CUBE_REPOSITORY)) {
    [Environment]::ExpandEnvironmentVariables($Env:C5_CUBE_REPOSITORY)
} else {
    Join-Path $Env:USERPROFILE "STM32Cube\Repository"
}
$cubeF1Root = Join-Path $cubeRepository "STM32Cube_FW_F1_V$($Env:C5_CUBEF1_VERSION)"
$cubeF1Versions = Get-InstalledVersions $cubeRepository |
    Where-Object { $_ -like "STM32Cube_FW_F1_V*" }

$keilPackRoot = if (-not [string]::IsNullOrWhiteSpace($Env:C5_KEIL_PACK_ROOT)) {
    [Environment]::ExpandEnvironmentVariables($Env:C5_KEIL_PACK_ROOT)
} else {
    Join-Path $Env:LOCALAPPDATA "Arm\Packs"
}
$dfpFamilyRoot = Join-Path $keilPackRoot "Keil\STM32F1xx_DFP"
$dfpRoot = Join-Path $dfpFamilyRoot $Env:C5_STM32F1_DFP_VERSION
$dfpVersions = Get-InstalledVersions $dfpFamilyRoot

$selectedCompiler = if ($Env:C5_ARM_COMPILER -eq "5") { $armcc } else { $armclang }

$serialPorts = @()
if ($IncludeSerialPorts) {
    try {
        $serialPorts = Get-CimInstance Win32_SerialPort |
            Select-Object DeviceID, Name, Description
    }
    catch {
        $serialPorts = @(@{ Error = $_.Exception.Message })
    }
}

$programmerProbe = $null
if ($ProbeProgrammer -and $cubeProgrammer) {
    $probeLog = Join-Path $BuildDir "programmer-list.log"
    try {
        & $cubeProgrammer -l 2>&1 | Tee-Object -FilePath $probeLog | Out-Null
        $programmerProbe = @{
            Attempted = $true
            ExitCode = $LASTEXITCODE
            Log = $probeLog
        }
    }
    catch {
        $programmerProbe = @{
            Attempted = $true
            Error = $_.Exception.Message
            Log = $probeLog
        }
    }
}

$report = [ordered]@{
    Timestamp = (Get-Date).ToString("o")
    RepositoryRoot = $RepoRoot
    OperatingSystem = [Environment]::OSVersion.VersionString
    PowerShellVersion = $PSVersionTable.PSVersion.ToString()
    Tools = [ordered]@{
        STM32CubeMX = [ordered]@{ Path = $cubeMx; Version = Get-ProductVersion $cubeMx }
        KeilUV4 = [ordered]@{ Path = $uv4; Version = Get-ProductVersion $uv4 }
        STM32CubeProgrammerCLI = [ordered]@{ Path = $cubeProgrammer; Version = Get-ProductVersion $cubeProgrammer }
        ArmCompiler5 = [ordered]@{ Path = $armcc; Version = Get-CompilerVersion $armcc "--vsn" }
        ArmCompiler6 = [ordered]@{ Path = $armclang; Version = Get-CompilerVersion $armclang "--version" }
        Python = [ordered]@{ Path = $python; Version = Get-ProductVersion $python }
        Git = [ordered]@{ Path = $git; Version = Get-ProductVersion $git }
        Java = [ordered]@{ Path = $java; Version = Get-ProductVersion $java }
        Codex = [ordered]@{ Path = if ($codex) { $codex.Source } else { $null }; Version = $null }
    }
    Packages = [ordered]@{
        CubeRepository = $cubeRepository
        InstalledCubeF1 = $cubeF1Versions
        SelectedCubeF1 = $cubeF1Root
        KeilPackRoot = $keilPackRoot
        InstalledSTM32F1DFP = $dfpVersions
        SelectedSTM32F1DFP = $dfpRoot
    }
    Selection = [ordered]@{
        ArmCompilerMajor = $Env:C5_ARM_COMPILER
        CubeF1Version = $Env:C5_CUBEF1_VERSION
        STM32F1DFPVersion = $Env:C5_STM32F1_DFP_VERSION
    }
    ConfiguredProject = [ordered]@{
        IocPath = $Env:C5_IOC_PATH
        UvprojxPath = $Env:C5_UVPROJX_PATH
        KeilTarget = $Env:C5_KEIL_TARGET
        FirmwareImage = $Env:C5_FIRMWARE_IMAGE
        SerialPort = $Env:C5_SERIAL_PORT
        SerialBaud = $Env:C5_SERIAL_BAUD
    }
    SerialPorts = $serialPorts
    ProgrammerProbe = $programmerProbe
}

$jsonPath = Join-Path $BuildDir "doctor-report.json"
Write-Utf8Json $report $jsonPath

$mdPath = Join-Path $BuildDir "doctor-report.md"
$lines = @(
    "# C5 Development Environment Report",
    "",
    "- Generated: $($report.Timestamp)",
    "- Repository: ``$RepoRoot``",
    "",
    "## Toolchain",
    "",
    "| Tool | Version | Path |",
    "|---|---|---|"
)
foreach ($item in $report.Tools.GetEnumerator()) {
    $version = if ($item.Value.Version) { $item.Value.Version } else { "-" }
    $path = if ($item.Value.Path) { $item.Value.Path } else { "NOT FOUND" }
    $lines += "| $($item.Key) | $version | $path |"
}
$lines += @(
    "",
    "## Pinned packages",
    "",
    "| Package | Selected | Installed |",
    "|---|---|---|",
    "| STM32CubeF1 | $($report.Selection.CubeF1Version) | $($report.Packages.InstalledCubeF1 -join ', ') |",
    "| Keil STM32F1xx DFP | $($report.Selection.STM32F1DFPVersion) | $($report.Packages.InstalledSTM32F1DFP -join ', ') |",
    "| ARM compiler major | $($report.Selection.ArmCompilerMajor) | AC5 and AC6 paths reported above |",
    "",
    "## Safety note",
    "",
    "This script did not flash firmware, probe hardware unless explicitly requested, or change MCU configuration."
)
$lines | Set-Content -LiteralPath $mdPath -Encoding UTF8

Write-Host "Doctor report:"
Write-Host "  $jsonPath"
Write-Host "  $mdPath"

$requiredMissing = @()
if (-not $cubeMx) { $requiredMissing += "STM32CubeMX" }
if (-not $uv4) { $requiredMissing += "Keil UV4" }
if (-not $cubeProgrammer) { $requiredMissing += "STM32CubeProgrammer CLI" }
if (-not $selectedCompiler) { $requiredMissing += "Selected ARM compiler $($Env:C5_ARM_COMPILER)" }
if (-not (Test-Path -LiteralPath $cubeF1Root -PathType Container)) {
    $requiredMissing += "STM32CubeF1 $($Env:C5_CUBEF1_VERSION)"
}
if (-not (Test-Path -LiteralPath $dfpRoot -PathType Container)) {
    $requiredMissing += "Keil STM32F1xx DFP $($Env:C5_STM32F1_DFP_VERSION)"
}

if ($requiredMissing.Count -gt 0) {
    Write-Warning ("Required toolchain inputs not found: " + ($requiredMissing -join ", "))
    exit 2
}
exit 0
