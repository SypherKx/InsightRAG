# ============================================================
#  InsightRAG AI  -  Global 1-Line Web Installer & Updater
#  Run from ANY PowerShell terminal (no cd or folder needed):
#    irm https://www.insightrag.tech/install.ps1 | iex
# ============================================================

$ErrorActionPreference = "Continue"
$ProgressPreference    = "SilentlyContinue"

function Write-Highlight {
    param([string]$Text, [string]$Color = "Cyan")
    Write-Host $Text -ForegroundColor $Color
}

Write-Highlight "`n============================================================" "Cyan"
Write-Highlight " ⚡ InsightRAG AI - Smart Installer & Auto-Updater" "Green"
Write-Highlight "============================================================`n" "Cyan"

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
        (Join-Path $HOME "Desktop\InsightRAG"),
        (Join-Path $HOME "Downloads\InsightRAG"),
        (Join-Path $HOME "Documents\InsightRAG"),
        "C:\InsightRAG"
    )
    foreach ($cand in $candidates) {
        if ((Test-Path (Join-Path $cand "launch.ps1")) -and (Test-Path (Join-Path $cand "backend\main.py"))) {
            $TargetDir = $cand
            break
        }
    }
}

$isFreshInstall = $false
if (-not $TargetDir) {
    $TargetDir = Join-Path $HOME "InsightRAG"
    $isFreshInstall = $true
}

$gitCmd = Get-Command git -ErrorAction SilentlyContinue

function Update-From-Zip {
    param([string]$Destination)
    Write-Host "[*] Downloading latest release archive from GitHub..." -ForegroundColor Yellow
    $zipPath = "$env:TEMP\InsightRAG-latest.zip"
    $extractTemp = "$env:TEMP\InsightRAG-update-temp"
    if (Test-Path $extractTemp) { Remove-Item -Path $extractTemp -Recurse -Force -ErrorAction SilentlyContinue }

    try {
        Invoke-WebRequest -Uri "https://github.com/SypherKx/InsightRAG/archive/refs/heads/main.zip" -OutFile $zipPath -UseBasicParsing
        Expand-Archive -Path $zipPath -DestinationPath $extractTemp -Force
        
        $sourceDir = Join-Path $extractTemp "InsightRAG-main"
        if (Test-Path $sourceDir) {
            if (-not (Test-Path $Destination)) {
                New-Item -ItemType Directory -Path $Destination -Force | Out-Null
            }
            # Copy all files, preserving user database and uploads
            Get-ChildItem -Path $sourceDir | ForEach-Object {
                $destItem = Join-Path $Destination $_.Name
                if ($_.Name -in @("insightforge.db", ".env", "uploads") -and (Test-Path $destItem)) {
                    # Preserve existing user files
                } else {
                    Copy-Item -Path $_.FullName -Destination $Destination -Recurse -Force
                }
            }
            Remove-Item -Path $extractTemp -Recurse -Force -ErrorAction SilentlyContinue
            Remove-Item -Path $zipPath -Force -ErrorAction SilentlyContinue
            Write-Host "[✓] All project files successfully updated to latest version!" -ForegroundColor Green
        }
    } catch {
        Write-Host "[!] Warning: Could not update via zip: $_" -ForegroundColor Red
    }
}

if ($isFreshInstall) {
    Write-Host "[*] Fresh installation detected. Setting up InsightRAG at: $TargetDir" -ForegroundColor Yellow
    if ($gitCmd) {
        Write-Host "  -> Cloning repository via git..." -ForegroundColor DarkGray
        git clone https://github.com/SypherKx/InsightRAG.git $TargetDir
    } else {
        Update-From-Zip -Destination $TargetDir
    }
} else {
    Write-Host "[*] Existing installation detected at: $TargetDir" -ForegroundColor Cyan
    Write-Host "[*] Checking and applying latest updates from GitHub..." -ForegroundColor Yellow

    $updatedViaGit = $false
    if ((Test-Path (Join-Path $TargetDir ".git")) -and $gitCmd) {
        try {
            Push-Location $TargetDir
            # Abort any in-progress merge or rebase and clean conflict state
            git merge --abort 2>&1 | Out-Null
            git rebase --abort 2>&1 | Out-Null
            git fetch origin main 2>&1 | Out-Null
            $localRev = git rev-parse HEAD 2>$null
            $remoteRev = git rev-parse origin/main 2>$null
            if ($localRev -and $remoteRev -and ($localRev -ne $remoteRev)) {
                Write-Host "  -> Newer version found on GitHub! Updating repository..." -ForegroundColor Yellow
                git reset --hard origin/main 2>&1 | Out-Null
                Write-Host "[✓] Repository successfully updated to latest commit!" -ForegroundColor Green
            } else {
                git reset --hard origin/main 2>&1 | Out-Null
                Write-Host "[✓] Already running the latest version from GitHub." -ForegroundColor Green
            }
            $updatedViaGit = $true
            Pop-Location
        } catch {
            Pop-Location
            $updatedViaGit = $false
        }
    }

    if (-not $updatedViaGit) {
        Update-From-Zip -Destination $TargetDir
    }
}

# 2. Register Global Offline Command (Run 'insightrag' from anywhere)
try {
    $cliPath = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\insightrag.cmd"
    $cmdContent = "@echo off`r`npowershell -ExecutionPolicy Bypass -File `"$TargetDir\launch.ps1`""
    Set-Content -Path $cliPath -Value $cmdContent -Force -ErrorAction SilentlyContinue
} catch {}

# 3. Launch via launch.ps1
Set-Location $TargetDir
powershell -ExecutionPolicy Bypass -File (Join-Path $TargetDir "launch.ps1")
