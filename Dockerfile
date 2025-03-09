FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 as base

# Prevents prompts from packages asking for user input during installation
ENV DEBIAN_FRONTEND=noninteractive
# Prefer binary wheels over source distributions for faster pip installations
ENV PIP_PREFER_BINARY=1
# Ensures output from python is printed immediately to the terminal without buffering
ENV PYTHONUNBUFFERED=1 
# Speed up some cmake builds
ENV CMAKE_BUILD_PARALLEL_LEVEL=8

# Install Python, git, and other necessary tools
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3.10-venv \
    python3.10-distutils \
    python3.10-ensurepip \
    git \
    wget \
    libgl1 \
    && ln -sf /usr/bin/python3.10 /usr/bin/python \
    && ln -sf /usr/bin/pip3 /usr/bin/pip

# Ensure pip and virtualenv support is available
RUN python3 -m ensurepip --default-pip && pip install --upgrade pip

# Clean up to reduce image size
RUN apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Copy install and start scripts from src directory
COPY src/install_comfyui.sh /scripts/install_comfyui.sh
COPY src/start.sh /scripts/start.sh
COPY src/rp_handler.py /scripts/rp_handler.py

# Ensure scripts are executable
RUN chmod +x /scripts/install_comfyui.sh /scripts/start.sh /scripts/rp_handler.py

# Set entrypoint to installation script
ENTRYPOINT ["/scripts/install_comfyui.sh"]
