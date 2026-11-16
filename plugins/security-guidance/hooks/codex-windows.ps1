param([Parameter(Mandatory = $true)][string]$Target)
$ErrorActionPreference = 'Stop'
$programFiles = if ($env:ProgramW6432) { $env:ProgramW6432 } else { $env:ProgramFiles }
$bash = Join-Path $programFiles 'Git\bin\bash.exe'
if (-not (Test-Path -LiteralPath $bash -PathType Leaf)) {
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
