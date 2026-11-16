param([Parameter(Mandatory = $true)][string]$Target)
$ErrorActionPreference = 'Stop'
$roots = [System.Collections.Generic.List[string]]::new()
$git = Get-Command git.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($git) {
    $gitDir = Split-Path -Parent $git.Source
    $dirName = Split-Path -Leaf $gitDir
    if ($dirName -in @('cmd', 'bin')) {
        $parent = Split-Path -Parent $gitDir
        $parentName = Split-Path -Leaf $parent
        if ($dirName -eq 'bin' -and $parentName -in @('ucrt64', 'mingw64', 'mingw32')) {
            $roots.Add((Split-Path -Parent $parent))
        } else {
            $roots.Add($parent)
        }
    }
}
foreach ($programFiles in @($env:ProgramW6432, $env:ProgramFiles, ${env:ProgramFiles(x86)})) {
    if ($programFiles) { $roots.Add((Join-Path $programFiles 'Git')) }
}
$bash = $null
foreach ($root in $roots) {
    $candidate = Join-Path $root 'usr\bin\bash.exe'
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
    foreach ($arch in @('ucrt64', 'mingw64', 'mingw32')) {
        $gitBinary = Join-Path $root "$arch\bin\git.exe"
        $gitCore = Join-Path $root "$arch\libexec\git-core\git.exe"
        if ((Test-Path -LiteralPath $gitBinary -PathType Leaf) -and
            (Test-Path -LiteralPath $gitCore -PathType Leaf)) {
            $bash = $candidate
            break
        }
    }
    if ($bash) { break }
}
if (-not $bash) {
    [Console]::Error.WriteLine('Security guidance requires Git for Windows')
    exit 1
}
$utf8 = [Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
$inputText = [Console]::In.ReadToEnd()
$shim = Join-Path $env:CLAUDE_PLUGIN_ROOT 'hooks\sg-python.sh'
$targetPath = Join-Path $env:CLAUDE_PLUGIN_ROOT "hooks\$Target"
$inputText | & $bash $shim $targetPath
exit $LASTEXITCODE
