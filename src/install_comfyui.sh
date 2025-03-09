#!/bin/bash

set -e

# Define paths
VENV_PATH="/runpod-volume/venv"
COMFYUI_PATH="/runpod-volume/comfyui"
START_SCRIPT="/runpod-volume/start.sh"
RP_HANDLER_SCRIPT="/runpod-volume/rp_handler.py"

# Check if Python virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Setting up Python virtual environment..."
    python3 -m venv "$VENV_PATH"
fi

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Check if ComfyUI is installed
if [ ! -d "$COMFYUI_PATH" ]; then
    echo "Installing ComfyUI dependencies..."
    git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFYUI_PATH"
    cd "$COMFYUI_PATH"
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "ComfyUI already installed. Skipping installation."
fi

# Check and copy necessary scripts
if [ -f "/scripts/start.sh" ]; then
    echo "Copying start.sh to runpod volume..."
    cp /scripts/start.sh "$START_SCRIPT"
    chmod +x "$START_SCRIPT"
else
    echo "Warning: start.sh not found in /scripts."
fi

if [ -f "/scripts/rp_handler.py" ]; then
    echo "Copying rp_handler.py to runpod volume..."
    cp /scripts/rp_handler.py "$RP_HANDLER_SCRIPT"
else
    echo "Warning: rp_handler.py not found in /scripts."
fi

# Execute start script
exec "$START_SCRIPT"
