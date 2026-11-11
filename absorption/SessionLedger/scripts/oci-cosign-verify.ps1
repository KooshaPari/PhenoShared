<#
.SYNOPSIS
  Verify-on-deploy check for the best-effort GHCR sl-daemon OCI image.

.DESCRIPTION
  Resolves (or accepts) an image digest, then runs keyless cosign verify against
  the SessionLedger release.yml tag identity. Optionally runs
  `gh attestation verify` for GitHub OCI provenance.

  This script is for deploy-time trust checks. Release CI runs the same verify
  on the canonical repository after sign/attest. Forks skip the `oci-image` job
  when GHCR/OIDC credentials are unavailable.

  Exit codes:
    0 — cosign verify succeeded (and attestation when -RequireAttestation)
    1 — verification failed or required tools/digest missing
    2 — usage / parameter error

.PARAMETER Image
  Registry/repo reference without digest. Default: ghcr.io/kooshapari/sl-daemon

.PARAMETER Tag
  Release tag (for example v0.1.0). Used for certificate-identity and optional
  digest resolution when -Digest is omitted.

.PARAMETER Digest
  Image digest (sha256:…). Prefer this over tag-only pulls for deploy.

.PARAMETER CertificateIdentity
  Override the expected Fulcio certificate identity. Default binds to
  release.yml at refs/tags/<Tag>.

.PARAMETER CertificateOidcIssuer
  Expected OIDC issuer. Default: https://token.actions.githubusercontent.com

.PARAMETER Repo
  GitHub repo for `gh attestation verify`. Default: KooshaPari/SessionLedger

.PARAMETER SkipAttestation
  Skip the optional `gh attestation verify` step (cosign-only).

.PARAMETER RequireAttestation
  Fail if GitHub OCI attestation is missing or unverifiable. Implies attestation
  is attempted (overrides -SkipAttestation).

.PARAMETER AllowUnsigned
  When set, a missing signature prints a warning and exits 0. Use only for
  dry-runs; do not use for production verify-on-deploy.

.PARAMETER SelfCheck
  Hermetic policy anchor check (docs + release.yml + dry-run path). No registry
  access required; cosign dry-run runs only when cosign is on PATH.

.EXAMPLE
  pwsh ./scripts/oci-cosign-verify.ps1 -SelfCheck
  pwsh ./scripts/oci-cosign-verify.ps1 -Tag v0.1.0 -Digest sha256:abc…

.EXAMPLE
  pwsh ./scripts/oci-cosign-verify.ps1 -Tag v0.1.0 -RequireAttestation
#>
[CmdletBinding()]
param(
    [string]$Image = "ghcr.io/kooshapari/sl-daemon",

    [string]$Tag = "",

    [string]$Digest = "",

    [string]$CertificateIdentity = "",

    [string]$CertificateOidcIssuer = "https://token.actions.githubusercontent.com",

    [string]$Repo = "KooshaPari/SessionLedger",

    [switch]$SkipAttestation,

    [switch]$RequireAttestation,

    [switch]$AllowUnsigned,

    [switch]$SelfCheck
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Write-Check {
    param([string]$Label, [bool]$Ok)
    $mark = if ($Ok) { "PASS" } else { "FAIL" }
    Write-Host "  [$mark] $Label"
    return $Ok
}

function Assert-File {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Label
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing $Label at '$Path'."
    }
}

function Assert-Contains {
    param(
        [Parameter(Mandatory = $true)][string]$Doc,
        [Parameter(Mandatory = $true)][string]$Needle,
        [Parameter(Mandatory = $true)][string]$Label,
        [string]$Context = "document"
    )
    $ok = $Doc.Contains($Needle)
    [void](Write-Check -Label $Label -Ok $ok)
    if (-not $ok) {
        throw "$Context missing required anchor: '$Needle'"
    }
}

function Test-CommandAvailable {
    param([Parameter(Mandatory = $true)][string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-YamlJobBlock {
    param(
        [Parameter(Mandatory = $true)][string]$Document,
        [Parameter(Mandatory = $true)][string]$JobName
    )

    $lines = $Document -split "\r?\n"
    $start = -1
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -eq "  ${JobName}:") {
            $start = $index
            break
        }
    }
    if ($start -lt 0) {
        throw "Workflow missing '$JobName' job definition."
    }

    $end = $lines.Count
    for ($index = $start + 1; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match '^  [A-Za-z0-9_-]+:\s*$') {
            $end = $index
            break
        }
    }
    return ($lines[$start..($end - 1)] -join "`n")
}

