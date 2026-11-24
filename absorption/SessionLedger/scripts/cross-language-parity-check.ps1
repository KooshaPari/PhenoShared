<#
.SYNOPSIS
  Machine-check the C08 L75 cross-language OKF fixture parity SSOT + structural
  harness + Python/Go/TypeScript adapter stubs.

.DESCRIPTION
  Verifies docs/ops/cross-language-parity.md documents the Python / TypeScript /
  Go parity matrix, language-tag rule, Harbor N/A boundary, and native language
  adapter stub; that each matrix fixture exists with a matching source_id
  language tag; that a thin structural-invariant harness finds the same OKF
  v1.0 core shape across those fixtures; that the Python reference adapter can
  validate + emit the Python fixture path; that Go and TypeScript adapter sources
  exist (runtime go run / Node >=22 when installed; otherwise explicit skip).
  Hermetic: no daemon, no network, no cargo (stdlib python always; optional host
  go / node).

.PARAMETER SelfCheck
  Explicit docs/fixture/structural/adapter smoke (CI unit proof). Same checks as
  the default path.

.EXAMPLE
  pwsh ./scripts/cross-language-parity-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [switch]$SelfCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$docPath = Join-Path $repoRoot "docs/ops/cross-language-parity.md"
$evalScopePath = Join-Path $repoRoot "docs/EVAL_SCOPE.md"
$manifestPath = Join-Path $repoRoot "docs/ops/eval-manifest.json"
$checkScript = Join-Path $repoRoot "scripts/cross-language-parity-check.ps1"
$rustWrapper = Join-Path $repoRoot "tests/cross_language_parity.rs"
$workflowPath = Join-Path $repoRoot ".github/workflows/eval-compression.yml"
$fixturesDir = Join-Path $repoRoot "docs/reference/conformance/fixtures"
$adapterReadme = Join-Path $repoRoot "adapters/README.md"
$pythonAdapter = Join-Path $repoRoot "adapters/python/okf_adapter.py"
$pythonFixture = Join-Path $fixturesDir "cursor-python-029.okf.json"
$goMod = Join-Path $repoRoot "adapters/go/go.mod"
$goMain = Join-Path $repoRoot "adapters/go/main.go"
$goDir = Join-Path $repoRoot "adapters/go"
$goFixture = Join-Path $fixturesDir "forge-go-module-026.okf.json"
$tsAdapter = Join-Path $repoRoot "adapters/typescript/okf_adapter.ts"
$tsFixture = Join-Path $fixturesDir "codex-typescript-023.okf.json"

$parityRows = @(
    @{ Language = "Python"; Tag = "python"; Fixture = "cursor-python-029.okf.json" }
    @{ Language = "TypeScript"; Tag = "typescript"; Fixture = "codex-typescript-023.okf.json" }
    @{ Language = "Go"; Tag = "go"; Fixture = "forge-go-module-026.okf.json" }
)

# Shared OKF v1.0 entity types every cross-language matrix fixture must carry.
$requiredSharedEntityTypes = @(
    "intent"
    "acceptance"
    "constraint"
    "resource"
    "state"
    "gate"
)

$allowedRelationTypes = @(
    "verified_by"
    "bounded_by"
    "grounds"
    "requires"
    "asserts"
)

function Assert-File {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Label
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing $Label at '$Path'."
    }
}

function Write-Check {
    param([string]$Label, [bool]$Ok)
    $mark = if ($Ok) { "PASS" } else { "FAIL" }
    Write-Host "  [$mark] $Label"
    return $Ok
}

function Test-DocContains {
    param(
        [Parameter(Mandatory = $true)][string]$Doc,
        [Parameter(Mandatory = $true)][string]$Needle,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "docs/ops/cross-language-parity.md missing required anchor: '$Needle'"
    }
}

function Get-EntityTypeSet {
    param([Parameter(Mandatory = $true)]$Entities)
    $types = New-Object 'System.Collections.Generic.HashSet[string]'
    foreach ($entity in @($Entities)) {
        if ($null -eq $entity.type -or [string]::IsNullOrWhiteSpace([string]$entity.type)) {
            throw "Entity missing type."
        }
        [void]$types.Add([string]$entity.type)
    }
    return $types
}

