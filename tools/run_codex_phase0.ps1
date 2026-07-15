[CmdletBinding()]
param()

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$promptPath = Join-Path $repoRoot "prompts\00_first_run_audit.md"

if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
    throw "Codex CLI was not found on PATH."
}

$prompt = Get-Content -LiteralPath $promptPath -Raw
Push-Location $repoRoot
try {
    codex exec --sandbox workspace-write $prompt
}
finally {
    Pop-Location
}
