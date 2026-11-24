[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$daemonDir = Join-Path $repoRoot "crates/sl-daemon"
$openapiPath = Join-Path $repoRoot "docs/api/openapi.yaml"

if (-not (Test-Path -LiteralPath $openapiPath -PathType Leaf)) {
    throw "Missing OpenAPI contract: $openapiPath"
}

if (-not (Test-Path -LiteralPath (Join-Path $daemonDir "Cargo.toml") -PathType Leaf)) {
    throw "Missing sl-daemon manifest at '$daemonDir/Cargo.toml'."
}

Write-Host "==> OpenAPI drift gate (docs/api/openapi.yaml vs sl-daemon axum routes)"
Push-Location -LiteralPath $daemonDir
try {
    cargo test openapi_route_surface --locked
    if ($LASTEXITCODE -ne 0) {
        throw "OpenAPI drift check failed. Update docs/api/openapi.yaml and crates/sl-daemon/src/http.rs together."
    }
}
finally {
    Pop-Location
}

Write-Host "OpenAPI drift gate passed."