function Assert-OkfStructuralInvariants {
    param(
        [Parameter(Mandatory = $true)][string]$Language,
        [Parameter(Mandatory = $true)][string]$Stem,
        [Parameter(Mandatory = $true)]$Doc
    )

    if ($null -eq $Doc.okf -or [string]$Doc.okf -ne "1.0") {
        throw "$Language fixture: expected okf '1.0', got '$($Doc.okf)'."
    }
    if ($null -eq $Doc.source_id -or [string]$Doc.source_id -ne $Stem) {
        throw "$Language fixture: expected source_id '$Stem', got '$($Doc.source_id)'."
    }
    if ($null -eq $Doc.provenance) {
        throw "$Language fixture: missing document provenance."
    }
    if ([string]$Doc.provenance.source_id -ne $Stem) {
        throw "$Language fixture: provenance.source_id must equal '$Stem'."
    }
    if ($null -eq $Doc.entities) {
        throw "$Language fixture: missing entities array."
    }

    $entities = @($Doc.entities)
    if ($entities.Count -lt 1) {
        throw "$Language fixture: entities must be non-empty."
    }

    $ids = New-Object 'System.Collections.Generic.HashSet[string]'
    foreach ($entity in $entities) {
        if ($null -eq $entity.id -or [string]::IsNullOrWhiteSpace([string]$entity.id)) {
            throw "$Language fixture: entity missing id."
        }
        if ($null -eq $entity.type -or [string]::IsNullOrWhiteSpace([string]$entity.type)) {
            throw "$Language fixture: entity '$($entity.id)' missing type."
        }
        if ($null -eq $entity.label -or [string]::IsNullOrWhiteSpace([string]$entity.label)) {
            throw "$Language fixture: entity '$($entity.id)' missing label."
        }
        if (-not $ids.Add([string]$entity.id)) {
            throw "$Language fixture: duplicate entity id '$($entity.id)'."
        }
    }

    $typeSet = Get-EntityTypeSet -Entities $entities
    foreach ($needed in $requiredSharedEntityTypes) {
        if (-not $typeSet.Contains($needed)) {
            throw "$Language fixture: missing required shared entity type '$needed'."
        }
    }

    $relations = @()
    if ($null -ne $Doc.relations) {
        $relations = @($Doc.relations)
    }
    if ($relations.Count -lt 1) {
        throw "$Language fixture: relations must be non-empty for parity fixtures."
    }

    foreach ($rel in $relations) {
        if ($null -eq $rel.source -or -not $ids.Contains([string]$rel.source)) {
            throw "$Language fixture: relation source '$($rel.source)' not in entities."
        }
        if ($null -eq $rel.target -or -not $ids.Contains([string]$rel.target)) {
            throw "$Language fixture: relation target '$($rel.target)' not in entities."
        }
        if ($null -eq $rel.type -or ($allowedRelationTypes -notcontains [string]$rel.type)) {
            throw "$Language fixture: relation type '$($rel.type)' not in OKF v1.0 set."
        }
        if ($null -eq $rel.provenance -or [string]$rel.provenance.source_id -ne $Stem) {
            throw "$Language fixture: relation provenance.source_id must equal '$Stem'."
        }
    }

    # Fingerprint = sorted intersection of present types with the shared required core.
    $corePresent = @($requiredSharedEntityTypes | Where-Object { $typeSet.Contains($_) } | Sort-Object)
    return ($corePresent -join ",")
}

function Resolve-Python {
    foreach ($candidate in @("python3", "python")) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -ne $cmd) {
            return $cmd.Source
        }
    }
    throw "python3/python not found on PATH (needed for adapters/python/okf_adapter.py SelfCheck)."
}

function Resolve-Go {
    $cmd = Get-Command "go" -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
        return $cmd.Source
    }
    return $null
}

function Invoke-PythonAdapter {
    param(
        [Parameter(Mandatory = $true)][string]$Python,
        [Parameter(Mandatory = $true)][string]$AdapterPath,
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string]$FixturePath
    )

    $output = & $Python $AdapterPath $Command $FixturePath 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($output | Out-String).TrimEnd()
    if ($exitCode -ne 0) {
        throw "Python OKF adapter '$Command' failed (exit $exitCode): $text"
    }
    return $text
}

