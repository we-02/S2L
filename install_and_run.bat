@echo off
setlocal enabledelayedexpansion

:: ─── S2L Launcher ────────────────────────────────────────────────────
set REPO_URL=https://github.com/aftabnadim/S2L.git
set INSTALL_DIR=%USERPROFILE%\S2L
set ENV_NAME=S2L
set PYTHON_VER=3.11

echo.
echo  ========================================
echo           S2L Launcher
echo  ========================================
echo.

:: ─── Check conda ─────────────────────────────────────────────────────
where conda >nul 2>&1
if errorlevel 1 (
    echo [ERROR] conda not found. Install Miniconda first:
    echo         https://docs.conda.io/en/latest/miniconda.html
    pause
    exit /b 1
)

:: ─── Check git ───────────────────────────────────────────────────────
where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] git not found. Install Git first:
    echo         https://git-scm.com/download/win
    pause
    exit /b 1
)

:: ─── Clone or update repo ────────────────────────────────────────────
if exist "%INSTALL_DIR%\.git" (
    echo [*] Updating S2L...
    cd /d "%INSTALL_DIR%"
    git pull --ff-only 2>nul || echo [WARN] Could not pull updates, using existing code.
) else (
    echo [*] Cloning S2L...
    git clone "%REPO_URL%" "%INSTALL_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to clone repository.
        pause
        exit /b 1
    )
    cd /d "%INSTALL_DIR%"
)

:: ─── Create conda env if needed ──────────────────────────────────────
conda env list | findstr /b "%ENV_NAME% " >nul 2>&1
if errorlevel 1 (
    echo [*] Creating conda environment '%ENV_NAME%' with Python %PYTHON_VER%...
    call conda create -n %ENV_NAME% python=%PYTHON_VER% -y
    if errorlevel 1 (
        echo [ERROR] Failed to create conda environment.
        pause
        exit /b 1
    )

    echo [*] Installing core dependencies...
    call conda run -n %ENV_NAME% pip install -r requirements.txt
    if errorlevel 1 (
        echo [WARN] Some dependencies failed to install.
    )

    :: ─── GPU Detection ───────────────────────────────────────────────
    echo.
    echo [*] Detecting GPU...
    set HAS_NVIDIA=0
    nvidia-smi >nul 2>&1
    if not errorlevel 1 (
        set HAS_NVIDIA=1
        echo [*] NVIDIA GPU detected.
        echo.
        echo     CUDA acceleration makes segmentation 5-20x faster.
        echo.
        set /p USE_CUDA="    Install PyTorch with CUDA support? [Y/n]: "
        if /i "!USE_CUDA!"=="n" (
            echo [*] Installing PyTorch CPU-only...
            call conda run -n %ENV_NAME% pip install torch torchvision
        ) else (
            echo [*] Installing PyTorch with CUDA...
            call conda run -n %ENV_NAME% pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
        )
    ) else (
        echo [*] No NVIDIA GPU detected. Installing PyTorch CPU-only...
        call conda run -n %ENV_NAME% pip install torch torchvision
    )

    echo.
    echo [*] Setup complete.
    echo.
) else (
    echo [*] Environment '%ENV_NAME%' already exists. Skipping setup.
)

:: ─── Launch ──────────────────────────────────────────────────────────
echo [*] Launching S2L...
echo.
call conda run -n %ENV_NAME% python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] S2L exited with an error.
    pause
)
