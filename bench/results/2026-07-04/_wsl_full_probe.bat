@echo off
echo === WSL STATUS ===
wsl --status > "%~dp0\_wsl_status.txt" 2>&1
type "%~dp0\_wsl_status.txt"

echo.
echo === WSL LIST VERBOSE ===
wsl --list --verbose > "%~dp0\_wsl_list.txt" 2>&1
type "%~dp0\_wsl_list.txt"

echo.
echo === WSL UBUNTU 22.04 NVIDIA DEV ===
wsl -d Ubuntu-22.04 -- bash -c "ls -la /dev/nvidia* 2>&1; echo --; nvidia-smi -L 2>&1; echo --; ls -la /usr/lib/wsl/lib/libcuda* 2>&1" > "%~dp0\_wsl_nvidia_dev.txt" 2>&1
type "%~dp0\_wsl_nvidia_dev.txt"

echo.
echo === WSL NVIDIA DRIVER CHECK ===
where nvidia-smi.exe > "%~dp0\_wsl_drv_check.txt" 2>&1
echo Windows nvidia-smi path: >> "%~dp0\_wsl_drv_check.txt"
where nvidia-smi.exe >> "%~dp0\_wsl_drv_check.txt" 2>&1
echo. >> "%~dp0\_wsl_drv_check.txt"
echo lxss/lib contents: >> "%~dp0\_wsl_drv_check.txt"
dir "C:\Windows\System32\lxss\lib" >> "%~dp0\_wsl_drv_check.txt" 2>&1
type "%~dp0\_wsl_drv_check.txt"