function Invoke-GoAdapter {
    param(
        [Parameter(Mandatory = $true)][string]$Go,
        [Parameter(Mandatory = $true)][string]$GoDir,
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string]$FixturePath
    )

    $output = & $Go -C $GoDir run . $Command $FixturePath 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($output | Out-String).TrimEnd()
    if ($exitCode -ne 0) {
        throw "Go OKF adapter '$Command' failed (exit $exitCode): $text"
    }
    return $text
}

function Resolve-Node {
    $cmd = Get-Command node -ErrorAction SilentlyContinue
    if ($null -eq $cmd) {
        return $null
    }
    $versionOut = & $cmd.Source --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    $match = [regex]::Match([string]$versionOut, 'v(\d+)\.')
    if (-not $match.Success) {
        return $null
    }
    $major = [int]$match.Groups[1].Value
    if ($major -lt 22) {
        return $null
    }
    return $cmd.Source
}

function Invoke-TypeScriptAdapter {
    param(
        [Parameter(Mandatory = $true)][string]$Node,
        [Parameter(Mandatory = $true)][string]$AdapterPath,
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string]$FixturePath
    )

    $output = & $Node --no-warnings --experimental-strip-types $AdapterPath $Command $FixturePath 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($output | Out-String).TrimEnd()
    if ($exitCode -ne 0) {
        throw "TypeScript OKF adapter '$Command' failed (exit $exitCode): $text"
    }
    return $text
}

Write-Host "Cross-language parity checklist check (C08 L75)"
if ($SelfCheck) {
    Write-Host "Mode: SelfCheck (docs + fixture tags + structural harness + Python/Go/TypeScript adapters; no cargo / no network)"
}

Assert-File -Path $docPath -Label "cross-language parity doc"
Assert-File -Path $checkScript -Label "cross-language parity check script"
Assert-File -Path $rustWrapper -Label "cross-language parity rust SelfCheck wrapper"
Assert-File -Path $evalScopePath -Label "EVAL_SCOPE.md"
Assert-File -Path $manifestPath -Label "eval-manifest.json"
Assert-File -Path $workflowPath -Label "eval-compression workflow"
Assert-File -Path $adapterReadme -Label "adapters README (language-agnostic interface)"
Assert-File -Path $pythonAdapter -Label "Python OKF adapter reference"
Assert-File -Path $pythonFixture -Label "Python matrix fixture for adapter SelfCheck"
Assert-File -Path $goMod -Label "Go OKF adapter go.mod"
Assert-File -Path $goMain -Label "Go OKF adapter main.go"
Assert-File -Path $goFixture -Label "Go matrix fixture for adapter SelfCheck"
Assert-File -Path $tsAdapter -Label "TypeScript OKF adapter reference"
Assert-File -Path $tsFixture -Label "TypeScript matrix fixture for adapter SelfCheck"

$doc = Get-Content -LiteralPath $docPath -Raw
$evalScope = Get-Content -LiteralPath $evalScopePath -Raw
$manifest = Get-Content -LiteralPath $manifestPath -Raw
$workflow = Get-Content -LiteralPath $workflowPath -Raw
$adapterDoc = Get-Content -LiteralPath $adapterReadme -Raw
$adapterSrc = Get-Content -LiteralPath $pythonAdapter -Raw
$goSrc = Get-Content -LiteralPath $goMain -Raw
$goModSrc = Get-Content -LiteralPath $goMod -Raw
$tsSrc = Get-Content -LiteralPath $tsAdapter -Raw

Write-Host "Doc anchors:"
Test-DocContains -Doc $doc -Needle "# Cross-language OKF fixture parity (SSOT)" `
    -Label "SSOT heading"
Test-DocContains -Doc $doc -Needle "## Parity matrix" `
    -Label "parity matrix section"
Test-DocContains -Doc $doc -Needle "### Fixture language-tag rule" `
    -Label "language-tag rule"
Test-DocContains -Doc $doc -Needle "## Structural invariant harness" `
    -Label "structural invariant harness section"
Test-DocContains -Doc $doc -Needle "## Native language adapter stub" `
    -Label "native language adapter stub section"
Test-DocContains -Doc $doc -Needle "cursor-python-029.okf.json" `
    -Label "Python fixture row"
