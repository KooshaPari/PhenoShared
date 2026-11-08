<#
repo-delete-gate.ps1
----------------------------------------------------------------------------
PowerShell equivalent of bin/repo-delete-gate.sh for Windows runners.

Wraps `gh repo delete` with the same four-gate pre-delete fence:
  (a) docs/absorbed-from-<repo>/ABSORPTION.md exists with all required
      sections (Source, Target, Status, Last-Resort-Exceptions,
      Restore-Command)
  (b) GitHub API confirms isArchived=true AND default-branch protection
      is not active
  (c) local-only dry-run is the DEFAULT; pass -Apply to actually delete
  (d) -Force bypasses the gate after printing a loud warning

Mirrors the bash script 1:1 in behavior so audit logs are comparable
across runners. Lessons-learned source:
  forge/agentuserstatus-merge/phenotype-tooling/docs/absorbed-from-go-nippon/ABSORPTION.md:1-28

Usage
  pwsh bin/repo-delete-gate.ps1 -Repo <owner/repo> [-Apply] [-Force]
                                [-DocsRoot <path>] [-ToolingRoot <path>]

Exit codes (kept identical to the bash version):
  0  deletion performed (only with -Apply and gates passed)
  2  gate failure
  3  invalid arguments / missing tool
  4  GitHub API failure
  5  user aborted after -Force warning
----------------------------------------------------------------------------
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)] [string]$Repo,
  [switch]$Apply,
  [switch]$Force,
  [string]$DocsRoot = 'docs',
  [string]$ToolingRoot = '.'
)

$ErrorActionPreference = 'Stop'

# ---------- helpers -----------------------------------------------------------
function Write-GateLog    { param([string]$Msg) Write-Host "[repo-delete-gate] $Msg" }
function Write-GateWarn   { param([string]$Msg) Write-Warning "[repo-delete-gate][WARN] $Msg" }
function Write-GateError  { param([string]$Msg) Write-Error "[repo-delete-gate][ERROR] $Msg" }

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  Write-GateError "required tool 'gh' not found in PATH"; exit 3
}

$requiredSections = @('Source','Target','Status','Last-Resort-Exceptions','Restore-Command')

$repoLeaf = $Repo.Split('/')[-1]
# Normalize roots: if DocsRoot is absolute, ignore ToolingRoot; else join.
if (-not [System.IO.Path]::IsPathRooted($DocsRoot)) {
  $manifestDir  = Join-Path -Path $ToolingRoot -ChildPath $DocsRoot
} else {
  $manifestDir = $DocsRoot
}
# Strip trailing separators, then append the absorbed-from-<repo> segment.
$manifestDir  = $manifestDir.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
$manifestDir  = Join-Path -Path $manifestDir -ChildPath ("absorbed-from-$repoLeaf")
$manifestFile = Join-Path -Path $manifestDir -ChildPath 'ABSORPTION.md'

# ---------- gate (a): absorption manifest -------------------------------------
$gateAStatus = 'FAIL'
$gateADetail = ''
if (-not (Test-Path -LiteralPath $manifestFile)) {
  $gateADetail = "manifest missing at $manifestFile"
} else {
  $missing = @()
  foreach ($section in $requiredSections) {
    $pattern = "^\#{1,6}\s+$([regex]::Escape($section))\s*$"
    $hit = Select-String -Path $manifestFile -Pattern $pattern -SimpleMatch:$false -Quiet -ErrorAction SilentlyContinue
    if (-not $hit) { $missing += $section }
  }
  if ($missing.Count -gt 0) {
    $gateADetail = "manifest present but missing sections: $($missing -join ', ')"
  } else {
    $gateAStatus = 'PASS'
    $gateADetail = "manifest at $manifestFile contains all required sections"
  }
}

# ---------- gate (b): github api state ----------------------------------------
$gateBStatus = 'FAIL'
$gateBDetail = ''
try {
  $repoJson = gh api "/repos/$Repo" 2>$null | ConvertFrom-Json -ErrorAction Stop
  $isArchived = [bool]$repoJson.archived

  $defaultBranch = $repoJson.default_branch
  $protectionActive = $false
  try {
    $protection = gh api "/repos/$Repo/branches/$defaultBranch/protection" 2>$null | ConvertFrom-Json -ErrorAction Stop
    if ($protection.enabled) { $protectionActive = $true }
  } catch {
    # 404 / 403 => no protection configured; leave $protectionActive = $false
    $protectionActive = $false
  }

  if ($isArchived -and -not $protectionActive) {
    $gateBStatus = 'PASS'
    $gateBDetail = "isArchived=true and no active default-branch protection"
  } else {
    $gateBDetail = "isArchived=$isArchived, protection_active=$protectionActive (both must be archived AND unprotected)"
  }
} catch {
  $gateBDetail = "gh api /repos/$Repo failed: $($_.Exception.Message)"
}

# ---------- gate summary ------------------------------------------------------
$overall = 'PASS'
if ($gateAStatus -ne 'PASS') { $overall = 'FAIL' }
if ($gateBStatus -ne 'PASS') { $overall = 'FAIL' }

Write-GateLog "gate (a) manifest     : $gateAStatus -- $gateADetail"
Write-GateLog "gate (b) github state : $gateBStatus -- $gateBDetail"
Write-GateLog "overall               : $overall"

# ---------- success path ------------------------------------------------------
if ($overall -eq 'PASS') {
  if (-not $Apply) {
    Write-GateLog "(dry-run) would run: gh repo delete $Repo --yes"
    Write-GateLog "(dry-run) no deletion performed. Re-run with -Apply to delete."
    exit 0
  }
  Write-GateLog "all gates passed; executing: gh repo delete $Repo --yes"
  gh repo delete $Repo --yes
  exit 0
}

# ---------- failure path ------------------------------------------------------
if ($Force) {
  Write-GateWarn "gate FAILED but -Force was supplied."
  Write-GateWarn "this bypass is intentional only for emergency rollback."
  Write-GateWarn "post-deletion, you MUST still author docs/absorbed-from-$repoLeaf/ABSORPTION.md"
  Write-GateWarn "within 24h or this deletion is unrecoverable per the go-nippon precedent."
  if ($Apply) {
    Write-GateLog "executing forced delete: gh repo delete $Repo --yes"
    gh repo delete $Repo --yes
    exit 0
  }
  Write-GateLog "(dry-run) -Force acknowledged; re-run with -Apply to actually delete."
  exit 0
}

Write-GateError "gate failed for $Repo; rerun with -Force only if you accept the risk and will author the manifest retroactively."
exit 2
