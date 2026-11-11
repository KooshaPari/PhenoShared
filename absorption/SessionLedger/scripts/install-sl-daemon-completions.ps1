# Install committed sl-daemon shell completions from crates/sl-daemon/completions/.
#
# Usage:
#   pwsh -NoProfile -File scripts/install-sl-daemon-completions.ps1
#   pwsh -NoProfile -File scripts/install-sl-daemon-completions.ps1 -Shell powershell
#   pwsh -NoProfile -File scripts/install-sl-daemon-completions.ps1 -Shell all

[CmdletBinding()]
param(
    [ValidateSet('bash', 'zsh', 'fish', 'powershell', 'all')]
    [string]$Shell = 'powershell',

    [string]$RepoRoot = $env:SL_REPO_ROOT,

    [string]$CompletionsDir = $env:SL_COMPLETIONS_DIR
)

$ErrorActionPreference = 'Stop'

if (-not $RepoRoot) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    try {
        $RepoRoot = (git -C (Join-Path $scriptDir '..') rev-parse --show-toplevel 2>$null).Trim()
    } catch {
        $RepoRoot = $null
    }
    if (-not $RepoRoot) {
        $RepoRoot = (Resolve-Path (Join-Path $scriptDir '..')).Path
    }
}

$srcDir = Join-Path $RepoRoot 'crates/sl-daemon/completions'
if (-not (Test-Path -LiteralPath $srcDir)) {
    throw "completions directory not found: $srcDir"
}

function Install-CompletionFile {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )
    if (-not (Test-Path -LiteralPath $Source)) {
        throw "missing source completion file: $Source"
    }
    $destParent = Split-Path -Parent $Destination
    if (-not (Test-Path -LiteralPath $destParent)) {
        New-Item -ItemType Directory -Force -Path $destParent | Out-Null
    }
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    Write-Host "installed $Destination"
}

function Install-Bash {
    $destRoot = if ($CompletionsDir) { $CompletionsDir } else {
        $xdg = if ($env:XDG_DATA_HOME) { $env:XDG_DATA_HOME } else { Join-Path $HOME '.local/share' }
        Join-Path $xdg 'bash-completion/completions'
    }
    Install-CompletionFile (Join-Path $srcDir 'sl-daemon.bash') (Join-Path $destRoot 'sl-daemon')
}

function Install-Zsh {
    $destRoot = if ($CompletionsDir) { $CompletionsDir } else { Join-Path $HOME '.zsh/completions' }
    Install-CompletionFile (Join-Path $srcDir '_sl-daemon') (Join-Path $destRoot '_sl-daemon')
    Write-Host "note: ensure fpath includes $destRoot and run: autoload -Uz compinit && compinit"
}

function Install-Fish {
    $destRoot = if ($CompletionsDir) { $CompletionsDir } else { Join-Path $HOME '.config/fish/completions' }
    Install-CompletionFile (Join-Path $srcDir 'sl-daemon.fish') (Join-Path $destRoot 'sl-daemon.fish')
}

function Install-PowerShellCompletion {
    $destRoot = if ($CompletionsDir) {
        $CompletionsDir
    } elseif ($PROFILE) {
        Split-Path -Parent $PROFILE
    } else {
        Join-Path $HOME 'Documents/PowerShell'
    }
    $dest = Join-Path $destRoot 'sl-daemon.ps1'
    Install-CompletionFile (Join-Path $srcDir 'sl-daemon.ps1') $dest
    Write-Host "note: add to your PowerShell profile: . '$dest'"
}

switch ($Shell) {
    'bash' { Install-Bash }
    'zsh' { Install-Zsh }
    'fish' { Install-Fish }
    'powershell' { Install-PowerShellCompletion }
    'all' {
        Install-Bash
        Install-Zsh
        Install-Fish
        Install-PowerShellCompletion
    }
}
