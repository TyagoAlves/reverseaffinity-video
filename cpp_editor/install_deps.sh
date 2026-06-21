#!/usr/bin/env bash
set -euo pipefail

echo "=== Installing Qt5 Development Dependencies ==="

# Detect package manager
if command -v apt &>/dev/null; then
    echo "[APT] Installing Qt5 dev packages..."
    sudo apt update
    sudo apt install -y qtbase5-dev qt5-qmake cmake g++ libgl1-mesa-dev
elif command -v dnf &>/dev/null; then
    echo "[DNF] Installing Qt5 dev packages..."
    sudo dnf install -y qt5-qtbase-devel cmake gcc-c++ mesa-libGL-devel
elif command -v pacman &>/dev/null; then
    echo "[PACMAN] Installing Qt5 dev packages..."
    sudo pacman -S --noconfirm qt5-base cmake gcc mesa
elif command -v zypper &>/dev/null; then
    echo "[ZYPPER] Installing Qt5 dev packages..."
    sudo zypper install -y libQt5Widgets-devel cmake gcc-c++ Mesa-libGL-devel
elif command -v apk &>/dev/null; then
    echo "[APK] Installing Qt5 dev packages..."
    sudo apk add qt5-qtbase-dev cmake g++ mesa-dev
else
    echo "Unsupported package manager."
    echo "Please install Qt5 development libraries manually:"
    echo "  Debian/Ubuntu: sudo apt install qtbase5-dev qt5-qmake cmake g++"
    echo "  Fedora:        sudo dnf install qt5-qtbase-devel cmake gcc-c++"
    echo "  Arch:          sudo pacman -S qt5-base cmake gcc"
    exit 1
fi

echo ""
echo "Qt5 development libraries installed successfully."
echo "You can now run: bash build.sh"
