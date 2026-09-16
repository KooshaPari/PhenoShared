@echo off
setlocal
"C:\Python314\python.exe" -X utf8 "C:\Users\koosh\pheno-harness\bench\results\2026-07-04\_pypi_probe.py" > "C:\Users\koosh\pheno-harness\bench\results\2026-07-04\_pypi_probe.out" 2>&1
echo RC=%errorlevel%
type "C:\Users\koosh\pheno-harness\bench\results\2026-07-04\_pypi_probe.out"