@echo off
REM sign_release.bat — Windows equivalent of scripts/sign_release.sh
REM Build a tarball of the current HEAD, sign with cosign keyless, upload to GitHub Release.
REM
REM Usage:
REM   scripts\sign_release.bat [TAG]
REM   TAG defaults to the most recent v* tag (e.g. v0.37-pheno-harness-summit)
REM
REM Requirements:
REM   - cosign on PATH (or in C:\tmp\cosign.exe)
REM   - gh CLI authenticated (gh auth login)
REM   - Python 3.11+ for tarball build

setlocal EnableDelayedExpansion
set
TAG=%1
if "%TAG%"=="" (
    for /f "delims=" %%t in ('git describe --tags --abbrev=0 "v*" 2^>nul') do set TAG=%%t
)
if "%TAG%"=="" (
    echo ERROR: no tag found, pass TAG explicitly.
    exit /b 1
)

if exist C:\tmp\cosign.exe set COSIGN=C:\tmp\cosign.exe
if "%COSIGN%"=="" (
    where cosign >nul 2>&1
    if !ERRORLEVEL!==0 set COSIGN=cosign
)
if "%COSIGN%"=="" (
    echo ERROR: cosign not found. Install or place at C:\tmp\cosign.exe.
    exit /b 1
)

where gh >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo ERROR: gh CLI not on PATH.
    exit /b 1
)

echo ==^> Building tarball for %T%
set OUTFILE=pheno-harness-%TAG%.tar.gz
python scripts\_make_tarball.py %OUTFILE%
if not exist %OUTFILE% (
    echo ERROR: tarball not produced.
    exit /b 1
)

echo ==^> SHA256 sidecar
certutil -hashfile %OUTFILE% SHA256 > %OUTFILE%.sha256
type %OUTFILE%.sha256

echo ==^> Sign with cosign keyless (Sigstore OIDC)
%COSIGN% sign-blob %OUTFILE% --output-signature %OUTFILE%.sig --output-certificate %OUTFILE%.cert --yes
if !ERRORLEVEL! neq 0 (
    echo WARN: keyless signing failed, falling back to local key
    if not exist cosign.key (
        %COSIGN% generate-key-pair --output-key-prefix cosign
    )
    %COSIGN% sign-blob --key cosign.key %OUTFILE% --output-signature %OUTFILE%.sig --output-certificate %OUTFILE%.cert --yes
)

echo ==^> Upload to GitHub Release
gh release upload %TAG% %OUTFILE% %OUTFILE%.sig %OUTFILE%.cert %OUTFILE%.sha256 --clobber
if !ERRORLEVEL! neq 0 (
    echo WARN: upload failed. Make sure the release exists: gh release create %TAG%
    exit /b 1
)

echo ==^> Done. Files uploaded:
dir %OUTFILE%* | findstr /C:"%TAG%"

endlocal