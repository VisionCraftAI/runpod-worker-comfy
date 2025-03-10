#!/bin/bash

set -e

# Define paths
VENV_PATH="/runpod-volume/venv"
COMFYUI_PATH="/runpod-volume/comfyui"
RP_HANDLER_SCRIPT="/rp_handler.py"
INSTALL_SCRIPT="/install_comfyui.sh"

# Use libtcmalloc for better memory management
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"

# Run install_comfyui.sh
echo "[INFO] Running installing ComfyUI..."
"${INSTALL_SCRIPT}"

# Activate virtual environment
echo "[INFO] Activating virtual environment..."
source "${VENV_PATH}/bin/activate"

echo "[INFO] Starting ComfyUI..."

if [ "$SERVE_API_LOCALLY" == "true" ]; then
    echo "runpod-worker-comfy: Starting ComfyUI (localy)"
    python3 "${COMFYUI_PATH}/main.py" --disable-auto-launch --disable-metadata --listen &
    
    echo "runpod-worker-comfy: Starting RunPod Handler"
    python3 -u "${RP_HANDLER_SCRIPT}" --rp_serve_api --rp_api_host=0.0.0.0
else
    echo "runpod-worker-comfy: Starting ComfyUI (API server)"
    python3 "${COMFYUI_PATH}/main.py" --disable-auto-launch --disable-metadata &
    
    echo "runpod-worker-comfy: Starting RunPod Handler"
    python3 -u "${RP_HANDLER_SCRIPT}"
fi
