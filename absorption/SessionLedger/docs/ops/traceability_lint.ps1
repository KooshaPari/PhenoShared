[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$allowedStatuses = @("done", "partial", "todo", "blocked", "na")
$errors = [System.Collections.Generic.List[string]]::new()
$opsDir = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $opsDir "../..")).Path
$tracePath = Join-Path $opsDir "TRACEABILITY.json"
$frPath = Join-Path $repoRoot "docs/functional_requirements.md"
$planPath = Join-Path $repoRoot "PLAN.md"
$wbsPath = Join-Path $opsDir "WBS.md"

if (-not (Test-Path -LiteralPath $tracePath -PathType Leaf)) {
    Write-Error "Missing traceability SSOT: $tracePath"
    exit 1
}

if (-not (Test-Path -LiteralPath $frPath -PathType Leaf)) {
    Write-Error "Missing functional requirements catalog: $frPath"
    exit 1
}

try {
    $trace = Get-Content -LiteralPath $tracePath -Raw | ConvertFrom-Json
}
catch {
    Write-Error "TRACEABILITY.json is not valid JSON: $($_.Exception.Message)"
    exit 1
}

if (-not ($trace.PSObject.Properties.Name -contains "schema")) {
    $errors.Add("TRACEABILITY.json is missing the schema key.")
}
elseif ($trace.schema -ne "sessionledger.traceability/v1") {
    $errors.Add("Unsupported schema '$($trace.schema)'; expected sessionledger.traceability/v1.")
}

$frCatalog = @{}
foreach ($line in Get-Content -LiteralPath $frPath) {
    if ($line -match '^\|\s*(FR-\d{3})\s*\|.*?\|\s*(done|partial|todo|blocked|na)\s*\|') {
        $frCatalog[$Matches[1]] = $Matches[2]
    }
}

if ($frCatalog.Count -eq 0) {
    $errors.Add("No FR rows were parsed from docs/functional_requirements.md.")
}

$traceFr = @{}
foreach ($item in @($trace.fr)) {
    if ($traceFr.ContainsKey($item.id)) {
        $errors.Add("Duplicate FR entry '$($item.id)' in TRACEABILITY.json.")
    }
    $traceFr[$item.id] = $item.status
}

foreach ($frId in $frCatalog.Keys) {
    if (-not $traceFr.ContainsKey($frId)) {
        $errors.Add("$frId appears in functional_requirements.md but not TRACEABILITY.json.")
    }
    elseif ($traceFr[$frId] -ne $frCatalog[$frId]) {
        $errors.Add("$frId status mismatch: FR catalog='$($frCatalog[$frId])', JSON='$($traceFr[$frId])'.")
    }
}

function Test-DocumentMirror {
    param(
        [string]$CollectionName,
        [string]$DocumentPath,
        [string]$IdPattern
    )

    $documentItems = @{}
    foreach ($line in Get-Content -LiteralPath $DocumentPath) {
        if ($line -match $IdPattern) {
            $documentItems[$Matches[1]] = $Matches[2]
        }
    }

    $jsonItems = @{}
    foreach ($item in @($trace.$CollectionName)) {
        $jsonItems[$item.id] = $item.status
    }

    foreach ($id in $documentItems.Keys) {
        if (-not $jsonItems.ContainsKey($id)) {
            $errors.Add("$id appears in $([IO.Path]::GetFileName($DocumentPath)) but not TRACEABILITY.json.")
        }
        elseif ($jsonItems[$id] -ne $documentItems[$id]) {
            $errors.Add("$id status mismatch: document='$($documentItems[$id])', JSON='$($jsonItems[$id])'.")
        }
    }
}

Test-DocumentMirror `
    -CollectionName "plan" `
    -DocumentPath $planPath `
    -IdPattern '^\|\s*(T-\d{3})\s*\|.*\|\s*(done|partial|todo|blocked|na)\s*\|'
Test-DocumentMirror `
    -CollectionName "wbs" `
    -DocumentPath $wbsPath `
    -IdPattern '^\|\s*(WBS-\d+\.\d+)\s*\|.*?\|\s*(done|partial|todo|blocked|na)\s*\|\s*(?:machine|human)\s*\|'

foreach ($collectionName in @("fr", "plan", "wbs", "clusters")) {
    foreach ($item in @($trace.$collectionName)) {
        if (-not ($item.PSObject.Properties.Name -contains "status")) {
            $errors.Add("$collectionName entry '$($item.id)' is missing status.")
        }
        elseif ($allowedStatuses -notcontains $item.status) {
            $errors.Add("$collectionName entry '$($item.id)' has invalid status '$($item.status)'.")
        }
    }
}

if ($errors.Count -gt 0) {
    foreach ($message in $errors) {
        Write-Error $message
    }
    exit 1
}

Write-Host "Traceability lint passed: $($frCatalog.Count) FRs; statuses valid."
exit 0