Test-DocContains -Doc $doc -Needle "codex-typescript-023.okf.json" `
    -Label "TypeScript fixture row"
Test-DocContains -Doc $doc -Needle "forge-go-module-026.okf.json" `
    -Label "Go fixture row"
Test-DocContains -Doc $doc -Needle "Harbor / Portage / Terminal-Bench" `
    -Label "Harbor N/A non-goal"
Test-DocContains -Doc $doc -Needle "scripts/cross-language-parity-check.ps1" `
    -Label "SelfCheck script reference"
Test-DocContains -Doc $doc -Needle "-SelfCheck" `
    -Label "SelfCheck invocation"
Test-DocContains -Doc $doc -Needle "Cross-language parity SelfCheck | **done**" `
    -Label "SelfCheck gate row"
Test-DocContains -Doc $doc -Needle "tests/cross_language_parity.rs" `
    -Label "rust wrapper reference"
Test-DocContains -Doc $doc -Needle "adapters/python/okf_adapter.py" `
    -Label "Python adapter path reference"
Test-DocContains -Doc $doc -Needle "adapters/go/main.go" `
    -Label "Go adapter path reference"
Test-DocContains -Doc $doc -Needle "adapters/typescript/okf_adapter.ts" `
    -Label "TypeScript adapter path reference"

Write-Host "Adapter interface anchors:"
$ifaceOk = $adapterDoc.Contains("load(path)") -and `
    $adapterDoc.Contains("validate(doc)") -and `
    $adapterDoc.Contains("emit(doc)")
[void](Write-Check -Label "adapters/README.md load/validate/emit contract" -Ok $ifaceOk)
if (-not $ifaceOk) {
    throw "adapters/README.md missing load/validate/emit interface anchors"
}
$harborOk = $adapterDoc.Contains("not") -and $adapterDoc.ToLowerInvariant().Contains("harbor")
[void](Write-Check -Label "adapters/README.md Harbor non-goal" -Ok $harborOk)
if (-not $harborOk) {
    throw "adapters/README.md must keep Harbor out of scope"
}
$goReadmeOk = $adapterDoc.Contains("go/main.go") -or $adapterDoc.Contains("adapters/go")
[void](Write-Check -Label "adapters/README.md Go adapter row" -Ok $goReadmeOk)
if (-not $goReadmeOk) {
    throw "adapters/README.md missing Go adapter reference"
}
$tsReadmeOk = $adapterDoc.Contains("typescript/okf_adapter.ts") -or $adapterDoc.Contains("adapters/typescript")
[void](Write-Check -Label "adapters/README.md TypeScript adapter row" -Ok $tsReadmeOk)
if (-not $tsReadmeOk) {
    throw "adapters/README.md missing TypeScript adapter reference"
}

$pyAnchors = @(
    @{ Needle = "def load("; Label = "Python load()" }
    @{ Needle = "def validate("; Label = "Python validate()" }
    @{ Needle = "def emit("; Label = "Python emit()" }
    @{ Needle = 'OKF_DIALECT = "1.0"'; Label = "Python OKF dialect 1.0" }
    @{ Needle = '"validate"'; Label = "Python validate CLI" }
    @{ Needle = '"emit"'; Label = "Python emit CLI" }
)
foreach ($anchor in $pyAnchors) {
    $ok = $adapterSrc.Contains($anchor.Needle)
    [void](Write-Check -Label $anchor.Label -Ok $ok)
    if (-not $ok) {
        throw "adapters/python/okf_adapter.py missing anchor: '$($anchor.Needle)'"
    }
}

$goAnchors = @(
    @{ Needle = "func load("; Label = "Go load()" }
    @{ Needle = "func validate("; Label = "Go validate()" }
    @{ Needle = "func emit("; Label = "Go emit()" }
    @{ Needle = 'okfDialect = "1.0"'; Label = "Go OKF dialect 1.0" }
    @{ Needle = '"validate"'; Label = "Go validate CLI" }
    @{ Needle = '"emit"'; Label = "Go emit CLI" }
)
foreach ($anchor in $goAnchors) {
    $ok = $goSrc.Contains($anchor.Needle)
    [void](Write-Check -Label $anchor.Label -Ok $ok)
    if (-not $ok) {
        throw "adapters/go/main.go missing anchor: '$($anchor.Needle)'"
    }
}
$goModOk = $goModSrc.Contains("module ") -and $goModSrc.Contains("go ")
[void](Write-Check -Label "adapters/go/go.mod module + go version" -Ok $goModOk)
if (-not $goModOk) {
    throw "adapters/go/go.mod missing module/go directives"
}

