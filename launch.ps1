﻿# ============================================================
#
#  InsightRAG AI  -  Autonomous Multimodal RAG Engine
#  1-Click Local Launcher & Installer
#
#  Usage (from project folder):
#    powershell -ExecutionPolicy Bypass -File .\launch.ps1
#
# ============================================================

$ErrorActionPreference = "SilentlyContinue"
$ProgressPreference    = "SilentlyContinue"

# Resolve Project Root
$ProjectRoot = if ($PSScriptRoot) { $PSScriptRoot } elseif ($MyInvocation.MyCommand.Path) { Split-Path -Parent $MyInvocation.MyCommand.Path } else { (Get-Location).Path }
Set-Location $ProjectRoot

# Helpers
function cw {
    param(
        [Parameter(Mandatory=$true)][string]$Text,
        [string]$Color = "White",
        [switch]$NoNewline
    )
    if ($NoNewline) {
        Write-Host $Text -ForegroundColor $Color -NoNewline
    } else {
        Write-Host $Text -ForegroundColor $Color
    }
}

function Sep { cw "============================================================" "Cyan" }
function DashSep { cw "------------------------------------------------------------" "DarkGray" }

function Write-Step {
    param(
        [Parameter(Mandatory=$true)][string]$Msg,
        [Parameter(Mandatory=$true)][string]$Status,
        [string]$StatusColor = "Green"
    )
    cw "[*] $Msg... [ " "White" -NoNewline
    cw $Status $StatusColor -NoNewline
    cw " ]" "White"
}

# Force UTF-8 in Console to prevent â–ˆ corruption
try {
    [Console]::InputEncoding = [System.Text.Encoding]::UTF8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
    $null = chcp 65001
} catch {}

# Banner
Clear-Host
cw ""
cw "██╗███╗   ██╗███████╗██╗ ██████╗ ██╗  ██╗████████╗    ██████╗   █████╗   ██████╗ " "Cyan"
cw "██║████╗  ██║██╔════╝██║██╔════╝ ██║  ██║╚══██╔══╝    ██╔══██╗ ██╔══██╗ ██╔════╝ " "Cyan"
cw "██║██╔██╗ ██║███████╗██║██║  ███╗███████║   ██║       ██████╔╝ ███████║ ██║  ███╗" "Cyan"
cw "██║██║╚██╗██║╚════██║██║██║   ██║██╔══██║   ██║       ██╔══██╗ ██╔══██║ ██║   ██║" "Cyan"
cw "██║██║ ╚████║███████║██║╚██████╔╝██║  ██║   ██║       ██║  ██║ ██║  ██║ ╚██████╔╝" "Cyan"
cw "╚═╝╚═╝  ╚═══╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝       ╚═╝  ╚═╝ ╚═╝  ╚═╝  ╚═════╝ " "Cyan"
cw ""

# 1. Python Check
$pyExe  = $null
$pyVers = $null
foreach ($candidate in @("python", "python3", "py")) {
    $v = & $candidate --version 2>&1
    if ($LASTEXITCODE -eq 0 -and $v -match "Python (\d+\.\d+)") {
        $pyExe  = $candidate
        $pyVers = $Matches[1]
        break
    }
}
if ($pyExe) {
    Write-Step "Checking Python installation ($pyVers)" "OK" "Green"
} else {
    cw "[!] Python 3.10+ not found. Install from https://python.org then re-run." "Red"
    Read-Host "Press Enter to exit"
    exit 1
}

# 2. Node / npm Check
$npmCmd = $null
$chkNpm = Get-Command npm -ErrorAction SilentlyContinue
$chkNpmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
if ($chkNpm) {
    $npmCmd = "npm"
} elseif ($chkNpmCmd) {
    $npmCmd = "npm.cmd"
}

