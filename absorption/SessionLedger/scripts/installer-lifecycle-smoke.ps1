[CmdletBinding()]
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$EvidencePath,
    [switch]$WindowsInstallLifecycle
)

$ErrorActionPreference = "Stop"

function Assert-Path {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Description
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing $Description at '$Path'."
    }
    Write-Output "ok: $Description"
}

function Assert-Contains {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Pattern,
        [Parameter(Mandatory = $true)][string]$Description
    )

    if (-not (Select-String -LiteralPath $Path -Pattern $Pattern -Quiet)) {
        throw "Missing $Description in '$Path'."
    }
    Write-Output "ok: $Description"
}

function Assert-Not-Path {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Description
    )

    if (Test-Path -LiteralPath $Path) {
        throw "Expected $Description to be absent at '$Path'."
    }
    Write-Output "ok: $Description absent"
}

function Wait-UntilAbsent {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Description,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (-not (Test-Path -LiteralPath $Path)) {
            Write-Output "ok: $Description absent"
            return
        }
        Start-Sleep -Seconds 1
    }

    throw "Timed out waiting for $Description to be absent at '$Path'."
}

function Join-RepoPath {
    param([Parameter(Mandatory = $true)][string[]]$Parts)
    $path = $ProjectRoot
    foreach ($part in $Parts) {
        $path = Join-Path $path $part
    }
    return $path
}

$script:EvidenceSteps = [System.Collections.Generic.List[object]]::new()

function Add-EvidenceStep {
    param(
        [Parameter(Mandatory = $true)][string]$Id,
        [Parameter(Mandatory = $true)][string]$Description,
        [Parameter(Mandatory = $true)][ValidateSet("pass", "fail", "skip")]
        [string]$Status,
        [string]$Detail
    )

    $script:EvidenceSteps.Add([ordered]@{
        id          = $Id
        description = $Description
        status      = $Status
        detail      = $Detail
        at          = (Get-Date).ToUniversalTime().ToString("o")
    })
}

function Write-CleanHostEvidence {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][ValidateSet("scaffold", "windows-unsigned-portable")]
        [string]$Mode,
        [Parameter(Mandatory = $true)][ValidateSet("pass", "fail")]
        [string]$Outcome
    )

    $evidence = [ordered]@{
        schema      = "sessionledger.clean-host-evidence.v1"
        mode        = $Mode
        outcome     = $Outcome
        unsigned    = $true
        authenticode = $false
        host        = [ordered]@{
            os        = if ($IsWindows -or $env:OS -eq "Windows_NT") { "windows" } else { "non-windows" }
            ci        = [bool]($env:GITHUB_ACTIONS -eq "true")
            runner    = $env:RUNNER_OS
            workflow  = $env:GITHUB_WORKFLOW
            run_id    = $env:GITHUB_RUN_ID
            run_url   = $env:GITHUB_SERVER_URL, $env:GITHUB_REPOSITORY, "actions/runs", $env:GITHUB_RUN_ID -join "/"
        }
        generatedAt = (Get-Date).ToUniversalTime().ToString("o")
        steps       = @($script:EvidenceSteps)
        notes       = @(
            "Unsigned portable install/uninstall smoke; does not prove Authenticode or MSI.",
            "User data is intentionally preserved by Uninstall.ps1; verify separately when testing data roots."
        )
    }

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    $evidence | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Path -Encoding utf8
    Write-Output "ok: clean-host evidence written to $Path"
}

function Get-ViewerVersion {
    $metadata = cargo metadata --manifest-path (Join-RepoPath @("Cargo.toml")) --no-deps --format-version 1 |
        ConvertFrom-Json
    $viewer = $metadata.packages | Where-Object { $_.name -eq "sl-viewer" } | Select-Object -First 1
    if (-not $viewer) {
        throw "Could not determine the sl-viewer version from cargo metadata."
    }
    return $viewer.version
}

