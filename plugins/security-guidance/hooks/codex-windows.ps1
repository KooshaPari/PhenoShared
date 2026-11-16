param([Parameter(Mandatory = $true)][string]$Target)
$ErrorActionPreference = 'Stop'
$roots = [System.Collections.Generic.List[string]]::new()
$git = Get-Command git.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($git) {
    $dir = Split-Path -Parent $git.Source
    for ($i = 0; $i -lt 3 -and $dir; $i++) {
        $roots.Add($dir)
        $dir = Split-Path -Parent $dir
    }
}
foreach ($programFiles in @($env:ProgramW6432, $env:ProgramFiles, ${env:ProgramFiles(x86)})) {
    if ($programFiles) { $roots.Add((Join-Path $programFiles 'Git')) }
}
$bash = $null
foreach ($root in $roots) {
    foreach ($relative in @('bin\bash.exe', 'usr\bin\bash.exe')) {
        $candidate = Join-Path $root $relative
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
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
