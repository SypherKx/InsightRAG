# ============================================================
#  InsightRAG AI  -  Global 1-Line Web Installer & Launcher
#  Run from ANY PowerShell terminal (no cd or folder needed):
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
Write-Host "  100% Local Compute | Hardware Auto-Tuned | Instant Browser Launch" -ForegroundColor DarkGray
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Smart Target Directory Detection
$TargetDir = $null

# Check if current directory is already the repository
$currentDir = (Get-Location).Path
if ((Test-Path (Join-Path $currentDir "launch.ps1")) -and (Test-Path (Join-Path $currentDir "backend\main.py"))) {
    $TargetDir = $currentDir
}

# Check common desktop / user locations if already downloaded
if (-not $TargetDir) {
    $candidates = @(
        (Join-Path $HOME "InsightRAG"),
        (Join-Path $HOME "OneDrive\Desktop\Insight-Forge-master\Insight-Forge-master"),
        (Join-Path $HOME "Desktop\Insight-Forge-master\Insight-Forge-master"),
        (Join-Path $HOME "Desktop\InsightRAG"),
        (Join-Path $HOME "Downloads\InsightRAG"),
        "C:\InsightRAG"
    )
    foreach ($cand in $candidates) {
        if ((Test-Path (Join-Path $cand "launch.ps1")) -and (Test-Path (Join-Path $cand "backend\main.py"))) {
            $TargetDir = $cand
            break
        }
    }
}

# If not found anywhere, clone or download into $HOME\InsightRAG
if (-not $TargetDir) {
    $TargetDir = Join-Path $HOME "InsightRAG"
    if (-not (Test-Path $TargetDir)) {
        Write-Host "[*] Setting up InsightRAG in: $TargetDir" -ForegroundColor Yellow
        $gitCmd = Get-Command git -ErrorAction SilentlyContinue
        if ($gitCmd) {
            git clone https://github.com/SypherKx/InsightRAG.git $TargetDir
        } else {
            Write-Host "[*] Downloading InsightRAG bundle..." -ForegroundColor Yellow
            $zipPath = "$env:TEMP\InsightRAG.zip"
            Invoke-WebRequest -Uri "https://github.com/SypherKx/InsightRAG/archive/refs/heads/main.zip" -OutFile $zipPath -UseBasicParsing
            Expand-Archive -Path $zipPath -DestinationPath $HOME -Force
            if (Test-Path (Join-Path $HOME "InsightRAG-main")) {
                Rename-Item -Path (Join-Path $HOME "InsightRAG-main") -NewName "InsightRAG" -Force
            }
        }
    } else {
        Write-Host "[*] Updating existing installation in: $TargetDir" -ForegroundColor Yellow
        Push-Location $TargetDir
        git pull origin main 2>&1 | Out-Null
        Pop-Location
    }
}

Write-Host "[*] Project Location: $TargetDir" -ForegroundColor Green
Write-Host "[*] Starting Engine & Web Studio..." -ForegroundColor Cyan
Write-Host ""

Set-Location $TargetDir
powershell -ExecutionPolicy Bypass -File (Join-Path $TargetDir "launch.ps1")

