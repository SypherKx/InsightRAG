# ============================================================
#
#  InsightRAG AI  -  Autonomous Multimodal RAG Engine
#  1-Click Local Launcher & Installer
#
#  Usage (from project folder):
#    powershell -ExecutionPolicy Bypass -File .\launch.ps1
#
# ============================================================

param(
    [switch]$Update
)

$ErrorActionPreference = "SilentlyContinue"
$ProgressPreference = "SilentlyContinue"

# Resolve Project Root
$ProjectRoot = if ($PSScriptRoot) { $PSScriptRoot } elseif ($MyInvocation.MyCommand.Path) { Split-Path -Parent $MyInvocation.MyCommand.Path } else { (Get-Location).Path }
Set-Location $ProjectRoot

# Display Bold Cyan ASCII Art Banner
Clear-Host
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$b64 = '4paI4paI4pWX4paI4paI4paI4pWXICAg4paI4paI4pWX4paI4paI4paI4paI4paI4paI4paI4pWX4paI4paI4pWXIOKWiOKWiOKWiOKWiOKWiOKWiOKVlyDilojilojilZcgIOKWiOKWiOKVl+KWiOKWiOKWiOKWiOKWiOKWiOKWiOKWiOKVlyAgICDilojilojilojilojilojilojilZcgICDilojilojilojilojilojilZcgICDilojilojilojilojilojilojilZcgCuKWiOKWiOKVkeKWiOKWiOKWiOKWiOKVlyAg4paI4paI4pWR4paI4paI4pWU4pWQ4pWQ4pWQ4pWQ4pWd4paI4paI4pWR4paI4paI4pWU4pWQ4pWQ4pWQ4pWQ4pWdIOKWiOKWiOKVkSAg4paI4paI4pWR4pWa4pWQ4pWQ4paI4paI4pWU4pWQ4pWQ4pWdICAgIOKWiOKWiOKVlOKVkOKVkOKWiOKWiOKVlyDilojilojilZTilZDilZDilojilojilZcg4paI4paI4pWU4pWQ4pWQ4pWQ4pWQ4pWdIArilojilojilZHilojilojilZTilojilojilZcg4paI4paI4pWR4paI4paI4paI4paI4paI4paI4paI4pWX4paI4paI4pWR4paI4paI4pWRICDilojilojilojilZfilojilojilojilojilojilojilojilZEgICDilojilojilZEgICAgICAg4paI4paI4paI4paI4paI4paI4pWU4pWdIOKWiOKWiOKWiOKWiOKWiOKWiOKWiOKVkSDilojilojilZEgIOKWiOKWiOKWiOKVlwrilojilojilZHilojilojilZHilZrilojilojilZfilojilojilZHilZrilZDilZDilZDilZDilojilojilZHilojilojilZHilojilojilZEgICDilojilojilZHilojilojilZTilZDilZDilojilojilZEgICDilojilojilZEgICAgICAg4paI4paI4pWU4pWQ4pWQ4paI4paI4pWXIOKWiOKWiOKVlOKVkOKVkOKWiOKWiOKVkSDilojilojilZEgICDilojilojilZEK4paI4paI4pWR4paI4paI4pWRIOKVmuKWiOKWiOKWiOKWiOKVkeKWiOKWiOKWiOKWiOKWiOKWiOKWiOKVkeKWiOKWiOKVkeKVmuKWiOKWiOKWiOKWiOKWiOKWiOKVlOKVneKWiOKWiOKVkSAg4paI4paI4pWRICAg4paI4paI4pWRICAgICAgIOKWiOKWiOKVkSAg4paI4paI4pWRIOKWiOKWiOKVkSAg4paI4paI4pWRIOKVmuKWiOKWiOKWiOKWiOKWiOKWiOKVlOKVnQrilZrilZDilZ3ilZrilZDilZ0gIOKVmuKVkOKVkOKVkOKVneKVmuKVkOKVkOKVkOKVkOKVkOKVkOKVneKVmuKVkOKVnSDilZrilZDilZDilZDilZDilZDilZ0g4pWa4pWQ4pWdICDilZrilZDilZ0gICDilZrilZDilZ0gICAgICAg4pWa4pWQ4pWdICDilZrilZDilZ0g4pWa4pWQ4pWdICDilZrilZDilZ0gIOKVmuKVkOKVkOKVkOKVkOKVkOKVnSA='
$banner = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($b64))
Write-Host "`n$banner`n" -ForegroundColor Cyan

# Helpers
function cw {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [string]$Color = "White",
        [switch]$NoNewline
    )
    if ($NoNewline) {
        Write-Host $Text -ForegroundColor $Color -NoNewline
    }
    else {
        Write-Host $Text -ForegroundColor $Color
    }
}

