#!/bin/bash

set -e

# Define paths
VENV_PATH="/runpod-volume/venv"
COMFYUI_PATH="/runpod-volume/comfyui"
START_SCRIPT="/runpod-volume/start.sh"
RP_HANDLER_SCRIPT="/runpod-volume/rp_handler.py"
REQUIREMENTS_FILE="/runpod-volume/requirements.txt"

echo "[INFO] Starting installation script."

# Ensure the runpod-volume directory exists
if [ ! -d "/runpod-volume" ]; then
    echo "[ERROR] /runpod-volume directory does not exist. Please ensure it is created before running this script."
    exit 1
fi

# Check if Python virtual environment exists
if [ ! -d "$VENV_PATH" ] || [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "[INFO] Virtual environment not found. Creating a new one."
    rm -rf "$VENV_PATH"  # Remove any broken venv
    python3 -m venv "$VENV_PATH"
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment. Exiting."
        exit 1
    fi
    echo "[INFO] Virtual environment created successfully."
    
    # Activate the virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Export current packages to file
    echo "[INFO] Exporting list of installed packages..."
    pip list --format=freeze > /runpod-volume/installed_packages.txt
    echo "[INFO] Package list exported to /runpod-volume/installed_packages.txt"
    echo "[INFO] Installing installed_packages.txt"
    pip install -r /runpod-volume/installed_packages.txt
fi

# Verify virtual environment activation script exists
if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "[ERROR] Virtual environment activation script still not found. Exiting."
    exit 1
fi

# Activate virtual environment
echo "[INFO] Activating virtual environment."
source "$VENV_PATH/bin/activate"

# Install PyTorch with CUDA 11.8 support
echo "[INFO] Installing PyTorch with CUDA 11.8 support..."
python -m pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu118
echo "[INFO] PyTorch installation completed."

# Check if requirements.txt exists in /runpod-volume, copy from root if not present
if [ ! -f "$REQUIREMENTS_FILE" ] && [ -f "/requirements.txt" ]; then
    echo "[INFO] Copying requirements.txt from root to /runpod-volume."
    cp /requirements.txt "$REQUIREMENTS_FILE"
elif [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "[WARNING] requirements.txt not found in root or /runpod-volume."
else
    echo "[INFO] requirements.txt already exists in /runpod-volume. Skipping copy."
fi

# Install from requirements.txt if present (separate command)
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "[INFO] Installing packages from requirements.txt..."
    pip install -r "$REQUIREMENTS_FILE"
    echo "[INFO] Requirements installation completed."
fi

# Check if ComfyUI is installed
if [ ! -d "$COMFYUI_PATH" ]; then
    echo "[INFO] ComfyUI not found. Installing..."
    git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFYUI_PATH"
    cd "$COMFYUI_PATH"
    echo "[INFO] Upgrading pip."
    pip install --upgrade pip
    echo "[INFO] Installing ComfyUI dependencies."
    pip install -r requirements.txt
    echo "[INFO] ComfyUI installation completed."
else
    echo "[INFO] ComfyUI already installed. Skipping installation."
fi

# Check and copy necessary scripts
if [ -f "/scripts/start.sh" ] && [ ! -f "$START_SCRIPT" ]; then
    echo "[INFO] Copying start.sh to /runpod-volume."
    cp /scripts/start.sh "$START_SCRIPT"
    chmod +x "$START_SCRIPT"
elif [ -f "$START_SCRIPT" ]; then
    echo "[INFO] start.sh already exists in /runpod-volume. Skipping copy."
else
    echo "[WARNING] start.sh not found in /scripts. Skipping copy."
fi

if [ -f "/scripts/rp_handler.py" ] && [ ! -f "$RP_HANDLER_SCRIPT" ]; then
    echo "[INFO] Copying rp_handler.py to /runpod-volume."
    cp /scripts/rp_handler.py "$RP_HANDLER_SCRIPT"
    chmod +x "$RP_HANDLER_SCRIPT"
elif [ -f "$RP_HANDLER_SCRIPT" ]; then
    echo "[INFO] rp_handler.py already exists in /runpod-volume. Skipping copy."
else
    echo "[WARNING] rp_handler.py not found in /scripts. Skipping copy."
fi

echo "[INFO] Installation script completed. Starting ComfyUI..."

# Execute start script
exec "$START_SCRIPT"