function Get-YamlStepBlock {
    param(
        [Parameter(Mandatory = $true)][string]$Document,
        [Parameter(Mandatory = $true)][string]$StepName,
        [ValidateRange(1, 32)]
        [int]$Indent = 6
    )

    $stepLine = (" " * $Indent) + "- name: $StepName"
    $lines = $Document -split "\r?\n"
    $start = -1
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -eq $stepLine) {
            $start = $index
            break
        }
    }
    if ($start -lt 0) {
        throw "Workflow missing step '$StepName'."
    }

    $nextStepPattern = '^ {' + $Indent + '}- name:'
    $end = $lines.Count
    for ($index = $start + 1; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match $nextStepPattern) {
            $end = $index
            break
        }
    }
    return ($lines[$start..($end - 1)] -join "`n")
}

if ($SelfCheck) {
    Write-Host "OCI cosign verify policy check (C06 L56)"
    Write-Host "Mode: SelfCheck (docs + release.yml anchors; optional cosign dry-run)"

    $distDoc = Join-Path $repoRoot "docs/ops/distribution.md"
    $releaseWorkflow = Join-Path $repoRoot ".github/workflows/release.yml"
    $packagingReadme = Join-Path $repoRoot "packaging/README.md"
    $selfScript = Join-Path $repoRoot "scripts/oci-cosign-verify.ps1"

    Assert-File -Path $distDoc -Label "distribution doc"
    Assert-File -Path $releaseWorkflow -Label "release workflow"
    Assert-File -Path $packagingReadme -Label "packaging README"
    Assert-File -Path $selfScript -Label "oci-cosign-verify script"

    $dist = Get-Content -LiteralPath $distDoc -Raw
    $release = Get-Content -LiteralPath $releaseWorkflow -Raw
    $packaging = Get-Content -LiteralPath $packagingReadme -Raw
    $selfText = Get-Content -LiteralPath $selfScript -Raw

    Write-Host "distribution.md anchors:"
    Assert-Contains -Doc $dist -Needle "OCI cosign policy matrix (unconditional vs credential-gated)" `
        -Label "unconditional vs credential-gated matrix" -Context "docs/ops/distribution.md"
    Assert-Contains -Doc $dist -Needle "Canonical ``KooshaPari/SessionLedger`` ``v*`` tag | **Required, release-blocking**" `
        -Label "canonical unconditional row" -Context "docs/ops/distribution.md"
    Assert-Contains -Doc $dist -Needle "Fork ``v*`` tag push | Skipped with explicit reason" `
        -Label "fork credential-gated row" -Context "docs/ops/distribution.md"
    Assert-Contains -Doc $dist -Needle "oci-cosign-verify.ps1 -SelfCheck" `
        -Label "SelfCheck invocation" -Context "docs/ops/distribution.md"

    Write-Host "release.yml anchors:"
    if ($release -notmatch '(?m)^\s*oci-image:\s*$') {
        throw "release.yml missing oci-image job."
    }
    [void](Write-Check -Label "oci-image job present" -Ok $true)

    if ($release -notmatch 'detect OCI release gate') {
        throw "release.yml missing detect OCI release gate step."
    }
    [void](Write-Check -Label "detect OCI release gate step" -Ok $true)

    if ($release -notmatch 'name:\s*oci-cosign-verify \(blocking\)') {
        throw "release.yml missing blocking oci-cosign-verify step."
    }
    [void](Write-Check -Label "blocking oci-cosign-verify step" -Ok $true)

    $ociImageBlock = Get-YamlJobBlock -Document $release -JobName "oci-image"
    $verifyBlock = Get-YamlStepBlock -Document $ociImageBlock -StepName "oci-cosign-verify (blocking)"
    if ($verifyBlock -match 'continue-on-error:\s*true') {
        throw "oci-cosign-verify step must not set continue-on-error: true."
    }
    if ($verifyBlock -notmatch 'continue-on-error:\s*false') {
        throw "oci-cosign-verify step must document continue-on-error: false."
    }
    [void](Write-Check -Label "oci-cosign-verify continue-on-error: false" -Ok $true)

    if ($release -notmatch '(?s)needs:.*?\boci-image\b') {
        throw "release.yml release job should depend on oci-image."
    }
    [void](Write-Check -Label "release job needs oci-image" -Ok $true)

    Write-Host "packaging/README.md anchors:"
    Assert-Contains -Doc $packaging -Needle "oci-cosign-verify.ps1" `
        -Label "oci-cosign-verify cross-link" -Context "packaging/README.md"
    Assert-Contains -Doc $packaging -Needle "unconditional" `
        -Label "unconditional OCI policy note" -Context "packaging/README.md"

    Assert-Contains -Doc $selfText -Needle "AllowUnsigned set: exiting 0 despite failed cosign verify" `
        -Label "AllowUnsigned dry-run anchor" -Context "scripts/oci-cosign-verify.ps1"

    Write-Host "Dry-run path (AllowUnsigned + policy dry-run; no registry):"
    $dryDigest = "sha256:$('0' * 64)"
    $prevDryRun = $env:SL_OCI_VERIFY_POLICY_DRYRUN
    $env:SL_OCI_VERIFY_POLICY_DRYRUN = "1"
    try {
        & $PSCommandPath -Tag "v0.0.0-selfcheck" -Digest $dryDigest -AllowUnsigned
        if ($LASTEXITCODE -ne 0) {
            throw "AllowUnsigned dry-run path exited $LASTEXITCODE (expected 0)."
        }
    } finally {
        if ($null -eq $prevDryRun) {
            Remove-Item Env:SL_OCI_VERIFY_POLICY_DRYRUN -ErrorAction SilentlyContinue
        } else {
            $env:SL_OCI_VERIFY_POLICY_DRYRUN = $prevDryRun
        }
    }
    [void](Write-Check -Label "AllowUnsigned dry-run exits 0" -Ok $true)

    Write-Host "OCI cosign verify SelfCheck passed (C06 L56 unconditional release-blocking OCI on canonical tags)."
    exit 0
}

function Fail {
    param(
        [Parameter(Mandatory = $true)][int]$Code,
        [Parameter(Mandatory = $true)][string]$Message
    )
    Write-Host $Message -ForegroundColor Red
    exit $Code
}

function Write-UsageHint {
    Write-Host @"
Usage:
  pwsh ./scripts/oci-cosign-verify.ps1 -Tag <vX.Y.Z> [-Digest sha256:…] [-RequireAttestation]

Requires: cosign on PATH. Optional: crane (digest resolve), gh (attestation).
Portable Releases stay valid without OCI signatures; use those when verify fails.
"@
}

if ([string]::IsNullOrWhiteSpace($Tag)) {
    Write-UsageHint
    Fail -Code 2 -Message "Tag is required (for example v0.1.0)."
}

if ($Tag -notmatch '^v') {
    Write-Warning "Tag '$Tag' does not start with 'v'. Certificate identity still uses refs/tags/$Tag."
}

if ([string]::IsNullOrWhiteSpace($CertificateIdentity)) {
    $CertificateIdentity = "https://github.com/KooshaPari/SessionLedger/.github/workflows/release.yml@refs/tags/$Tag"
}

function Resolve-ImageDigest {
    param(
        [Parameter(Mandatory = $true)][string]$ImageRef,
        [Parameter(Mandatory = $true)][string]$ImageTag
    )

    $ref = "${ImageRef}:${ImageTag}"

    if (Test-CommandAvailable -Name "crane") {
        Write-Host "==> Resolving digest with crane: $ref"
        $resolved = (& crane digest $ref 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -eq 0 -and $resolved -match '^sha256:[0-9a-f]{64}$') {
            return $resolved
        }
        Write-Warning "crane digest failed for $ref (exit $LASTEXITCODE): $resolved"
    }

    if (Test-CommandAvailable -Name "cosign") {
        Write-Host "==> Resolving digest with cosign triangulate: $ref"
        $tri = (& cosign triangulate $ref 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -eq 0 -and $tri -match '@(sha256:[0-9a-f]{64})\s*$') {
            return $Matches[1]
        }
        # Some cosign versions print IMAGE@sha256:… on one line.
        if ($tri -match '(sha256:[0-9a-f]{64})') {
            return $Matches[1]
        }
        Write-Warning "cosign triangulate failed for $ref (exit $LASTEXITCODE): $tri"
    }

    return $null
}

$normalizedDigest = $Digest.Trim()
if (-not [string]::IsNullOrWhiteSpace($normalizedDigest)) {
    if ($normalizedDigest -notmatch '^sha256:[0-9a-f]{64}$') {
        Fail -Code 2 -Message "Digest must look like sha256:<64 hex chars>; got: $normalizedDigest"
    }
} else {
    $normalizedDigest = Resolve-ImageDigest -ImageRef $Image -ImageTag $Tag
    if ([string]::IsNullOrWhiteSpace($normalizedDigest)) {
        Fail -Code 1 -Message @"
Could not resolve image digest for ${Image}:${Tag}.
Pass -Digest sha256:… explicitly (from the Release Actions summary or crane digest),
or install crane/cosign with registry access.
"@
    }
    if ($normalizedDigest -notmatch '^sha256:[0-9a-f]{64}$') {
        Fail -Code 1 -Message "Resolved digest is invalid: $normalizedDigest"
    }
}

if (-not (Test-CommandAvailable -Name "cosign") -and $env:SL_OCI_VERIFY_POLICY_DRYRUN -ne "1") {
    Fail -Code 1 -Message "cosign is not on PATH. Install from https://docs.sigstore.dev/cosign/installation/"
}

$subject = "${Image}@${normalizedDigest}"
Write-Host "==> Verify-on-deploy subject: $subject"
Write-Host "    certificate-identity: $CertificateIdentity"
Write-Host "    certificate-oidc-issuer: $CertificateOidcIssuer"

$cosignArgs = @(
    "verify",
    "--certificate-identity", $CertificateIdentity,
    "--certificate-oidc-issuer", $CertificateOidcIssuer,
    $subject
)

Write-Host "==> cosign $($cosignArgs -join ' ')"
if ($env:SL_OCI_VERIFY_POLICY_DRYRUN -eq "1") {
  if ($AllowUnsigned) {
    Write-Warning @"
Policy dry-run: simulating failed cosign verify for $subject with AllowUnsigned.
Do not set SL_OCI_VERIFY_POLICY_DRYRUN outside SelfCheck.
"@
    Write-Warning "AllowUnsigned set: exiting 0 despite failed cosign verify (dry-run only)."
    exit 0
  }
  Fail -Code 1 -Message "Policy dry-run without AllowUnsigned would fail closed for $subject."
}
& cosign @cosignArgs
$cosignExit = $LASTEXITCODE

if ($cosignExit -ne 0) {
    $msg = @"
cosign verify failed for $subject (exit $cosignExit).
Treat OCI provenance as unavailable for this tag. Fall back to the portable
sl-daemon archive + SHA256SUMS path, or rebuild from crates/sl-daemon/Containerfile.
Unsigned portable Releases remain valid; do not treat a missing OCI signature as success.
"@
    if ($AllowUnsigned) {
        Write-Warning $msg
        Write-Warning "AllowUnsigned set: exiting 0 despite failed cosign verify (dry-run only)."
        exit 0
    }
    Fail -Code 1 -Message $msg
}

Write-Host "cosign verify: OK"

$runAttestation = $RequireAttestation -or (-not $SkipAttestation)
if ($runAttestation) {
    if (-not (Test-CommandAvailable -Name "gh")) {
        if ($RequireAttestation) {
            Fail -Code 1 -Message "gh is required for -RequireAttestation but is not on PATH."
        }
        Write-Warning "gh not on PATH; skipping OCI attestation verify. Pass -RequireAttestation to make this fatal."
    } else {
        $ociUri = "oci://${subject}"
        Write-Host "==> gh attestation verify $ociUri --repo $Repo"
        & gh attestation verify $ociUri --repo $Repo
        $attestExit = $LASTEXITCODE
        if ($attestExit -ne 0) {
            $attestMsg = "gh attestation verify failed for $ociUri (exit $attestExit)."
            if ($RequireAttestation) {
                Fail -Code 1 -Message "$attestMsg Cosign succeeded, but attestation is required."
            }
            Write-Warning "$attestMsg Cosign succeeded; attestation remains best-effort."
        } else {
            Write-Host "gh attestation verify: OK"
        }
    }
} else {
    Write-Host "Skipping gh attestation verify (-SkipAttestation)."
}

Write-Host "OCI verify-on-deploy passed for $subject"
exit 0
