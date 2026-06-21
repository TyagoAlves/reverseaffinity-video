# reverseaffinity Windows Build Script
# Run in PowerShell as Administrator

Write-Host "=== reverseaffinity Windows Build ===" -ForegroundColor Cyan

# 1. Check prerequisites
$missing = @()
if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) { $missing += "cmake (install with: winget install Kitware.CMake)" }
if (-not (Get-Command qmake -ErrorAction SilentlyContinue)) { $missing += "Qt5 (install from: https://www.qt.io/download-open-source)" }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { $missing += "git (install with: winget install Git.Git)" }
if (-not (Get-Command cl -ErrorAction SilentlyContinue)) {
    Write-Host "  [WARN] MSVC not found. Install Visual Studio 2022 Build Tools with C++ workload." -ForegroundColor Yellow
    $missing += "MSVC C++ compiler"
}
if ($missing.Count -gt 0) {
    Write-Host "Missing prerequisites:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host "Install missing tools, then re-run this script." -ForegroundColor Yellow
    exit 1
}

# 2. Detect Qt5 path
$qt5Path = $env:Qt5_DIR
if (-not $qt5Path) {
    $paths = @(
        "C:\Qt\5.15.2\msvc2019_64",
        "C:\Qt\5.15.2\mingw81_64",
        "C:\Qt\5.12.12\msvc2019_64",
        "$env:USERPROFILE\Qt\5.15.2\msvc2019_64"
    )
    foreach ($p in $paths) {
        if (Test-Path "$p\lib\cmake\Qt5Config.cmake") {
            $qt5Path = $p
            break
        }
    }
}
if (-not $qt5Path) {
    Write-Host "Qt5 not found. Set Qt5_DIR or install Qt5." -ForegroundColor Red
    exit 1
}
Write-Host "Qt5 found at: $qt5Path" -ForegroundColor Green

# 3. Determine build directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildDir = "$env:TEMP\reverseaffinity_win_build"
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null

# 4. Detect GPU (NVIDIA)
try {
    $gpu = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -match "NVIDIA|Quadro|Tesla|RTX|GeForce" } | Select-Object -First 1
    if ($gpu) {
        Write-Host "Dedicated GPU detected: $($gpu.Name)" -ForegroundColor Green
        Write-Host "  App will use NVIDIA GPU for OpenGL acceleration." -ForegroundColor Green
    }
} catch {
    Write-Host "  Could not detect GPU info." -ForegroundColor Yellow
}

# 5. Configure CMake with GPU options
cd $scriptDir
cmake -S . -B $buildDir `
    -DCMAKE_PREFIX_PATH="$qt5Path" `
    -DCMAKE_BUILD_TYPE=Release `
    -DUSE_GPU_ACCELERATION=ON 2>&1 | ForEach-Object { Write-Host $_ }

if ($LASTEXITCODE -ne 0) {
    Write-Host "CMake configure failed!" -ForegroundColor Red
    exit 1
}

# 6. Build
Write-Host "=== Building ===" -ForegroundColor Cyan
cmake --build $buildDir --config Release --parallel 2>&1 | ForEach-Object { Write-Host $_ }

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

# 7. Show results
$binary = "$buildDir\Release\reverseaffinity.exe"
if (-not (Test-Path $binary)) {
    $binary = "$buildDir\reverseaffinity.exe"
}
if (Test-Path $binary) {
    $size = (Get-Item $binary).Length / 1KB
    Write-Host "=== Build Complete ===" -ForegroundColor Cyan
    Write-Host "Binary at: $binary" -ForegroundColor Green
    Write-Host "Size: $([math]::Round($size, 0)) KB" -ForegroundColor Green
} else {
    Write-Host "Binary not found at expected paths." -ForegroundColor Red
    dir "$buildDir\*.exe" -Recurse -ErrorAction SilentlyContinue
}