if ($npmCmd) {
    $npmVers = & $npmCmd --version 2>&1
    Write-Step "Checking Node.js / npm (v$npmVers)" "OK" "Green"
} else {
    cw "[*] npm not found. Attempting install via winget..." "Yellow"
    winget install OpenJS.NodeJS.LTS --silent --accept-source-agreements --accept-package-agreements 2>&1 | Out-Null
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
    $npmCmd = if (Get-Command npm.cmd -ErrorAction SilentlyContinue) { "npm.cmd" } else { "npm" }
    $npmVers = & $npmCmd --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Step "Node.js installed (v$npmVers)" "OK" "Green"
    } else {
        cw "[!] Could not install Node.js. Please install from https://nodejs.org" "Red"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# 3. Ollama Check
$ollamaRunning = $false
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    if ($r.StatusCode -eq 200) {
        Write-Step "Checking Ollama AI Engine installation" "OK" "Green"
        Write-Step "Checking Ollama local service" "ACTIVE" "Green"
        $ollamaRunning = $true
    }
} catch {
    $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
    $ollamaSrc = if ($ollamaCmd) { $ollamaCmd.Source } else { $null }
    $ollamaExe = $null

    $candidates = @(
        $ollamaSrc,
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
        "C:\Program Files\Ollama\ollama.exe"
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path $p)) {
            $ollamaExe = $p
            break
        }
    }

    if ($ollamaExe) {
        Write-Step "Checking Ollama AI Engine installation" "OK" "Green"
        Write-Step "Checking Ollama local service" "STARTING SERVICE" "Yellow"
        Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 2
        cw "[*] Ollama process launched in background." "Green"
        $ollamaRunning = $true
    } else {
        cw "[*] Ollama not found - downloading installer..." "Yellow"
        $installer = "$env:TEMP\OllamaSetup.exe"
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $installer -UseBasicParsing
        cw "[*] Installing Ollama silently..." "Yellow"
        Start-Process -FilePath $installer -ArgumentList "/S" -Wait
        $ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
        if (Test-Path $ollamaExe) {
            Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep -Seconds 2
            Write-Step "Ollama installed and started" "OK" "Green"
            $ollamaRunning = $true
        } else {
            cw "[!] Ollama install skipped - continuing with local fallback." "Yellow"
        }
    }
}

# 4. Hardware Check
$threads = [System.Environment]::ProcessorCount
$gpuMode = "Standard Multi-Core CPU Mode ($threads Threads)"
try {
    $gpu = (& $pyExe -c "import torch; print(torch.cuda.get_device_name(0))" 2>&1)
    if ($LASTEXITCODE -eq 0 -and $gpu -notmatch "Error" -and $gpu.Trim()) {
        $gpuMode = "NVIDIA CUDA GPU [ $gpu ]"
    }
} catch {}
Write-Step "Hardware Architecture: $gpuMode" "ACTIVE" "Green"
cw ""

# 5. Python Dependencies
cw "[*] Downloading & checking dependencies with live status:" "Cyan"
DashSep

$pyPackages = @(
    @{ import="fastapi";              pip="fastapi" },
    @{ import="uvicorn";              pip="uvicorn[standard]" },
    @{ import="pydantic";             pip="pydantic" },
    @{ import="httpx";                pip="httpx" },
    @{ import="pandas";               pip="pandas" },
    @{ import="numpy";                pip="numpy" },
    @{ import="scipy";                pip="scipy" },
    @{ import="chardet";              pip="chardet" },
    @{ import="multipart";            pip="python-multipart" },
    @{ import="psutil";               pip="psutil" },
    @{ import="sqlalchemy";           pip="sqlalchemy" },
    @{ import="PIL";                  pip="pillow" },
    @{ import="sentence_transformers"; pip="sentence-transformers" },
    @{ import="faiss";                pip="faiss-cpu" },
    @{ import="pypdf";                pip="pypdf" },
    @{ import="docx";                 pip="python-docx" }
)

$toInstall = @()
foreach ($pkg in $pyPackages) {
    $chk = & $pyExe -c "import $($pkg.import)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        $name = $pkg.pip.PadRight(30)
        cw "  + $name  [ INSTALLED ]" "Green"
    } else {
        $name = $pkg.pip.PadRight(30)
        cw "  - $name  [ QUEUED ]" "Yellow"
        $toInstall += $pkg.pip
    }
}

if ($toInstall.Count -gt 0) {
    cw ""
    cw "  Installing $($toInstall.Count) package(s)..." "Yellow"
    DashSep
    & $pyExe -m pip install @toInstall 2>&1 | ForEach-Object {
        if ($_ -match "^(Collecting|Downloading|Installing|Successfully)") {
            cw "  $_" "DarkGray"
        }
    }
    cw ""
    cw "[OK] All Python packages installed!" "Green"
} else {
    cw ""
    cw "[OK] All Python packages already installed!" "Green"
}

# 6. Frontend Dependencies
$nodeModules = Join-Path $ProjectRoot "frontend\node_modules"
if (-not (Test-Path $nodeModules)) {
    cw ""
    cw "[*] Installing frontend npm packages (first run - ~1 min)..." "Yellow"
    DashSep
    Push-Location (Join-Path $ProjectRoot "frontend")
    & $npmCmd install 2>&1 | ForEach-Object { cw "  $_" "DarkGray" }
    Pop-Location
    cw "[OK] Frontend packages installed!" "Green"
} else {
    Write-Step "Checking frontend npm packages" "OK" "Green"
}

# 7. Launch Servers (Multi-threaded Python Orchestrator)
cw ""
Sep
cw "  ⚡ Launching Insight Forge Studio..." "Yellow"
cw "  👉 Studio URL: http://localhost:5173/app/upload" "Cyan"
Sep
cw ""

$runnerScript = Join-Path $ProjectRoot "scripts\run_local.py"
& $pyExe $runnerScript --skip-checks
