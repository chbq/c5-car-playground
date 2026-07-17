[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ProjectPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
$firmwareRoot = (Resolve-Path (Join-Path (Split-Path -Parent $ProjectPath) "..")).Path
$appSource = Join-Path $firmwareRoot "App\Src"
$appInclude = Join-Path $firmwareRoot "App\Inc"

if (-not (Test-Path -LiteralPath $appInclude -PathType Container)) {
    throw "Application include directory not found: $appInclude"
}

$sourceFiles = @(Get-ChildItem -LiteralPath $appSource -Filter "*.c" -File |
    Sort-Object Name)
if ($sourceFiles.Count -eq 0) {
    throw "No application sources found in $appSource"
}

$text = [System.IO.File]::ReadAllText($ProjectPath)

$includePattern = '<IncludePath>([^<]*\.\./Core/Inc[^<]*)</IncludePath>'
$includeMatch = [regex]::Match($text, $includePattern)
if (-not $includeMatch.Success) {
    throw "Could not locate the target C include path in $ProjectPath"
}
$includeItems = @($includeMatch.Groups[1].Value -split ';')
if ($includeItems -notcontains '../App/Inc') {
    $newIncludes = ($includeItems + '../App/Inc') -join ';'
    $text = $text.Remove($includeMatch.Groups[1].Index,
                         $includeMatch.Groups[1].Length)
    $text = $text.Insert($includeMatch.Groups[1].Index, $newIncludes)
}

$existingGroupPattern = '(?s)\s*<Group>\s*<GroupName>Application/User/App</GroupName>.*?</Group>'
$text = [regex]::Replace($text, $existingGroupPattern, '')

$fileXml = foreach ($file in $sourceFiles) {
    @"
            <File>
              <FileName>$($file.Name)</FileName>
              <FileType>1</FileType>
              <FilePath>../App/Src/$($file.Name)</FilePath>
            </File>
"@
}

$groupXml = @"
        <Group>
          <GroupName>Application/User/App</GroupName>
          <Files>
$($fileXml -join "`r`n")
          </Files>
        </Group>
"@

$groupsEnd = '      </Groups>'
if (-not $text.Contains($groupsEnd)) {
    throw "Could not locate the Groups closing element in $ProjectPath"
}
$text = $text.Replace($groupsEnd, "$groupXml`r`n$groupsEnd")

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($ProjectPath, $text, $utf8NoBom)
Write-Host "Synchronized $($sourceFiles.Count) App source file(s) into $ProjectPath"
