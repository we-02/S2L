#!/usr/bin/env bash
set -e

REPO_URL="https://github.com/aftabnadim/S2L.git"
INSTALL_DIR="$HOME/S2L"
ENV_NAME="S2L"
PYTHON_VER="3.11"

echo ""
echo "  ========================================"
echo "           S2L Launcher"
echo "  ========================================"
echo ""

# ─── Check conda ─────────────────────────────────────────────────────
if ! command -v conda &>/dev/null; then
    echo "[ERROR] conda not found. Install Miniconda first:"
    echo "        https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# ─── Check git ───────────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
    echo "[ERROR] git not found."
    exit 1
fi

# ─── Clone or update repo ────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "[*] Updating S2L..."
    cd "$INSTALL_DIR"
    git pull --ff-only 2>/dev/null || echo "[WARN] Could not pull updates."
else
    echo "[*] Cloning S2L..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ─── Create conda env if needed ──────────────────────────────────────
FIRST_RUN=0
if ! conda env list | grep -q "^${ENV_NAME} "; then
    FIRST_RUN=1
    echo "[*] Creating conda environment '${ENV_NAME}' with Python ${PYTHON_VER}..."
    conda create -n "$ENV_NAME" python="$PYTHON_VER" -y
else
    echo "[*] Environment '${ENV_NAME}' exists."
fi

# ─── Always sync requirements ─────────────────────────────────────────
echo "[*] Syncing dependencies..."
conda run -n "$ENV_NAME" pip install -r requirements.txt --quiet 2>/dev/null || \
    echo "[WARN] Some dependencies failed."

# ─── GPU setup (first run only) ──────────────────────────────────────
if [ "$FIRST_RUN" -eq 1 ]; then
    echo ""
    OS="$(uname)"

    if [[ "$OS" == "Darwin" ]]; then
        echo "[*] macOS detected. Installing PyTorch CPU-only..."
        conda run -n "$ENV_NAME" pip install torch torchvision --quiet
    elif command -v nvidia-smi &>/dev/null; then
        echo "[*] NVIDIA GPU detected."
        echo ""
        echo "    CUDA acceleration makes segmentation 5-20x faster."
        echo ""
        read -p "    Install PyTorch with CUDA support? [Y/n]: " USE_CUDA
        if [[ "$USE_CUDA" =~ ^[Nn]$ ]]; then
            echo "[*] Installing PyTorch CPU-only..."
            conda run -n "$ENV_NAME" pip install torch torchvision --quiet
        else
            echo "[*] Installing PyTorch with CUDA..."
            conda run -n "$ENV_NAME" pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
        fi
    else
        echo "[*] No NVIDIA GPU detected. Installing PyTorch CPU-only..."
        conda run -n "$ENV_NAME" pip install torch torchvision --quiet
    fi

    echo ""
    echo "[*] Setup complete."
    echo ""
fi

# ─── Launch ──────────────────────────────────────────────────────────
echo "[*] Launching S2L..."
echo ""
conda run -n "$ENV_NAME" python main.py
