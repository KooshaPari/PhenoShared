$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$visualSpec = Join-Path $repoRoot "docs\VISUAL_SPEC.md"
$visualReadme = Join-Path $repoRoot "tests\visual\README.md"
$goldenDir = Join-Path $repoRoot "tests\visual\golden"
$goldenBaseline = Join-Path $goldenDir "e1-bundle-empty.png"
$goldenProvenance = Join-Path $repoRoot "tests\visual\PROVENANCE.md"
$a11ySpec = Join-Path $repoRoot "tests\visual\harness\a11y.spec.js"
$visualSpecHarness = Join-Path $repoRoot "tests\visual\harness\visual.spec.js"
$viewerServer = Join-Path $repoRoot "tests\visual\harness\serve-viewer.mjs"
$viewerConfig = Join-Path $repoRoot "crates\sl-viewer\Dioxus.toml"

$requiredSections = @(
    "## 1. Lab-Coat palette",
    "## 2. Empty states",
    "## 3. Loading & skeleton states",
    "## 4. Error & failure states",
    "## 5. Motion & reduced motion",
    "## 7. Keyboard map (viewer)",
    "## 8. Acceptance (L107)"
)

$missing = @()
foreach ($section in $requiredSections) {
    if (-not (Select-String -Path $visualSpec -SimpleMatch $section -Quiet)) {
        $missing += $section
    }
}

if (-not (Test-Path -Path $visualReadme -PathType Leaf)) {
    $missing += "tests/visual/README.md"
}
if (-not (Test-Path -Path $goldenDir -PathType Container)) {
    $missing += "tests/visual/golden/"
}
if (-not (Test-Path -Path $a11ySpec -PathType Leaf)) {
    $missing += "tests/visual/harness/a11y.spec.js"
}
if (-not (Test-Path -Path $visualSpecHarness -PathType Leaf)) {
    $missing += "tests/visual/harness/visual.spec.js"
}
if (-not (Test-Path -Path $viewerServer -PathType Leaf)) {
    $missing += "tests/visual/harness/serve-viewer.mjs"
}
if (-not (Test-Path -Path $viewerConfig -PathType Leaf)) {
    $missing += "crates/sl-viewer/Dioxus.toml"
}
if (-not (Test-Path -Path $goldenBaseline -PathType Leaf)) {
    $missing += "tests/visual/golden/e1-bundle-empty.png"
}
if (-not (Test-Path -Path $goldenProvenance -PathType Leaf)) {
    $missing += "tests/visual/PROVENANCE.md"
} elseif (-not (Select-String -Path $goldenProvenance -SimpleMatch "e1-bundle-empty.png" -Quiet)) {
    $missing += "tests/visual/PROVENANCE.md row for e1-bundle-empty.png"
}

if ($missing.Count -gt 0) {
    Write-Error ("Visual contract validation failed. Missing: " + ($missing -join ", "))
}

Write-Host "Visual contract validation passed."
