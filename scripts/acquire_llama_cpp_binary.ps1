[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$TargetRoot = 'D:\WSL\tools',
    [string]$Tag = 'b10012',
    [ValidateSet('12.4', '13.3')]
    [string]$CudaToolkit = '13.3',
    [switch]$Execute
)

$ErrorActionPreference = 'Stop'
$targetName = if ($CudaToolkit -eq '13.3') { "llama.cpp-$Tag" } else { "llama.cpp-$Tag-cuda$CudaToolkit" }
$target = [IO.Path]::GetFullPath((Join-Path $TargetRoot $targetName))
$archiveRoot = Join-Path $target 'archives'
$binaryArchive = "llama-$Tag-bin-win-cuda-$CudaToolkit-x64.zip"
$runtimeArchive = "cudart-llama-bin-win-cuda-$CudaToolkit-x64.zip"
$knownHashes = @{
    '12.4' = @{
        $binaryArchive = 'daf5af0fe82dbda414aaf50ea57491e886c99e7fa1c741075f01431688ae9829'
        $runtimeArchive = '8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6'
    }
    '13.3' = @{
        $binaryArchive = '9573c446e8cea590e4d0825adafe97d518032ac8f0f786c267e45607e38e801b'
        $runtimeArchive = '1462a050eb4c684921ba51dcc4cc488a036674c3e73e9945ee705b854808d03e'
    }
}
$items = @(
    @{ name = $binaryArchive; sha256 = $knownHashes[$CudaToolkit][$binaryArchive] },
    @{ name = $runtimeArchive; sha256 = $knownHashes[$CudaToolkit][$runtimeArchive] }
)

if ($target -notmatch '^[DEde]:\\') { throw "Toolchain target must be on D: or E:; got $target" }
foreach ($item in $items) {
    $item.url = "https://github.com/ggml-org/llama.cpp/releases/download/$Tag/$($item.name)"
    $item.archive = Join-Path $archiveRoot $item.name
}
$manifest = [ordered]@{
    schema = 'pheno.llama_cpp_binary.v1'
    tag = $Tag
    target = $target
    platform = "windows-x64-cuda-$CudaToolkit"
    release = 'https://github.com/ggml-org/llama.cpp/releases/tag/' + $Tag
    assets = $items
    downloaded = $false
    extracted = $false
}

if (-not $Execute) {
    $manifest | ConvertTo-Json -Depth 5
    exit 0
}

New-Item -ItemType Directory -Force -Path $archiveRoot | Out-Null
foreach ($item in $items) {
    if (-not (Test-Path -LiteralPath $item.archive)) {
        if (-not $PSCmdlet.ShouldProcess($item.archive, "Download $($item.name)")) { continue }
        & curl.exe --fail --location --retry 5 --retry-delay 3 --continue-at - --output $item.archive $item.url
        if ($LASTEXITCODE -ne 0) { throw "curl failed for $($item.name) with exit code $LASTEXITCODE" }
    }
    $actual = (Get-FileHash -LiteralPath $item.archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $item.sha256) { throw "SHA-256 mismatch for $($item.name): $actual" }
}
$manifest.downloaded = $true

if ($PSCmdlet.ShouldProcess($target, 'Extract verified llama.cpp archives')) {
    Expand-Archive -LiteralPath (Join-Path $archiveRoot $binaryArchive) -DestinationPath $target -Force
    Expand-Archive -LiteralPath (Join-Path $archiveRoot $runtimeArchive) -DestinationPath $target -Force
}
$manifest.extracted = Test-Path -LiteralPath (Join-Path $target 'llama-quantize.exe')
$manifest.generated_at = (Get-Date).ToUniversalTime().ToString('o')
$manifestPath = Join-Path $target 'acquisition.json'
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
$manifest | ConvertTo-Json -Depth 5
if (-not $manifest.extracted) { throw "Verified archives extracted, but llama-quantize.exe was not found under $target" }
