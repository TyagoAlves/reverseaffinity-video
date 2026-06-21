#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="${BUILD_DIR:-/tmp/reverseaffinity_cpp_build}"

echo "=== reverseaffinity C++ Backend Build ==="

# Detect distro
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID" | tr '[:upper:]' '[:lower:]'
    elif command -v lsb_release &>/dev/null; then
        lsb_release -is | tr '[:upper:]' '[:lower:]'
    else
        echo "unknown"
    fi
}

DISTRO=$(detect_distro)

install_deps() {
    case "$DISTRO" in
        ubuntu|debian|linuxmint|pop|elementary|zorin|kali)
            echo "[INFO] Installing Qt5 + CMake + GCC (apt)..."
            sudo apt update -qq
            sudo apt install -y -qq cmake g++ qtbase5-dev qtchooser qt5-qmake libgl1-mesa-dev
            ;;
        fedora|rhel|centos|rocky|alma)
            echo "[INFO] Installing Qt5 + CMake + GCC (dnf)..."
            sudo dnf install -y cmake gcc-c++ qt5-qtbase-devel mesa-libGL-devel
            ;;
        arch|manjaro|endeavouros|garuda|artix)
            echo "[INFO] Installing Qt5 + CMake + GCC (pacman)..."
            sudo pacman -S --noconfirm cmake gcc qt5-base mesa
            ;;
        opensuse*|suse)
            echo "[INFO] Installing Qt5 + CMake + GCC (zypper)..."
            sudo zypper install -y cmake gcc-c++ libQt5Core-devel Mesa-libGL-devel
            ;;
        alpine)
            echo "[INFO] Installing Qt5 + CMake + GCC (apk)..."
            sudo apk add cmake g++ qt5-qtbase-dev mesa-dev
            ;;
        *)
            echo "[ERROR] Unsupported distro '$DISTRO'. Install Qt5 dev headers manually."
            echo "  Debian/Ubuntu: sudo apt install qtbase5-dev cmake g++"
            echo "  Fedora:        sudo dnf install qt5-qtbase-devel cmake gcc-c++"
            exit 1
            ;;
    esac
}

# Check dependencies
if ! command -v cmake &>/dev/null; then
    echo "[INFO] CMake not found. Installing..."
    install_deps
elif ! command -v qmake &>/dev/null && [ ! -d /usr/include/qt5/QtCore ]; then
    echo "[INFO] Qt5 not found. Installing..."
    install_deps
fi

# Configure
echo ""
echo "=== Configuring CMake ==="
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cmake -S "$PROJECT_DIR" -B "$BUILD_DIR" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    2>&1 || { echo "[ERROR] CMake configure failed."; exit 1; }

# Build
echo ""
echo "=== Building ==="
cmake --build "$BUILD_DIR" -j"$(nproc)" 2>&1

echo ""
echo "=== Build Complete ==="
echo "Binary at: $BUILD_DIR/reverseaffinity"
echo "Run: $BUILD_DIR/reverseaffinity"
