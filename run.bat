@echo off
title InsightRAG Studio Launcher
cd /d "%~dp0"
echo ======================================================================
echo  [ INSIGHT RAG ] - Launching 100%% Local Multimodal RAG Factory...
echo ======================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [*] Falling back to direct Python orchestrator...
    python "%~dp0scripts\run_local.py"
)
pause
