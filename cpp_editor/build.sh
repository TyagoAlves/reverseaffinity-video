#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="/tmp/reverseaffinity_build"
QT_LOCAL_DIR="$PROJECT_DIR/qt_local/gcc_64"

echo "=== reverseaffinity Build Script ==="

# ---- detect Linux distro ----
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

install_qt5_system() {
    case "$DISTRO" in
        ubuntu|debian|linuxmint|pop|elementary|zorin|kali)
            echo "[INFO] Detected Debian/Ubuntu ($DISTRO). Installing Qt5 via apt..."
            sudo apt update -qq
            sudo apt install -y -qq cmake g++ qtbase5-dev qtchooser qt5-qmake libgl1-mesa-dev
            ;;
        fedora|rhel|centos|rocky|alma)
            echo "[INFO] Detected RHEL/Fedora ($DISTRO). Installing Qt5 via dnf..."
            if command -v dnf &>/dev/null; then
                sudo dnf install -y cmake gcc-c++ qt5-qtbase-devel mesa-libGL-devel
            else
                sudo yum install -y cmake gcc-c++ qt5-qtbase-devel mesa-libGL-devel
            fi
            ;;
        arch|manjaro|endeavouros|garuda|artix)
            echo "[INFO] Detected Arch Linux ($DISTRO). Installing Qt5 via pacman..."
            sudo pacman -S --noconfirm cmake gcc qt5-base mesa
            ;;
        opensuse*|suse)
            echo "[INFO] Detected openSUSE ($DISTRO). Installing Qt5 via zypper..."
            sudo zypper install -y cmake gcc-c++ libQt5Core-devel Mesa-libGL-devel
            ;;
        alpine)
            echo "[INFO] Detected Alpine ($DISTRO). Installing Qt5 via apk..."
            sudo apk add cmake g++ qt5-qtbase-dev mesa-dev
            ;;
        void)
            echo "[INFO] Detected Void Linux ($DISTRO). Installing Qt5 via xbps..."
            sudo xbps-install -Sy cmake gcc qt5-devel Mesa-devel
            ;;
        gentoo)
            echo "[INFO] Detected Gentoo ($DISTRO). Installing Qt5 via emerge..."
            sudo emerge dev-util/cmake sys-devel/gcc dev-qt/qtcore:5 media-libs/mesa
            ;;
        *)
            echo "[WARNING] Unknown distro '$DISTRO'. Trying apt as fallback..."
            sudo apt update -qq 2>/dev/null || true
            sudo apt install -y -qq cmake g++ qtbase5-dev qtchooser qt5-qmake libgl1-mesa-dev 2>/dev/null || {
                echo "[ERROR] Could not install Qt5. Please install qtbase5-dev (Debian/Ubuntu),"
                echo "  qt5-qtbase-devel (Fedora), or qt5-base (Arch) manually."
                exit 1
            }
            ;;
    esac
}

# ---- ensure Qt5 is available ----
if command -v qmake &>/dev/null && [ -d /usr/include/qt5/QtCore ]; then
    echo "[OK] System Qt5 detected (qmake: $(qmake --version 2>&1 | head -1))"
elif [ -d "$QT_LOCAL_DIR/include/QtCore" ]; then
    echo "[OK] Local Qt5 headers at $QT_LOCAL_DIR"
else
    echo "[INFO] Qt5 not found. Installing system Qt5 for $DISTRO..."
    install_qt5_system
    if ! command -v qmake &>/dev/null || [ ! -d /usr/include/qt5/QtCore ]; then
        echo "[WARNING] System Qt5 install might have failed. Falling back to aqtinstall..."
        QT_TMP=$(mktemp -d)
        if python3 -c "import aqt" 2>/dev/null; then
            AQT_CMD="python3 -m aqt"
        else
            pip install aqtinstall -q --break-system-packages 2>/dev/null || pip install aqtinstall -q 2>/dev/null || true
            AQT_CMD="python3 -m aqt"
        fi
        if python3 -c "import aqt" 2>/dev/null; then
            $AQT_CMD install-qt linux desktop 5.15.2 gcc_64 -O "$QT_TMP" 2>&1
            rm -rf "$QT_LOCAL_DIR"
            mkdir -p "$PROJECT_DIR/qt_local"
            (cd "$QT_TMP/5.15.2" && tar cf - gcc_64 --dereference) | (cd "$PROJECT_DIR/qt_local" && tar xf - 2>/dev/null || true)
            rm -rf "$QT_TMP"
            echo "[OK] Qt5 downloaded to $QT_LOCAL_DIR"
        else
            echo "[ERROR] Could not install Qt5 via aqtinstall either."
            echo "  Please install Qt5 dev headers manually."
            exit 1
        fi
    fi
fi

# ---- configure CMake ----
echo ""
echo "=== Configuring CMake ==="
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cmake -S "$PROJECT_DIR" -B "$BUILD_DIR" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_PREFIX_PATH="$QT_LOCAL_DIR" \
    2>&1 || { echo "CMake configure failed."; exit 1; }

# ---- build ----
echo ""
echo "=== Building ==="
cmake --build "$BUILD_DIR" -j"$(nproc)" 2>&1

echo ""
echo "=== Build Complete ==="
echo "Binary at: $BUILD_DIR/reverseaffinity"
echo ""
echo "To run: $BUILD_DIR/reverseaffinity"
