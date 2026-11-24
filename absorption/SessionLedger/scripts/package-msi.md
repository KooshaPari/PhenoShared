# Windows MSI (unsigned)

`packaging/windows/Product.wxs` is the WiX v4 definition for a per-user MSI.
It installs `sl-viewer.exe` below `%LOCALAPPDATA%\Programs\SessionLedger` and
adds a Start Menu shortcut. Release CI builds and publishes
`SessionLedger-<version>-x64.msi` via `scripts/package-msi.ps1`. Authenticode
signing remains deferred ([ADR 0003](../docs/adr/0003-platform-code-signing.md)).

## Developer build

On Windows, create the application layout (or let `package-msi.ps1` do it):

```powershell
.\scripts\package-windows.ps1
```

Install WiX v4 (`dotnet tool install --global wix`), then build the MSI:

```powershell
.\scripts\package-msi.ps1
# or, when the layout already exists:
.\scripts\package-msi.ps1 -SkipBuild -SkipLayout `
  -SourceDir (Resolve-Path "packaging\dist\sl-viewer-v0.1.0-x86_64-pc-windows-msvc")
```

Equivalent manual WiX invocation:

```powershell
$version = "0.1.0"
$source = Resolve-Path "packaging\dist\sl-viewer-v$version-x86_64-pc-windows-msvc"
wix build .\packaging\windows\Product.wxs `
  -d "Version=$version" `
  -d "SourceDir=$source" `
  -o ".\packaging\dist\SessionLedger-$version-x64.msi"
```

## Silent install smoke (unsigned)

```powershell
$msi = Resolve-Path ".\packaging\dist\SessionLedger-0.1.0-x64.msi"
msiexec /i $msi /qn /norestart
& "$env:LOCALAPPDATA\Programs\SessionLedger\sl-viewer.exe" --version
msiexec /x $msi /qn /norestart
```

Release CI runs the same install → `--version` → uninstall path on
`windows-latest`. SmartScreen may still warn on interactive installs until
Authenticode lands.

## Signing is deferred

Neither `sl-viewer.exe` nor the MSI is Authenticode-signed. Production release
work must sign both files with `signtool`, timestamp signatures, and establish
certificate custody before claiming a SmartScreen-trusted installer. Until then,
MSI artifacts are unsigned release assets for internal evaluation.

Release archives remain covered by the existing checksum, keyless cosign, and
GitHub attestation path documented in
[`docs/ops/distribution.md`](../docs/ops/distribution.md#release-integrity-signing-cosign).
That supply-chain evidence does not replace Authenticode.
