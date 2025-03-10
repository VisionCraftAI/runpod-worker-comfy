#!/bin/bash

set -e

# Define paths
VENV_PATH="/runpod-volume/venv"
COMFYUI_PATH="/runpod-volume/comfyui"
RUNPOD_REQUIREMENTS_FILE="/runpod-volume/requirements.txt"
REQUIREMENTS_FILE="/requirements.txt"

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
    
    
    # Export current packages to file
    echo "[INFO] Exporting list of installed packages..."
    pip list --format=freeze > /installed_packages.txt
    echo "[INFO] Package list exported to /installed_packages.txt"

    echo "[INFO] Installing installed_packages.txt"
    # Activate the virtual environment
    source "$VENV_PATH/bin/activate"
    pip install -r /installed_packages.txt
    # closing the virtual environment
    deactivate
    
fi

# Verify virtual environment activation script exists
if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "[ERROR] Virtual environment activation script still not found. Exiting."
    exit 1
fi

# Activate virtual environment
echo "[INFO] Activating virtual environment."
source "$VENV_PATH/bin/activate"

# Install from /requirements.txt if present
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "[INFO] Installing packages from requirements.txt..."
    pip install -r "$REQUIREMENTS_FILE"
    echo "[INFO] Requirements installation completed."
fi

# Install from /runpod-volume/requirements.txt if present
if [ -f "$RUNPOD_REQUIREMENTS_FILE" ]; then
    echo "[INFO] Installing packages from requirements.txt..."
    pip install -r "$RUNPOD_REQUIREMENTS_FILE"
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

