@echo off
powershell -NoProfile -Command "wsl --status" > "C:\Users\koosh\pheno-harness\bench\results\2026-07-04\_wsl_status.txt" 2>&1
powershell -NoProfile -Command "Get-ChildItem 'C:\Program Files\NVIDIA Corporation\' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name" > "C:\Users\koosh\pheno-harness\bench\results\2026-07-04\_nvidia_corp.txt" 2>&1
powershell -NoProfile -Command "Get-ChildItem 'C:\Windows\System32\lxss\lib\' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name" > "C:\Users\koosh\pheno-harness\bench\results\2026-07-04\_wsl_lib.txt" 2>&1
echo done