$tsAnchors = @(
    @{ Needle = "function load("; Label = "TypeScript load()" }
    @{ Needle = "function validate("; Label = "TypeScript validate()" }
    @{ Needle = "function emit("; Label = "TypeScript emit()" }
    @{ Needle = 'const OKF_DIALECT = "1.0"'; Label = "TypeScript OKF dialect 1.0" }
    @{ Needle = '"validate"'; Label = "TypeScript validate CLI" }
    @{ Needle = '"emit"'; Label = "TypeScript emit CLI" }
)
foreach ($anchor in $tsAnchors) {
    $ok = $tsSrc.Contains($anchor.Needle)
    [void](Write-Check -Label $anchor.Label -Ok $ok)
    if (-not $ok) {
        throw "adapters/typescript/okf_adapter.ts missing anchor: '$($anchor.Needle)'"
    }
}

Write-Host "Cross-links:"
$evalOk = $evalScope.Contains("cross-language-parity.md")
[void](Write-Check -Label "EVAL_SCOPE -> cross-language-parity" -Ok $evalOk)
if (-not $evalOk) {
    throw "docs/EVAL_SCOPE.md missing link to cross-language-parity.md"
}
$evalAdapterOk = $evalScope.Contains("adapters/README.md")
[void](Write-Check -Label "EVAL_SCOPE -> adapters README" -Ok $evalAdapterOk)
if (-not $evalAdapterOk) {
    throw "docs/EVAL_SCOPE.md missing link to adapters/README.md"
}

