# N11 — MSVC env wrapper (Forward DAG v2)
# Pony 0.67.0 was built with MSVC 19.51 but cl.exe is not on PATH by default.
# This wrapper imports the VS 2022 Community VC env so `nim c` and `ponyc` can find cl/link.
# Usage:  powershell -File scripts/vsdevcmd.ps1 -- nim c -d:release hello.nim
# Or dot-source: . scripts/vsdevcmd.ps1; nim c ...

$vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $vsWhere) {
    $vsPath = & $vsWhere -latest -products * -property installationPath
} else {
    $vsPath = "C:\Program Files\Microsoft Visual Studio\2022\Community"
}
$devCmd = Join-Path $vsPath "Common7\Tools\vsdevcmd.bat"
if (-not (Test-Path $devCmd)) { $devCmd = Join-Path $vsPath "VC\Auxiliary\Build\vcvars64.bat" }

if ($args.Count -eq 0) {
    Write-Host "vsdevcmd: MSVC 19.44 (Community) imported. cl.exe now on PATH."
    Write-Host "Run: vsdevcmd.ps1 -- <command>  or  . vsdevcmd.ps1"
    cmd /c "`"$devCmd`" -arch=x64 && set" | ForEach-Object {
        if ($_ -match "^(.*?)=(.*)$") { Set-Item -Path "env:$($Matches[1])" -Value $Matches[2] }
    }
} else {
    cmd /c "`"$devCmd`" -arch=x64 && $($args -join ' ')"
}
