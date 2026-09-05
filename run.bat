@echo off
title Insight Forge Studio Launcher
cd /d "%~dp0"
echo ======================================================================
echo  [ INSIGHT FORGE ] - Launching 100%% Local Multimodal AI Engine...
echo ======================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [*] Falling back to direct Python orchestrator...
    python "%~dp0scripts\run_local.py"
)
pause
