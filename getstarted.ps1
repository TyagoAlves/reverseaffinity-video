param([switch]$Run)
$Host.UI.RawUI.WindowTitle = "reverseaffinity Setup"
Write-Host "=== reverseaffinity Photo Editor - Windows Setup ===" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"
$appDir = "$env:USERPROFILE\reverseaffinity"

function Write-Step($num, $msg) {
    Write-Host "[$num/4] $msg" -ForegroundColor Yellow
}

# --- Step 1: Python ---
Write-Step 1 "Verificando Python..."
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "   Python nao encontrado. Instalando..." -ForegroundColor Yellow
    try {
        winget install --silent --accept-package-agreements Python.Python 2>&1 | Out-Null
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    } catch {
        Write-Host "   Baixando Python manualmente..." -ForegroundColor Yellow
        $url = "https://www.python.org/ftp/python/3.12.5/python-3.12.5-amd64.exe"
        $out = "$env:TEMP\python-installer.exe"
        Invoke-WebRequest -Uri $url -OutFile $out
        Start-Process -Wait -FilePath $out -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1"
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Host "   Python instalado! Feche e reabra o PowerShell, depois execute:" -ForegroundColor Green
        Write-Host "   powershell -ExecutionPolicy Bypass -File \"`$env:TEMP\getstarted.ps1\" -Run" -ForegroundColor Cyan
        pause; exit
    }
}
Write-Host "   $(python --version)" -ForegroundColor Gray

# --- Step 2: Baixar o projeto ---
Write-Step 2 "Baixando reverseaffinity..."
if (Test-Path "$appDir\main.py") {
    Write-Host "   Ja existe. Pulando download." -ForegroundColor Gray
} else {
    Remove-Item -Path "$appDir" -Recurse -Force -ErrorAction SilentlyContinue
    $zipUrl = "https://github.com/TyagoAlves/reverseaffinity/archive/refs/heads/main.zip"
    $zipOut = "$env:TEMP\reverseaffinity.zip"
    Write-Host "   Baixando ZIP..." -ForegroundColor Gray
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipOut
    Write-Host "   Extraindo..." -ForegroundColor Gray
    Expand-Archive -Path $zipOut -DestinationPath "$env:TEMP" -Force
    Remove-Item $zipOut -Force
    Rename-Item "$env:TEMP\reverseaffinity-main" $appDir -ErrorAction SilentlyContinue
    if (-not (Test-Path "$appDir\main.py")) {
        Write-Host "Erro: falha ao baixar o projeto." -ForegroundColor Red
        pause; exit
    }
}

# --- Step 3: Dependencias ---
Write-Step 3 "Instalando dependencias (PyQt5, numpy, Pillow)..."
python -m pip install --upgrade pip -q
python -m pip install -r "$appDir\requirements.txt" -q
Write-Host "   OK" -ForegroundColor Gray

# --- Step 4: Atalho ---
Write-Step 4 "Criando atalho no Desktop..."
try {
    $ws = New-Object -ComObject WScript.Shell
    $shortcut = $ws.CreateShortcut("$env:USERPROFILE\Desktop\reverseaffinity.lnk")
    $shortcut.TargetPath = "python"
    $shortcut.Arguments = "`"$appDir\main.py`""
    $shortcut.WorkingDirectory = $appDir
    $shortcut.Description = "reverseaffinity Photo Editor"
    $shortcut.Save()
    Write-Host "   Atalho criado em: Area de Trabalho\reverseaffinity.lnk" -ForegroundColor Gray
} catch {
    Write-Host "   Aviso: nao foi possivel criar atalho (COM desabilitado)." -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "=== Instalacao concluida! ===" -ForegroundColor Green
Write-Host "Para iniciar:" -ForegroundColor White
Write-Host "   1. Clique no atalho 'reverseaffinity' na Area de Trabalho" -ForegroundColor Cyan
Write-Host "   2. Ou execute: python `"$appDir\main.py`"" -ForegroundColor Cyan
Write-Host ""

if ($Run) {
    Write-Host "Iniciando editor..." -ForegroundColor Yellow
    Set-Location $appDir
    python main.py
}
