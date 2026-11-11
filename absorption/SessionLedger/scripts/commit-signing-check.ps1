<#
.SYNOPSIS
  Verify GPG/SSH commit signatures on main and optional branch-protection checklist.

.DESCRIPTION
  Reads commit object headers via bounded line-scanner (no unbounded git cat-file
  buffers or multiline regex over whole objects). Classifies gpg/ssh/unsigned.

.PARAMETER SelfCheck
  Hermetic policy anchor check + classification fixtures. No signed main required.

.EXAMPLE
  pwsh ./scripts/commit-signing-check.ps1 -Ref main -Count 30
  pwsh ./scripts/commit-signing-check.ps1 -SelfCheck
#>
[CmdletBinding()]
param(
    [string]$Ref = "main",
    [int]$Count = 30,
    [switch]$Strict,
    [switch]$BranchProtectionChecklist,
    [switch]$SelfCheck,
    [string]$Repo = "KooshaPari/SessionLedger",
    [int]$MaxCommitObjectBytes = 1048576,
    [int]$MaxHeaderLines = 256
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

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

function Get-CommitHeaderLines {
    param(
        [Parameter(Mandatory = $true)][string]$Sha,
        [int]$ObjectByteCap = 1048576,
        [int]$HeaderLineCap = 256
    )

    $sizeRaw = (& git cat-file -s $Sha 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($sizeRaw)) {
        return $null
    }
    if ($sizeRaw -notmatch '^\d+$') {
        throw "Unexpected git cat-file -s output for ${Sha}: $sizeRaw"
    }
    $objectSize = [long]::Parse($sizeRaw)
    if ($objectSize -gt $ObjectByteCap) {
        throw "Commit object $Sha size $objectSize exceeds cap $ObjectByteCap bytes"
    }

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "git"
    $psi.Arguments = "cat-file -p $Sha"
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $proc = [System.Diagnostics.Process]::Start($psi)
    if (-not $proc) {
        throw "Failed to start git cat-file -p $Sha"
    }

    $lines = [System.Collections.Generic.List[string]]::new()
    $bytesRead = 0
    try {
        while ($true) {
            $line = $proc.StandardOutput.ReadLine()
            if ($null -eq $line) {
                break
            }
            $bytesRead += [System.Text.Encoding]::UTF8.GetByteCount($line) + 1
            if ($bytesRead -gt $ObjectByteCap) {
                throw "Commit object $Sha exceeded byte cap while streaming header"
            }
            if ([string]::IsNullOrWhiteSpace($line)) {
                break
            }
            $lines.Add($line)
            if ($lines.Count -gt $HeaderLineCap) {
                throw "Commit object $Sha header exceeds $HeaderLineCap lines"
            }
        }
    }
    finally {
        if (-not $proc.HasExited) {
            $proc.Kill()
        }
        $proc.Dispose()
    }

    if ($proc.ExitCode -ne 0 -and $lines.Count -eq 0) {
        return $null
    }

    return ,@($lines.ToArray())
}

function Get-CommitSignatureKindFromHeader {
    param([string[]]$HeaderLines)

    if (-not $HeaderLines -or $HeaderLines.Count -eq 0) {
        return "missing"
    }

    $hasGpgsig = $false
    $joined = [string]::Join("`n", $HeaderLines)
    foreach ($line in $HeaderLines) {
        if ($line.StartsWith("gpgsig ")) {
            $hasGpgsig = $true
            break
        }
    }
    if (-not $hasGpgsig) {
        return "unsigned"
    }
    if ($joined.Contains("BEGIN SSH SIGNATURE")) {
        return "ssh"
    }
    if ($joined.Contains("BEGIN PGP SIGNATURE")) {
        return "gpg"
    }
    return "malformed"
}

function Get-CommitSignatureKind {
    param(
        [string]$Sha,
        [int]$ObjectByteCap,
        [int]$HeaderLineCap
    )
    $header = Get-CommitHeaderLines -Sha $Sha -ObjectByteCap $ObjectByteCap -HeaderLineCap $HeaderLineCap
    if ($null -eq $header) {
        return "missing"
    }
    return Get-CommitSignatureKindFromHeader -HeaderLines $header
}

function Test-CommitVerifier {
    param([string]$Sha)
    $Output = (& git verify-commit $Sha 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -eq 0) {
        return @{ Ok = $true; Detail = $Output }
    }
    if ($Output -match 'No signature') {
        return @{ Ok = $false; Detail = "no signature" }
    }
    if ($Output -match 'gpg:\s+Signature made|Good signature|not certified|Can''t check signature|no public key') {
        return @{ Ok = $true; Detail = $Output }
    }
    return @{ Ok = $false; Detail = $Output }
}

function Write-ChecklistItem {
    param([string]$Text, [bool]$Done = $false)
    $Mark = if ($Done) { "[x]" } else { "[ ]" }
    Write-Host "$Mark $Text"
}

function Resolve-GitRef {
    param(
        [string]$RefName,
        [int]$FetchDepth
    )

    $Candidates = @($RefName)
    if ($RefName -eq "main") {
        $Candidates += "origin/main"
    }

    foreach ($Candidate in $Candidates) {
        & git rev-parse --verify "$Candidate^{commit}" *> $null
        if ($LASTEXITCODE -eq 0) {
            return $Candidate
        }
    }

    if ($RefName -eq "main") {
        Write-Host "Local main not found; fetching origin/main (depth $FetchDepth)..."
        & git fetch --no-tags --depth $FetchDepth origin main 2>&1 | Out-Host
        if ($LASTEXITCODE -eq 0) {
            & git rev-parse --verify "origin/main^{commit}" *> $null
            if ($LASTEXITCODE -eq 0) {
                return "origin/main"
            }
        }
    }

    throw "Ref not found: $RefName (tried: $($Candidates -join ', '))"
}

function Invoke-BranchProtectionChecklist {
    $Items = @(
        "Require signed commits on branch main",
        "Require a pull request before merging (recommended)",
        "Do not allow bypassing the above settings (recommended)"
    )

    Write-Host "Branch protection checklist for $Repo (main):"
    foreach ($Item in $Items) {
        Write-ChecklistItem $Item
    }

    $Gh = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $Gh) {
        Write-Host ""
        Write-Host "WARN: gh CLI not found; branch protection is not machine-verifiable in OSS."
        Write-Host "See docs/ops/commit-signing.md for manual Settings -> Branches steps."
        return 0
    }

    try {
        $Json = & gh api "repos/$Repo/branches/main/protection" 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw ($Json | Out-String)
        }
        $Protection = $Json | ConvertFrom-Json
        $Signed = [bool]$Protection.required_signatures
        Write-Host ""
        Write-ChecklistItem "Require signed commits on branch main" $Signed
        if (-not $Signed) {
            Write-Host "WARN: GitHub API reports required_signatures=false (or unset)."
            Write-Host "Enable 'Require signed commits' in repository branch protection."
            Write-Host "Exiting soft (docs-only) because OSS CI cannot enforce admin settings."
            return 0
        }
        Write-Host "Branch protection reports required_signatures=true."
        return 0
    }
    catch {
        Write-Host ""
        Write-Host "WARN: Could not query branch protection via gh api (admin scope required)."
        Write-Host $_.Exception.Message
        Write-Host "Exiting soft (docs-only). See docs/ops/commit-signing.md."
        return 0
    }
}

