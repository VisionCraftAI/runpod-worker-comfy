#!/usr/bin/env bash

set -e

SNAPSHOT_FILE=$(ls /runpod-volume/*snapshot*.json 2>/dev/null | head -n 1)

if [ -z "$SNAPSHOT_FILE" ]; then
    echo "runpod-worker-comfy: No snapshot file found. Exiting..."
    exit 0
fi

echo "runpod-worker-comfy: restoring snapshot: $SNAPSHOT_FILE"

comfy --workspace /runpod-volume/comfyui node restore-snapshot "$SNAPSHOT_FILE" --pip-non-url

echo "runpod-worker-comfy: restored snapshot file: $SNAPSHOT_FILE"