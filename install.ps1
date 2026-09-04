# ============================================================
#  InsightRAG AI  -  Global 1-Line Web Installer & Launcher
#  Usage from anywhere:
#    irm https://raw.githubusercontent.com/SypherKx/InsightRAG/main/install.ps1 | iex
# ============================================================

$ErrorActionPreference = "SilentlyContinue"
$ProgressPreference    = "SilentlyContinue"

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " ___ _   _ ____ ___ ____ _   _ _____   ____      _    ____ " -ForegroundColor Cyan
Write-Host "|_ _| \ | / ___|_ _/ ___| | | |_   _| |  _ \    / \  / ___|" -ForegroundColor Cyan
Write-Host " | ||  \| \___ \| | |  _| |_| | | |   | |_) |  / _ \| |  _ " -ForegroundColor Cyan
Write-Host " | || |\  |___) | | |_| |  _  | | |   |  _ <  / ___ \ |_| |" -ForegroundColor Cyan
Write-Host "|___|_| \_|____/___|____|_| |_| |_|   |_| \_\/_/   \_\____|" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  [ INSIGHT RAG ] - Autonomous Multimodal Local RAG Engine" -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Target Directory
$TargetDir = Join-Path $HOME "InsightRAG"
if (-not (Test-Path $TargetDir)) {
    Write-Host "[*] Cloning InsightRAG repository to $TargetDir..." -ForegroundColor Yellow
    git clone https://github.com/SypherKx/InsightRAG.git $TargetDir
} else {
    Write-Host "[*] Updating existing installation in $TargetDir..." -ForegroundColor Yellow
    Push-Location $TargetDir
    git pull origin main 2>&1 | Out-Null
    Pop-Location
}

# 2. Launch Local Engine
Set-Location $TargetDir
powershell -ExecutionPolicy Bypass -File (Join-Path $TargetDir "launch.ps1")
