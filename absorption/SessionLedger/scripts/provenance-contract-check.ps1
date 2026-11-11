[CmdletBinding()]
param(
    [string]$Workflow = ".github/workflows/release.yml",
    [string]$MaterialsFixture = "docs/ops/fixtures/slsa-materials-contract.sample.json"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

function Test-SlsaMaterialsFixture {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FixturePath
    )

    if (-not (Test-Path -LiteralPath $FixturePath -PathType Leaf)) {
        throw "SLSA materials fixture not found: $FixturePath"
    }

    $Statement = Get-Content -LiteralPath $FixturePath -Raw | ConvertFrom-Json
    $Errors = [System.Collections.Generic.List[string]]::new()

    if ($Statement._type -ne "https://in-toto.io/Statement/v1") {
        $Errors.Add("fixture _type must be https://in-toto.io/Statement/v1")
    }

    if (-not $Statement.subject -or @($Statement.subject).Count -lt 1) {
        $Errors.Add("fixture subject must contain at least one entry")
    } else {
        $PrimarySubject = @($Statement.subject)[0]
        if (-not $PrimarySubject.name) {
            $Errors.Add("fixture subject[0].name is required")
        }
        if (-not $PrimarySubject.digest -or -not $PrimarySubject.digest.sha256) {
            $Errors.Add("fixture subject[0].digest.sha256 is required")
        }
    }

    if ($Statement.predicateType -notmatch "slsa\.dev/provenance") {
        $Errors.Add("fixture predicateType must identify SLSA build provenance")
    }

    $HasMaterials = $false
    if ($Statement.predicate) {
        if ($Statement.predicate.materials -and @($Statement.predicate.materials).Count -gt 0) {
            $HasMaterials = $true
        }
        if ($Statement.predicate.buildDefinition.resolvedDependencies -and
            @($Statement.predicate.buildDefinition.resolvedDependencies).Count -gt 0) {
            $HasMaterials = $true
        }
    }

    if (-not $HasMaterials) {
        $Errors.Add("fixture predicate must declare materials or buildDefinition.resolvedDependencies")
    }

    if ($Errors.Count -gt 0) {
        throw ("SLSA materials fixture check failed: {0}" -f ($Errors -join "; "))
    }

    Write-Host "SLSA materials fixture check passed for $FixturePath"
}

if ([System.IO.Path]::IsPathRooted($Workflow)) {
    $WorkflowPath = $Workflow
} else {
    $WorkflowPath = Join-Path $RepoRoot $Workflow
}

if (-not (Test-Path -LiteralPath $WorkflowPath -PathType Leaf)) {
    throw "Release workflow not found: $WorkflowPath"
}

$Content = Get-Content -LiteralPath $WorkflowPath -Raw
$Missing = [System.Collections.Generic.List[string]]::new()

if ($Content -notmatch 'attest-build-provenance@') {
    $Missing.Add("attest-build-provenance action")
}

if ($Content -notmatch '(?ms)build:\s*[\s\S]*?permissions:\s*[\s\S]*?id-token:\s*write') {
    $Missing.Add("build job id-token: write permission")
}

if ($Content -notmatch '(?ms)build:\s*[\s\S]*?permissions:\s*[\s\S]*?attestations:\s*write') {
    $Missing.Add("build job attestations: write permission")
}

if ($Content -notmatch '(?ms)build:\s*[\s\S]*?name:\s*attest platform artifact') {
    $Missing.Add("per-matrix attest platform artifact step")
}

if ($Content -notmatch '(?ms)build:\s*[\s\S]*?name:\s*attest platform artifact[\s\S]*?subject-path:') {
    $Missing.Add("build job attest platform artifact subject-path binding")
}

if ($Content -notmatch '(?ms)release:\s*[\s\S]*?attest Release assets') {
    $Missing.Add("release job attest Release assets step")
}

if ($Content -notmatch '(?ms)release:\s*[\s\S]*?attest Release assets[\s\S]*?subject-path:') {
    $Missing.Add("release job attest Release assets subject-path binding")
}

if ($Content -notmatch 'Build provenance failed for KooshaPari/SessionLedger') {
    $Missing.Add("blocking release provenance failure message")
}

if ($Missing.Count -gt 0) {
    Write-Error ("Provenance contract check failed. Missing: {0}" -f ($Missing -join ", "))
    exit 1
}

Write-Host "Provenance contract check passed for $WorkflowPath"

if ([System.IO.Path]::IsPathRooted($MaterialsFixture)) {
    $FixturePath = $MaterialsFixture
} else {
    $FixturePath = Join-Path $RepoRoot $MaterialsFixture
}

Test-SlsaMaterialsFixture -FixturePath $FixturePath
