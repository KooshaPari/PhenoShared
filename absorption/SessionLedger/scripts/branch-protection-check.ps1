[CmdletBinding()]
param(
    [string]$Branch = "main",
    [string]$Repo = "KooshaPari/SessionLedger",
    # When set, exit 1 only if the API succeeds and required controls are missing.
    # Without -Strict, missing token / 404 / insufficient scope always soft-exit 0.
    [switch]$Strict,
    # Hermetic policy anchors only (C06 L59 source-provenance hook). No gh / no network.
    [switch]$PolicyOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

function Assert-SourceProvenancePolicy {
    $sourceProvDocPath = Join-Path $RepoRoot "docs/ops/source-provenance.md"
    $branchProtectionDocPath = Join-Path $RepoRoot "docs/ops/branch-protection.md"
    $codeownersPath = Join-Path $RepoRoot "CODEOWNERS"

    foreach ($pair in @(
            @{ Path = $sourceProvDocPath; Label = "source provenance policy doc" },
            @{ Path = $branchProtectionDocPath; Label = "branch protection doc" },
            @{ Path = $codeownersPath; Label = "CODEOWNERS" }
        )) {
        if (-not (Test-Path -LiteralPath $pair.Path -PathType Leaf)) {
            throw "Missing $($pair.Label) at '$($pair.Path)'."
        }
    }

    $sourceProvDoc = Get-Content -LiteralPath $sourceProvDocPath -Raw
    $branchProtectionDoc = Get-Content -LiteralPath $branchProtectionDocPath -Raw

    if ($sourceProvDoc -notmatch 'Require signed commits') {
        throw "docs/ops/source-provenance.md must document Require signed commits."
    }
    if ($sourceProvDoc -notmatch 'scripts/branch-protection-check\.ps1') {
        throw "docs/ops/source-provenance.md must reference scripts/branch-protection-check.ps1."
    }
    if ($sourceProvDoc -notmatch '-PolicyOnly') {
        throw "docs/ops/source-provenance.md must document branch-protection-check.ps1 -PolicyOnly."
    }
    if ($sourceProvDoc -notmatch 'NOT_VERIFIABLE_IN_REPO') {
        throw "docs/ops/source-provenance.md must include NOT_VERIFIABLE_IN_REPO human org rows."
    }
    if ($branchProtectionDoc -notmatch 'source-provenance\.md') {
        throw "docs/ops/branch-protection.md must cross-link docs/ops/source-provenance.md."
    }
    if ($branchProtectionDoc -notmatch 'Require signed commits') {
        throw "docs/ops/branch-protection.md must document Require signed commits."
    }

    Write-Host "Source provenance policy OK (docs + CODEOWNERS anchors; no live Settings claim)."
}

if ($PolicyOnly) {
    Write-Host "Branch protection check (PolicyOnly — C06 L59 hermetic policy hook)"
    Assert-SourceProvenancePolicy
    Write-Host "PolicyOnly: skipping GitHub API branch protection query."
    exit 0
}

function Write-Skip {
    param([string]$Reason)
    Write-Host "SKIP: $Reason"
    Write-Host "Branch protection remains a maintainer Settings control; see docs/ops/branch-protection.md."
    exit 0
}

function Write-Check {
    param([string]$Label, [bool]$Ok)
    $Mark = if ($Ok) { "PASS" } else { "FAIL" }
    Write-Host "  [$Mark] $Label"
}

# Resolve owner/repo from gh if caller left the default and we are inside a clone.
if ($Repo -eq "KooshaPari/SessionLedger") {
    $Detected = $null
    try {
        $Detected = (& gh repo view --json nameWithOwner -q .nameWithOwner 2>$null)
    }
    catch {
        $Detected = $null
    }
    if (-not [string]::IsNullOrWhiteSpace($Detected)) {
        $Repo = $Detected.Trim()
    }
}

Write-Host "Branch protection check for $Repo ($Branch)"

$Gh = Get-Command gh -ErrorAction SilentlyContinue
if (-not $Gh) {
    Write-Skip "gh CLI not found"
}

# Prefer an explicit token; otherwise rely on `gh auth` session.
$HasToken = -not [string]::IsNullOrWhiteSpace($env:GH_TOKEN) `
    -or -not [string]::IsNullOrWhiteSpace($env:GITHUB_TOKEN)
if (-not $HasToken) {
    $AuthStatus = (& gh auth status 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) {
        Write-Skip "no GH_TOKEN/GITHUB_TOKEN and gh is not authenticated"
    }
    Write-Host "Using gh auth session (no GH_TOKEN/GITHUB_TOKEN in environment)."
}
else {
    Write-Host "Using GH_TOKEN/GITHUB_TOKEN from environment."
}

$ApiPath = "repos/$Repo/branches/$Branch/protection"
$Raw = $null
try {
    $Raw = & gh api $ApiPath 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ($Raw | Out-String)
    }
}
catch {
    $Msg = ($_ | Out-String).Trim()
    if ($Msg -match 'Branch not protected|HTTP 404|Not Found') {
        Write-Host "WARN: GitHub reports branch '$Branch' is not protected (or rule is invisible)."
        if ($Strict) {
            Write-Host "Strict mode: enable Settings -> Branches protection for '$Branch'."
            exit 1
        }
        Write-Skip "branch not protected / API 404 (best-effort)"
    }
    if ($Msg -match 'Must have admin rights|HTTP 403|Resource not accessible|Bad credentials|HTTP 401') {
        Write-Skip "gh api lacks admin (or token) scope to read branch protection"
    }
    Write-Skip "gh api failed: $Msg"
}

try {
    $Protection = $Raw | ConvertFrom-Json
}
catch {
    Write-Skip "could not parse branch protection JSON"
}

$RequiredSignatures = $false
if ($null -ne $Protection.required_signatures) {
    # Classic API may return { enabled: true } or a bare bool depending on endpoint shape.
    if ($Protection.required_signatures -is [bool]) {
        $RequiredSignatures = [bool]$Protection.required_signatures
    }
    elseif ($null -ne $Protection.required_signatures.enabled) {
        $RequiredSignatures = [bool]$Protection.required_signatures.enabled
    }
}

# Cross-check dedicated signatures endpoint when classic payload is ambiguous.
if (-not $RequiredSignatures) {
    try {
        $SigRaw = & gh api "repos/$Repo/branches/$Branch/protection/required_signatures" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $Sig = $SigRaw | ConvertFrom-Json
            if ($null -ne $Sig.enabled) {
                $RequiredSignatures = [bool]$Sig.enabled
            }
        }
    }
    catch {
        # ignore; classic payload already inspected
    }
}

$RequirePr = $null -ne $Protection.required_pull_request_reviews
$EnforceAdmins = $false
if ($null -ne $Protection.enforce_admins) {
    if ($Protection.enforce_admins -is [bool]) {
        $EnforceAdmins = [bool]$Protection.enforce_admins
    }
    elseif ($null -ne $Protection.enforce_admins.enabled) {
        $EnforceAdmins = [bool]$Protection.enforce_admins.enabled
    }
}

$RequiredChecks = $false
if ($null -ne $Protection.required_status_checks) {
    $Contexts = @()
    if ($null -ne $Protection.required_status_checks.contexts) {
        $Contexts = @($Protection.required_status_checks.contexts)
    }
    $Checks = @()
    if ($null -ne $Protection.required_status_checks.checks) {
        $Checks = @($Protection.required_status_checks.checks)
    }
    $RequiredChecks = ($Contexts.Count -gt 0) -or ($Checks.Count -gt 0)
}

Write-Host "API report:"
Write-Check "Require signed commits (required_signatures)" $RequiredSignatures
Write-Check "Require a pull request before merging" $RequirePr
Write-Check "Do not allow bypassing the above settings (enforce_admins)" $EnforceAdmins
Write-Check "Require status checks to pass (optional)" $RequiredChecks

$CoreOk = $RequiredSignatures -and $RequirePr
if ($CoreOk) {
    Write-Host "Branch protection machine-verify: PASS (core controls present)."
    if (-not $EnforceAdmins) {
        Write-Host "NOTE: enforce_admins is off; admins may bypass (recommended on for production)."
    }
    exit 0
}

Write-Host "Branch protection machine-verify: incomplete core controls."
if ($Strict) {
    Write-Host "Strict mode failing. Enable required signatures + PR reviews on '$Branch'."
    exit 1
}

Write-Host "Soft exit 0 (best-effort). Maintainers: docs/ops/branch-protection.md."
exit 0
