# Stage 1: Base image with common dependencies
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 as base

# Prevents prompts from packages asking for user input during installation
ENV DEBIAN_FRONTEND=noninteractive
# Prefer binary wheels over source distributions for faster pip installations
ENV PIP_PREFER_BINARY=1
# Ensures output from python is printed immediately to the terminal without buffering
ENV PYTHONUNBUFFERED=1 
# Speed up some cmake builds
ENV CMAKE_BUILD_PARALLEL_LEVEL=8

# Install Python, git and other necessary tools
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3.10-venv \
    git \
    wget \
    libgl1 \
    && ln -sf /usr/bin/python3.10 /usr/bin/python \
    && ln -sf /usr/bin/pip3 /usr/bin/pip

# Clean up to reduce image size
RUN apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Copy install and start scripts from src directory
COPY src/install_comfyui.sh /install_comfyui.sh
COPY src/start.sh /start.sh
COPY src/rp_handler.py /rp_handler.py
COPY src/images_utils.py /images_utils.py
COPY requirements.txt requirements.txt

# Add validation schemas
COPY schemas /schemas

# Ensure scripts are executable
RUN chmod +x /install_comfyui.sh /start.sh /rp_handler.py requirements.txt

# Set entrypoint to installation script
ENTRYPOINT ["/start.sh"]