Write-Host "Parity fixtures + language tags:"
foreach ($row in $parityRows) {
    $fixturePath = Join-Path $fixturesDir $row.Fixture
    Assert-File -Path $fixturePath -Label "$($row.Language) fixture $($row.Fixture)"

    $stem = $row.Fixture -replace '\.okf\.json$', ''
    $raw = Get-Content -LiteralPath $fixturePath -Raw
    $hasSourceId = $raw.Contains("`"source_id`": `"$stem`"") -or `
        $raw.Contains("`"source_id`":`"$stem`"")
    if (-not $hasSourceId) {
        throw "Fixture $($row.Fixture) missing source_id '$stem'."
    }

    if ($stem -notlike "*$($row.Tag)*") {
        throw "Fixture stem '$stem' missing language tag '$($row.Tag)'."
    }
    if (-not $manifest.Contains($row.Fixture)) {
        throw "eval-manifest.json missing fixture anchor '$($row.Fixture)'."
    }

    Write-Host "  [PASS] $($row.Language): $($row.Fixture) (tag=$($row.Tag))"
}

Write-Host "Structural invariant harness (cross-language core fingerprint):"
$fingerprints = @()
foreach ($row in $parityRows) {
    $fixturePath = Join-Path $fixturesDir $row.Fixture
    $stem = $row.Fixture -replace '\.okf\.json$', ''
    $parsed = Get-Content -LiteralPath $fixturePath -Raw | ConvertFrom-Json
    $fp = Assert-OkfStructuralInvariants -Language $row.Language -Stem $stem -Doc $parsed
    $fingerprints += $fp
    Write-Host "  [PASS] $($row.Language): okf=1.0 + shared entity core + relation endpoints ($fp)"
}

$uniqueFp = @($fingerprints | Select-Object -Unique)
if ($uniqueFp.Count -ne 1) {
    throw "Cross-language structural fingerprints diverge: $($fingerprints -join ' | ')"
}
[void](Write-Check -Label "Python/TS/Go share identical core entity fingerprint" -Ok $true)

Write-Host "Python reference adapter (validate + emit on non-Rust fixture path):"
$python = Resolve-Python
$validateOut = Invoke-PythonAdapter -Python $python -AdapterPath $pythonAdapter `
    -Command "validate" -FixturePath $pythonFixture
if ($validateOut -notmatch "OKF validate ok") {
    throw "Python adapter validate missing success line: $validateOut"
}
[void](Write-Check -Label "python okf_adapter.py validate cursor-python-029" -Ok $true)

$emitOut = Invoke-PythonAdapter -Python $python -AdapterPath $pythonAdapter `
    -Command "emit" -FixturePath $pythonFixture
$emitted = $emitOut | ConvertFrom-Json
if ([string]$emitted.okf -ne "1.0") {
    throw "Python adapter emit produced unexpected okf dialect '$($emitted.okf)'."
}
if ([string]$emitted.source_id -ne "cursor-python-029") {
    throw "Python adapter emit produced unexpected source_id '$($emitted.source_id)'."
}
[void](Write-Check -Label "python okf_adapter.py emit cursor-python-029" -Ok $true)

Write-Host "Go reference adapter (validate + emit when go is installed):"
$go = Resolve-Go
if ($null -eq $go) {
    Write-Host "  [SKIP] go not found on PATH — retaining hermetic Go source/doc anchors only"
    [void](Write-Check -Label "go adapter runtime skipped (go absent)" -Ok $true)
}
else {
    $goValidateOut = Invoke-GoAdapter -Go $go -GoDir $goDir `
        -Command "validate" -FixturePath $goFixture
    if ($goValidateOut -notmatch "OKF validate ok") {
        throw "Go adapter validate missing success line: $goValidateOut"
    }
    [void](Write-Check -Label "go run . validate forge-go-module-026" -Ok $true)

    $goEmitOut = Invoke-GoAdapter -Go $go -GoDir $goDir `
        -Command "emit" -FixturePath $goFixture
    $goEmitted = $goEmitOut | ConvertFrom-Json
    if ([string]$goEmitted.okf -ne "1.0") {
        throw "Go adapter emit produced unexpected okf dialect '$($goEmitted.okf)'."
    }
    if ([string]$goEmitted.source_id -ne "forge-go-module-026") {
        throw "Go adapter emit produced unexpected source_id '$($goEmitted.source_id)'."
    }
    [void](Write-Check -Label "go run . emit forge-go-module-026" -Ok $true)
}

Write-Host "TypeScript reference adapter (validate + emit when Node >=22 is installed):"
$node = Resolve-Node
if ($null -eq $node) {
    Write-Host "  [SKIP] node >=22 not found on PATH — retaining hermetic TypeScript source/doc anchors only"
    [void](Write-Check -Label "typescript adapter runtime skipped (node absent or <22)" -Ok $true)
}
else {
    $tsValidateOut = Invoke-TypeScriptAdapter -Node $node -AdapterPath $tsAdapter `
        -Command "validate" -FixturePath $tsFixture
    if ($tsValidateOut -notmatch "OKF validate ok") {
        throw "TypeScript adapter validate missing success line: $tsValidateOut"
    }
    [void](Write-Check -Label "node --experimental-strip-types okf_adapter.ts validate codex-typescript-023" -Ok $true)

    $tsEmitOut = Invoke-TypeScriptAdapter -Node $node -AdapterPath $tsAdapter `
        -Command "emit" -FixturePath $tsFixture
    $tsEmitted = $tsEmitOut | ConvertFrom-Json
    if ([string]$tsEmitted.okf -ne "1.0") {
        throw "TypeScript adapter emit produced unexpected okf dialect '$($tsEmitted.okf)'."
    }
    if ([string]$tsEmitted.source_id -ne "codex-typescript-023") {
        throw "TypeScript adapter emit produced unexpected source_id '$($tsEmitted.source_id)'."
    }
    [void](Write-Check -Label "node --experimental-strip-types okf_adapter.ts emit codex-typescript-023" -Ok $true)
}

Write-Host "Workflow anchors:"
$wfOk = $workflow.Contains("cross-language-parity-check.ps1")
[void](Write-Check -Label "eval-compression.yml SelfCheck step" -Ok $wfOk)
if (-not $wfOk) {
    throw ".github/workflows/eval-compression.yml missing cross-language-parity-check.ps1"
}

Write-Host "Cross-language parity SelfCheck passed (C08 L75 SSOT + structural invariant harness + Python/Go/TypeScript adapter stubs)."