function Sep { cw "============================================================" "Cyan" }
function DashSep { cw "------------------------------------------------------------" "DarkGray" }

function Write-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Msg,
        [Parameter(Mandatory = $true)][string]$Status,
        [string]$StatusColor = "Green"
    )
    cw "[*] $Msg... [ " "White" -NoNewline
    cw $Status $StatusColor -NoNewline
    cw " ]" "White"
}

function Test-InternetConnection {
    try {
        $ping = New-Object System.Net.NetworkInformation.Ping
        $reply = $ping.Send("8.8.8.8", 1500)
        if ($reply.Status -eq [System.Net.NetworkInformation.IPStatus]::Success) {
            return $true
        }
    } catch {}
    try {
        $req = [System.Net.WebRequest]::Create("https://www.google.com")
        $req.Timeout = 2000
        $req.Method = "HEAD"
        $resp = $req.GetResponse()
        $resp.Close()
        return $true
    } catch {}
    return $false
}

# Register or update global 'insightrag' command in WindowsApps
try {
    $cliPath = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\insightrag.cmd"
    $cmdContent = "@echo off`r`npowershell -ExecutionPolicy Bypass -File `"$ProjectRoot\launch.ps1`" %*"
    Set-Content -Path $cliPath -Value $cmdContent -Force -ErrorAction SilentlyContinue
} catch {}

# Interactive update prompt
$shouldCheckUpdates = $false
if ($Update) {
    $shouldCheckUpdates = $true
} else {
    Sep
    cw " [?] Do you want to check for new updates? (y/N): " "Yellow" -NoNewline
    $ans = Read-Host
    if ($ans -and ($ans.Trim().ToLower() -in @("y", "yes"))) {
        $shouldCheckUpdates = $true
    }
}

if ($shouldCheckUpdates) {
    Sep
    cw " [*] Checking internet connection..." "Cyan"
    $isOnline = Test-InternetConnection
    if ($isOnline) {
        cw "[+] Internet connection active. Checking GitHub for updates..." "Green"
        $gitCmd = Get-Command git -ErrorAction SilentlyContinue
        if ((Test-Path (Join-Path $ProjectRoot ".git")) -and $gitCmd) {
            try {
                Push-Location $ProjectRoot
                git merge --abort 2>&1 | Out-Null
                git rebase --abort 2>&1 | Out-Null
                git fetch origin main 2>&1 | Out-Null
                $localRev = git rev-parse HEAD 2>$null
                $remoteRev = git rev-parse origin/main 2>$null
                if ($localRev -and $remoteRev -and ($localRev -ne $remoteRev)) {
                    cw "  -> Newer updates found! Updating repository..." "Yellow"
                    git reset --hard origin/main 2>&1 | Out-Null
                    cw "[+] Successfully updated to latest commit!" "Green"
                } else {
                    cw "[+] Already running the latest version." "Green"
                }
                Pop-Location
            } catch {
                Pop-Location
                cw "[!] Update check encountered an issue. Proceeding with installed version." "Yellow"
            }
        } else {
            cw "[*] Updating files from GitHub release archive..." "Yellow"
            try {
                $zipPath = "$env:TEMP\InsightRAG-latest.zip"
                $extractTemp = "$env:TEMP\InsightRAG-update-temp"
                if (Test-Path $extractTemp) { Remove-Item -Path $extractTemp -Recurse -Force -ErrorAction SilentlyContinue }
                Invoke-WebRequest -Uri "https://github.com/SypherKx/InsightRAG/archive/refs/heads/main.zip" -OutFile $zipPath -UseBasicParsing
                Expand-Archive -Path $zipPath -DestinationPath $extractTemp -Force
                $sourceDir = Join-Path $extractTemp "InsightRAG-main"
                if (Test-Path $sourceDir) {
                    Get-ChildItem -Path $sourceDir | ForEach-Object {
                        $destItem = Join-Path $ProjectRoot $_.Name
                        if ($_.Name -in @("insightforge.db", ".env", "uploads") -and (Test-Path $destItem)) {
                            # Preserve user database, settings, and uploaded files
                        } else {
                            Copy-Item -Path $_.FullName -Destination $ProjectRoot -Recurse -Force
                        }
                    }
                    Remove-Item -Path $extractTemp -Recurse -Force -ErrorAction SilentlyContinue
                    Remove-Item -Path $zipPath -Force -ErrorAction SilentlyContinue
                    cw "[+] Project files updated to latest version!" "Green"
                }
            } catch {
                cw "[!] Could not complete archive update: $_. Proceeding with installed version." "Yellow"
            }
        }
    } else {
        cw "[!] No internet connection detected." "Yellow"
        cw "[*] Proceeding offline with currently installed files..." "Cyan"
    }
} else {
    cw "[*] Continuing with installed version..." "DarkGray"
}

# 1. Python Check & Auto-Installation
$pyExe = $null
$pyVers = $null

function Find-Python {
    $candidates = @("python", "python3", "py", "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe", "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "C:\Program Files\Python311\python.exe", "C:\Program Files\Python312\python.exe")
    foreach ($cand in $candidates) {
        if ($cand -like "*\*" -and -not (Test-Path $cand)) { continue }
        $v = & $cand --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $v -match "Python (\d+\.\d+)") {
            return @{ exe = $cand; version = $Matches[1] }
        }
    }
    return $null
}

$foundPy = Find-Python
if ($foundPy) {
    $pyExe = $foundPy.exe
    $pyVers = $foundPy.version
} else {
    cw "[*] Python 3.10+ not found on your system." "Yellow"
    cw "[*] Automatically downloading and installing Python 3.11 for you..." "Yellow"
    
    # Try via winget first
    $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
    $installedViaWinget = $false
    if ($wingetCmd) {
        cw "  -> Installing via Windows Package Manager (winget)..." "DarkGray"
        winget install Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements 2>&1 | Out-Null
        $installedViaWinget = $true
    }
    
    # If winget failed or not present, download official installer
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
    $foundPy = Find-Python
    if (-not $foundPy) {
        cw "  -> Downloading official Python 3.11 standalone installer..." "DarkGray"
        $pyInstaller = "$env:TEMP\python-3.11.9-amd64.exe"
        try {
            Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -OutFile $pyInstaller -UseBasicParsing
            cw "  -> Running silent installation (adding to PATH)..." "DarkGray"
            Start-Process -FilePath $pyInstaller -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1" -Wait
        } catch {
            cw "[!] Error downloading Python installer: $_" "Red"
        }
    }

    # Refresh environment PATH
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";$env:LOCALAPPDATA\Programs\Python\Python311;$env:LOCALAPPDATA\Programs\Python\Python311\Scripts;$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts"
    
    $foundPy = Find-Python
    if ($foundPy) {
        $pyExe = $foundPy.exe
        $pyVers = $foundPy.version
        cw "[OK] Python ($pyVers) successfully installed!" "Green"
    } else {
        cw "[!] Python installation could not be completed automatically." "Red"
        cw "    Please install Python 3.10+ from https://www.python.org/downloads/ (check 'Add python.exe to PATH') and re-run." "Yellow"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# 2. Node.js & npm Check & Auto-Installation
function Find-Node {
    $candidates = @("node", "npm", "$env:ProgramFiles\nodejs\node.exe", "$env:LOCALAPPDATA\Programs\node\node.exe")
    foreach ($cand in $candidates) {
        if ($cand -like "*\*" -and -not (Test-Path $cand)) { continue }
        $v = & $cand --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $v -match "v(\d+)") {
            return @{ exe = $cand; version = $v }
        }
    }
    return $null
}

$foundNode = Find-Node
if ($foundNode) {
    Write-Step "Checking Node.js & npm environment" "OK" "Green"
} else {
    cw "[*] Node.js is required for InsightRAG Studio UI." "Yellow"
    cw "[*] Automatically installing Node.js LTS for you..." "Yellow"
    $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
    if ($wingetCmd) {
        cw "  -> Installing via Windows Package Manager (winget)..." "DarkGray"
        winget install OpenJS.NodeJS.LTS --silent --accept-source-agreements --accept-package-agreements 2>&1 | Out-Null
    }
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";$env:ProgramFiles\nodejs"
    $foundNode = Find-Node
    if (-not $foundNode) {
        cw "  -> Downloading Node.js LTS installer..." "DarkGray"
        $nodeMsi = "$env:TEMP\node-v20.18.0-x64.msi"
        try {
            Invoke-WebRequest -Uri "https://nodejs.org/dist/v20.18.0/node-v20.18.0-x64.msi" -OutFile $nodeMsi -UseBasicParsing
            cw "  -> Running silent installation..." "DarkGray"
            Start-Process -FilePath "msiexec.exe" -ArgumentList "/i `"$nodeMsi`" /qn /norestart" -Wait
        } catch {
            cw "[!] Error downloading Node.js: $_" "Red"
        }
    }
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";$env:ProgramFiles\nodejs"
    $foundNode = Find-Node
    if ($foundNode) {
        cw "[OK] Node.js ($($foundNode.version)) installed successfully!" "Green"
    } else {
        cw "[!] Node.js could not be installed automatically. Please install Node.js from https://nodejs.org/" "Yellow"
    }
}

# 3. Launch Python Orchestrator (handles banner, Ollama, packages, and servers)
$runnerScript = Join-Path $ProjectRoot "scripts\run_local.py"
& $pyExe $runnerScript
