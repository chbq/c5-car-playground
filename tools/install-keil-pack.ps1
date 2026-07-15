[CmdletBinding(SupportsShouldProcess=$true)]
param(
    [string]$Vendor = "Keil",
    [string]$Name = "STM32F1xx_DFP",
    [string]$Version = "",
    [string]$PackRoot = "",
    [switch]$Install
)

. (Join-Path $PSScriptRoot "common.ps1")

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = $Env:C5_STM32F1_DFP_VERSION
}
if ([string]::IsNullOrWhiteSpace($PackRoot)) {
    $PackRoot = $Env:C5_KEIL_PACK_ROOT
}
if ([string]::IsNullOrWhiteSpace($Version) -or [string]::IsNullOrWhiteSpace($PackRoot)) {
    throw "Pack version and root must be configured in tools/local.env.ps1."
}

$PackRoot = [IO.Path]::GetFullPath(
    [Environment]::ExpandEnvironmentVariables($PackRoot)
)
$familyRoot = Join-Path $PackRoot "$Vendor\$Name"
$target = Join-Path $familyRoot $Version
$pdscName = "$Vendor.$Name.pdsc"
$installedPdsc = Join-Path $target $pdscName

if (Test-Path -LiteralPath $installedPdsc -PathType Leaf) {
    Write-Host "Pack already installed: $target"
    exit 0
}
if (-not $Install) {
    Write-Warning "Pack is missing: $target"
    exit 2
}
if (Test-Path -LiteralPath $target) {
    throw "Pack target already exists but is incomplete: $target"
}

$url = "https://www.keil.com/pack/$Vendor.$Name.$Version.pack"
$cacheDir = Join-Path $BuildDir "toolchain-cache"
$archive = Join-Path $cacheDir "$Vendor.$Name.$Version.pack"
$stagingParent = Join-Path $PackRoot ".codex-staging"
$staging = Join-Path $stagingParent "$Vendor.$Name.$Version.$PID"

function Assert-WithinPackRoot {
    param([string]$Path)
    $full = [IO.Path]::GetFullPath($Path)
    $prefix = $PackRoot.TrimEnd('\') + '\'
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing pack operation outside configured root: $full"
    }
}

Assert-WithinPackRoot $familyRoot
Assert-WithinPackRoot $target
Assert-WithinPackRoot $stagingParent
Assert-WithinPackRoot $staging

if (-not $PSCmdlet.ShouldProcess($target, "Download and install $Vendor.$Name.$Version")) {
    exit 0
}

New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) {
    Write-Host "Downloading $url"
    Invoke-WebRequest -Uri $url -OutFile $archive -UseBasicParsing
}

$archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
Write-Host "Pack SHA256: $archiveHash"

New-Item -ItemType Directory -Force -Path $stagingParent | Out-Null
if (Test-Path -LiteralPath $staging) {
    throw "Staging path unexpectedly exists: $staging"
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
try {
    [IO.Compression.ZipFile]::ExtractToDirectory($archive, $staging)
    $stagedPdsc = Join-Path $staging $pdscName
    if (-not (Test-Path -LiteralPath $stagedPdsc -PathType Leaf)) {
        throw "Downloaded pack does not contain $pdscName."
    }
    New-Item -ItemType Directory -Force -Path $familyRoot | Out-Null
    Move-Item -LiteralPath $staging -Destination $target
}
finally {
    if (Test-Path -LiteralPath $staging) {
        Assert-WithinPackRoot $staging
        Remove-Item -LiteralPath $staging -Recurse -Force
    }
}

if (-not (Test-Path -LiteralPath $installedPdsc -PathType Leaf)) {
    throw "Pack installation did not produce the expected PDSC: $installedPdsc"
}

Write-Host "Installed pack: $target"
