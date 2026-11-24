# AgilePlus launcher — opens an interactive shell with the agileplus-cli on PATH.
$exe = "E:\agileplus-target\release\agileplus-cli.exe"
if (-not (Test-Path $exe)) { Write-Host "agileplus-cli.exe not built. Run: cargo build --release -p agileplus-cli"; pause; exit 1 }
# cd to the repo so the default ./agileplus.db (seeded: 6 projects, 6 epics, 150 stories) is found
Set-Location "E:\Dev\AgilePlus"
Set-Alias agileplus $exe
Write-Host "=== AgilePlus PM CLI ===" -ForegroundColor Cyan
& $exe list-projects
Write-Host ""
& $exe --help
Write-Host "`nType 'agileplus <command>' (e.g. agileplus list-projects). 'exit' to close." -ForegroundColor DarkGray
# drop into an interactive shell with the alias available
function prompt { "agileplus> " }