function New-ViewerStubExe {
    param(
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [Parameter(Mandatory = $true)][string]$Version,
        [Parameter(Mandatory = $true)][string]$WorkRoot
    )

    $rustSource = Join-Path $WorkRoot "viewer_stub.rs"
    @"
fn main() {
    for arg in std::env::args().skip(1) {
        match arg.as_str() {
            "--version" | "-V" => {
                println!("sl-viewer $Version");
                return;
            }
            "--help" | "-h" => {
                println!("SessionLedger viewer stub for installer lifecycle smoke");
                return;
            }
            _ => {}
        }
    }
}
"@ | Set-Content -LiteralPath $rustSource -Encoding utf8

    & rustc $rustSource -o $OutputPath
    if ($LASTEXITCODE -ne 0) {
        throw "rustc failed to build the viewer stub executable."
    }
}

function Invoke-WindowsInstallLifecycleSmoke {
    if (-not $IsWindows -and $env:OS -ne "Windows_NT") {
        throw "Windows unsigned clean-host portable install smoke requires a Windows host."
    }

    $version = Get-ViewerVersion
    $workRoot = Join-Path $env:TEMP "sl-cleanhost-smoke-$([Guid]::NewGuid().ToString('N'))"
    $distDir = Join-Path $workRoot "dist"
    $extractRoot = Join-Path $workRoot "extracted"
    $stubExe = Join-Path $workRoot "sl-viewer-stub.exe"
    $installDir = Join-Path $workRoot "installed"
    $shortcutPath = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\SessionLedger.lnk"
    $uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\SessionLedger"
    $packageScript = Join-RepoPath @("scripts", "package-windows.ps1")
    $defaultInstallDir = Join-Path $env:LOCALAPPDATA "Programs\SessionLedger"

    try {
        if (Test-Path -LiteralPath $defaultInstallDir) {
            throw "Clean-host precondition failed: default install dir already exists at '$defaultInstallDir'."
        }
        Add-EvidenceStep -Id "preflight" -Description "No prior SessionLedger install at default LocalAppData path" -Status "pass" -Detail $defaultInstallDir

        New-Item -ItemType Directory -Force -Path $workRoot | Out-Null
        New-ViewerStubExe -OutputPath $stubExe -Version $version -WorkRoot $workRoot
        Write-Output "ok: generated unsigned sl-viewer stub for clean-host packaging smoke"
        Add-EvidenceStep -Id "package-stub" -Description "Build unsigned stub sl-viewer.exe" -Status "pass" -Detail "version=$version"

        & $packageScript -SkipBuild -BinaryPath $stubExe -Version $version -DistDir $distDir
        if ($LASTEXITCODE -ne 0) {
            throw "package-windows.ps1 failed with exit code $LASTEXITCODE."
        }

        $archive = Get-ChildItem -LiteralPath $distDir -Filter *.zip -File | Select-Object -First 1
        if (-not $archive) {
            throw "Windows package archive was not produced."
        }
        Add-EvidenceStep -Id "package-zip" -Description "Produce unsigned portable ZIP via package-windows.ps1" -Status "pass" -Detail $archive.FullName

        Expand-Archive -LiteralPath $archive.FullName -DestinationPath $extractRoot
        $layoutDir = Get-ChildItem -LiteralPath $extractRoot -Directory | Select-Object -First 1
        if (-not $layoutDir) {
            throw "Extracted Windows package layout directory was not found."
        }
        Add-EvidenceStep -Id "extract" -Description "Extract portable ZIP to isolated work directory" -Status "pass" -Detail $layoutDir.FullName

        $installPs1 = Join-Path $layoutDir.FullName "Install.ps1"
        $uninstallPs1 = Join-Path $layoutDir.FullName "Uninstall.ps1"
        Assert-Path $installPs1 "extracted Install.ps1"
        Assert-Path $uninstallPs1 "extracted Uninstall.ps1"

        Push-Location $layoutDir.FullName
        try {
            & $installPs1 -InstallDir $installDir
            if ($LASTEXITCODE -ne 0) {
                throw "Install.ps1 failed with exit code $LASTEXITCODE."
            }
        }
        finally {
            Pop-Location
        }
        Add-EvidenceStep -Id "install" -Description "Run Install.ps1 into isolated install directory" -Status "pass" -Detail $installDir

        $installedBinary = Join-Path $installDir "sl-viewer.exe"
        Assert-Path $installedBinary "installed sl-viewer.exe"
        if (-not (Test-Path -LiteralPath $shortcutPath -PathType Leaf)) {
            throw "Start Menu shortcut was not created at '$shortcutPath'."
        }
        if (-not (Test-Path -LiteralPath $uninstallKey)) {
            throw "Windows uninstall registry entry was not created."
        }
        Write-Output "ok: Install.ps1 registered shortcut and uninstall metadata"
        Add-EvidenceStep -Id "register" -Description "Start Menu shortcut and uninstall registry entry created" -Status "pass" -Detail $shortcutPath

        $versionOutput = & $installedBinary --version
        if ($LASTEXITCODE -ne 0) {
            throw "Installed sl-viewer.exe --version failed with exit code $LASTEXITCODE."
        }
        $expectedVersionLine = "sl-viewer $version"
        if ($versionOutput -notcontains $expectedVersionLine) {
            throw "Installed binary version mismatch. Expected '$expectedVersionLine', got '$versionOutput'."
        }
        Write-Output "ok: installed binary --version returned '$expectedVersionLine'"
        Add-EvidenceStep -Id "launch" -Description "Installed binary --version succeeds" -Status "pass" -Detail $expectedVersionLine

        & $uninstallPs1 -InstallDir $installDir
        if ($LASTEXITCODE -ne 0) {
            throw "Uninstall.ps1 failed with exit code $LASTEXITCODE."
        }
        Add-EvidenceStep -Id "uninstall" -Description "Run Uninstall.ps1" -Status "pass" -Detail $installDir

        Wait-UntilAbsent -Path $installDir -Description "installed application directory after uninstall"
        Wait-UntilAbsent -Path $shortcutPath -Description "Start Menu shortcut after uninstall"
        Wait-UntilAbsent -Path $uninstallKey -Description "Windows uninstall registry entry after uninstall"
        Write-Output "ok: Windows unsigned clean-host portable install smoke passed"
        Add-EvidenceStep -Id "cleanup" -Description "Install dir, shortcut, and uninstall registry removed" -Status "pass" -Detail "post-uninstall verification"
    }
    finally {
        Remove-Item -LiteralPath $workRoot -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $shortcutPath -Force -ErrorAction SilentlyContinue
        Remove-Item -Path $uninstallKey -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $installDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$productWxs = Join-RepoPath @("packaging", "windows", "Product.wxs")
$installPs1 = Join-RepoPath @("packaging", "windows", "Install.ps1")
$uninstallPs1 = Join-RepoPath @("packaging", "windows", "Uninstall.ps1")
$appImageScript = Join-RepoPath @("packaging", "linux", "package-appimage.sh")
$distributionDoc = Join-RepoPath @("docs", "ops", "distribution.md")
$packagingReadme = Join-RepoPath @("packaging", "README.md")
$daemonContainerfile = Join-RepoPath @("crates", "sl-daemon", "Containerfile")

Write-Output "Clean-host smoke: documentation assertions (unsigned; no Authenticode)."
Write-Output "Optional -WindowsInstallLifecycle exercises unsigned portable install/uninstall on a clean Windows host."
Write-Output "Unsigned MSI Release smoke lives in release.yml; Authenticode remains deferred under ADR 0003 and issue #66."

$scaffoldOutcome = "pass"
try {
    Assert-Path $productWxs "WiX Product.wxs"
    Assert-Path $installPs1 "Windows Install.ps1"
    Assert-Path $uninstallPs1 "Windows Uninstall.ps1"
    Assert-Path $appImageScript "Linux AppImage script"
    Assert-Path (Join-RepoPath @("scripts", "package-msi.ps1")) "package-msi.ps1"
    Assert-Path (Join-RepoPath @("packaging", "macos", "package-app.sh")) "macOS package-app.sh"
    Assert-Path (Join-RepoPath @("packaging", "macos", "package-pkg.sh")) "macOS package-pkg.sh"

    Assert-Contains $productWxs 'Scope="perUser"' "WiX per-user install scope"
    Assert-Contains $productWxs 'sl-viewer\.exe' "WiX viewer executable payload"
    Assert-Contains $productWxs 'StartMenuShortcut' "WiX Start Menu shortcut"
    Assert-Contains $productWxs 'RemoveFolder.*On="uninstall"' "WiX uninstall removes install folder"

    Assert-Contains $installPs1 'Programs\\SessionLedger' "Windows install path below LocalAppData"
    Assert-Contains $installPs1 'SessionLedger\.lnk' "Windows Start Menu shortcut path"
    Assert-Contains $installPs1 'UninstallString' "Windows Installed Apps uninstall registration"

    Assert-Contains $uninstallPs1 'SessionLedger\.lnk' "Windows uninstall removes Start Menu shortcut"
    Assert-Contains $uninstallPs1 'CurrentVersion\\Uninstall\\SessionLedger' "Windows uninstall removes registry entry"
    Assert-Contains $uninstallPs1 'User data was not removed' "Windows uninstall preserves user data by design"

    Assert-Contains $appImageScript 'appimagetool' "AppImage tool requirement is explicit"
    Assert-Contains $appImageScript 'SessionLedger\.AppDir' "AppImage AppDir layout"
    Assert-Contains $appImageScript 'sessionledger\.desktop' "AppImage desktop entry"

    Assert-Contains $distributionDoc 'Clean-host install/uninstall evidence \(unsigned\)' "distribution guide documents unsigned clean-host checklist"
    Assert-Contains $distributionDoc 'Active \(unsigned\)' "distribution guide marks MSI/PKG Active unsigned"
    Assert-Contains $distributionDoc 'Uninstall / cleanliness' "distribution guide documents uninstall lifecycle"
    Assert-Contains $distributionDoc 'User data' "distribution guide documents user-data retention"
    Assert-Contains $packagingReadme 'Clean-host checklist \(unsigned\)' "packaging README documents unsigned clean-host checklist"
    Assert-Contains $packagingReadme 'Active \(unsigned\)' "packaging README marks MSI Active unsigned"

    Assert-Contains $daemonContainerfile 'HEALTHCHECK' "daemon Containerfile defines OCI HEALTHCHECK"
    Assert-Contains $daemonContainerfile '/healthz' "daemon Containerfile probes /healthz"

    Add-EvidenceStep -Id "scaffold" -Description "Installer documentation assertions" -Status "pass" -Detail "repository static checks"
    Write-Output "ok: clean-host documentation smoke passed"
}
catch {
    $scaffoldOutcome = "fail"
    Add-EvidenceStep -Id "scaffold" -Description "Installer scaffold and clean-host documentation assertions" -Status "fail" -Detail $_.Exception.Message
    throw
}
finally {
    if ($EvidencePath -and -not $WindowsInstallLifecycle) {
        Write-CleanHostEvidence -Path $EvidencePath -Mode "scaffold" -Outcome $scaffoldOutcome
    }
}

if ($WindowsInstallLifecycle) {
    $windowsOutcome = "pass"
    try {
        Invoke-WindowsInstallLifecycleSmoke
    }
    catch {
        $windowsOutcome = "fail"
        throw
    }
    finally {
        if ($EvidencePath) {
            Write-CleanHostEvidence -Path $EvidencePath -Mode "windows-unsigned-portable" -Outcome $windowsOutcome
        }
    }
}