function Test-SignatureClassificationFixtures {
    $cases = @(
        @{
            Name = "unsigned header"
            Header = @("tree abc", "parent def", "author A <a@b.c> 0 +0000", "committer A <a@b.c> 0 +0000")
            Expected = "unsigned"
        },
        @{
            Name = "gpg header"
            Header = @(
                "tree abc",
                "gpgsig -----BEGIN PGP SIGNATURE-----",
                " ",
                " -----END PGP SIGNATURE-----"
            )
            Expected = "gpg"
        },
        @{
            Name = "ssh header"
            Header = @(
                "tree abc",
                "gpgsig -----BEGIN SSH SIGNATURE-----",
                " -----END SSH SIGNATURE-----"
            )
            Expected = "ssh"
        },
        @{
            Name = "malformed gpgsig"
            Header = @("tree abc", "gpgsig not-a-known-format")
            Expected = "malformed"
        }
    )

    foreach ($case in $cases) {
        $actual = Get-CommitSignatureKindFromHeader -HeaderLines $case.Header
        if ($actual -ne $case.Expected) {
            throw "Fixture '$($case.Name)' expected $($case.Expected) got $actual"
        }
        [void](Write-Check -Label "fixture: $($case.Name)" -Ok $true)
    }
}

function Invoke-SelfCheck {
    Write-Host "Commit signing check policy (C04 L34)"
    Write-Host "Mode: SelfCheck (bounded header scanner + fixtures; no signed main required)"

    $docPath = Join-Path $RepoRoot "docs/ops/commit-signing.md"
    $workflowPath = Join-Path $RepoRoot ".github/workflows/commit-signing.yml"
    $selfPath = Join-Path $RepoRoot "scripts/commit-signing-check.ps1"

    Assert-File -Path $docPath -Label "commit-signing doc"
    Assert-File -Path $workflowPath -Label "commit-signing workflow"
    Assert-File -Path $selfPath -Label "commit-signing check script"

    $doc = Get-Content -LiteralPath $docPath -Raw
    $workflow = Get-Content -LiteralPath $workflowPath -Raw
    $selfText = Get-Content -LiteralPath $selfPath -Raw

    Assert-Contains -Doc $doc -Needle "scripts/commit-signing-check.ps1" `
        -Label "script reference" -Context "docs/ops/commit-signing.md"
    Assert-Contains -Doc $doc -Needle "-SelfCheck" `
        -Label "SelfCheck invocation" -Context "docs/ops/commit-signing.md"
    Assert-Contains -Doc $workflow -Needle "commit-signing-check.ps1" `
        -Label "workflow script invocation" -Context ".github/workflows/commit-signing.yml"

    if ($selfText -match '\(\?ms\)\^') {
        throw "commit-signing-check.ps1 must not use multiline (?ms) regex over commit objects."
    }
    [void](Write-Check -Label "no multiline regex anchors in script" -Ok $true)

    if ($selfText -notmatch 'MaxCommitObjectBytes') {
        throw "commit-signing-check.ps1 missing MaxCommitObjectBytes cap."
    }
    [void](Write-Check -Label "MaxCommitObjectBytes cap present" -Ok $true)

    if ($selfText -notmatch 'Get-CommitHeaderLines') {
        throw "commit-signing-check.ps1 missing bounded header line scanner."
    }
    [void](Write-Check -Label "bounded header line scanner present" -Ok $true)

    Write-Host "Classification fixtures:"
    Test-SignatureClassificationFixtures

    Write-Host "Commit signing check SelfCheck passed (C04 L34 bounded git cat-file header scan; branch protection remains soft)."
    exit 0
}

if ($SelfCheck) {
    Invoke-SelfCheck
}

Push-Location $RepoRoot
try {
    if ($BranchProtectionChecklist) {
        exit (Invoke-BranchProtectionChecklist)
    }

    $ResolvedRef = Resolve-GitRef -RefName $Ref -FetchDepth ([Math]::Max($Count, 30))
    if ($ResolvedRef -ne $Ref) {
        Write-Host "Resolved ref '$Ref' -> '$ResolvedRef'"
    }

    $Tip = (& git rev-parse "$ResolvedRef^{commit}").Trim()
    $Shas = @(& git rev-list -n $Count $ResolvedRef)
    if ($Shas.Count -eq 0) {
        throw "No commits found for ref $Ref"
    }

    $Stats = @{
        gpg       = 0
        ssh       = 0
        unsigned  = 0
        malformed = 0
    }
    $Problems = [System.Collections.Generic.List[string]]::new()

    foreach ($Sha in $Shas) {
        $Kind = Get-CommitSignatureKind -Sha $Sha -ObjectByteCap $MaxCommitObjectBytes -HeaderLineCap $MaxHeaderLines
        if ($Stats.ContainsKey($Kind)) {
            $Stats[$Kind]++
        }
        else {
            $Stats.malformed++
        }

        if ($Kind -eq "malformed") {
            $Problems.Add("$Sha has gpgsig block but unrecognized signature format")
            continue
        }
        if ($Kind -in @("gpg", "ssh") -and $Sha -eq $Tip) {
            $Verify = Test-CommitVerifier $Sha
            if (-not $Verify.Ok) {
                $Problems.Add("$Sha ($Kind) verify-commit failed: $($Verify.Detail)")
            }
        }
        if ($Strict -and $Kind -eq "unsigned") {
            $Subject = (& git show -s --format=%s $Sha).Trim()
            $Problems.Add("$Sha unsigned in strict window: $Subject")
        }
    }

    $TipKind = Get-CommitSignatureKind -Sha $Tip -ObjectByteCap $MaxCommitObjectBytes -HeaderLineCap $MaxHeaderLines
    Write-Host "Commit signing report for $ResolvedRef (tip $Tip, last $($Shas.Count) commits)"
    Write-Host "  gpg:       $($Stats.gpg)"
    Write-Host "  ssh:       $($Stats.ssh)"
    Write-Host "  unsigned:  $($Stats.unsigned)"
    Write-Host "  malformed: $($Stats.malformed)"
    Write-Host "  tip:       $TipKind"

    if ($TipKind -notin @("gpg", "ssh")) {
        $Problems.Add("Tip commit $Tip on $ResolvedRef is not GPG/SSH signed ($TipKind)")
    }

    if ($Problems.Count -gt 0) {
        Write-Host ""
        Write-Host "Findings:"
        foreach ($Problem in $Problems) {
            Write-Host "  - $Problem"
        }
        exit 1
    }

    Write-Host ""
    Write-Host "Commit signing check passed for $ResolvedRef."
    exit 0
}
finally {
    Pop-Location
}
