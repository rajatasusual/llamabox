#!/bin/bash
set -e

# Detect if running in WSL
VIRT=$(systemd-detect-virt 2>/dev/null || echo "none")

# ============================================================
# setup.sh - Automated setup for wsl-assistant on Debian in WSL2
# ============================================================
# NOTE: This script is intended to be run inside your Debian
# instance in WSL2. Ensure systemd is enabled in your WSL2
# configuration (see /etc/wsl.conf) before running. Otherwise 
# the script only runs the services in the background, meaning
# they will not be restarted automatically on reboot.
# ============================================================

if [[ "$VIRT" != "wsl" ]]; then
    echo "Running in non WSL environment (non-systemd mode)."
else 
    echo "Running in WSL environment (systemd mode)."
    echo "Please ensure systemd is enabled in your WSL2 configuration."
fi

echo "===================================="
echo "Starting wsl-assistant setup..."
echo "===================================="

# Update and upgrade system packages
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# ----------------------------------------
# 1. Install Essential Packages
# ----------------------------------------
echo "Installing essential packages..."
sudo apt install -y curl wget

# ----------------------------------------
# 2. Install Redis Stack Server
# ----------------------------------------
echo "Installing Redis Stack Server..."
sudo apt-get install -y lsb-release gpg
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
sudo chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb jammy main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt update
sudo apt install -y redis-stack-server
if [[ "$VIRT" != "wsl" ]]; then
    echo "Starting Redis manually..."
    nohup redis-server > redis.log 2>&1 &
else
    echo "Starting Redis with systemd..."
    sudo systemctl enable redis-stack-server
    sudo systemctl start redis-stack-server
fi

sleep 5
if redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis Stack Server is running."
else
    echo "❌ Error: Redis Stack Server did not start correctly."
fi

# ----------------------------------------
# 3. Install Neo4j
# ----------------------------------------
echo "Installing Oracle JDK 21 for Neo4j..."
wget https://download.oracle.com/java/21/latest/jdk-21_linux-x64_bin.deb -O /tmp/jdk-21_linux-x64_bin.deb
sudo dpkg -i /tmp/jdk-21_linux-x64_bin.deb || sudo apt-get install -f -y
echo "Java version: $(java --version)"

echo "Installing Neo4j..."
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/neotechnology.gpg
echo 'deb [signed-by=/etc/apt/keyrings/neotechnology.gpg] https://debian.neo4j.com stable latest' | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt-get update
sudo apt-get install -y neo4j=1:2025.02.0

echo "Setting initial password for Neo4j..."
sudo neo4j-admin dbms set-initial-password password

NEO4J_CONF="/etc/neo4j/neo4j.conf"
if grep -q "# server.default_listen_address=0.0.0.0" "$NEO4J_CONF"; then
    echo "Updating Neo4j network settings..."
    sudo sed -i 's|# server.default_listen_address=0.0.0.0|server.default_listen_address=0.0.0.0|' "$NEO4J_CONF"
fi
if [[ "$VIRT" != "wsl" ]]; then
    echo "Starting Neo4j manually..."
    nohup neo4j console > neo4j.log 2>&1 &
else
    echo "Starting Neo4j with systemd..."
    sudo systemctl enable neo4j
    sudo systemctl start neo4j
fi

sleep 5
if neo4j status | grep -q "is running"; then
    echo "✅ Neo4j is running."
else
    echo "❌ Error: Neo4j did not start correctly."
fi

# ----------------------------------------
# 4. Install llama.cpp and AI Models
# ----------------------------------------
echo "Installing llama.cpp dependencies and building the project..."
sudo apt install -y git cmake ninja-build python3-venv python3-pip
cd $HOME
if [ ! -d "llama.cpp" ]; then
    git clone https://github.com/ggml-org/llama.cpp.git
fi
cd llama.cpp
git submodule update --init --recursive

cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_EXAMPLES=ON \
  -DLLAMA_BUILD_SERVER=ON \
  -DBUILD_SHARED_LIBS=OFF

cmake --build build --config Release -j $(nproc)
sudo cmake --install build --config Release

echo "Installing Git LFS for model download..."
cd $HOME
curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
sudo apt-get install git-lfs
# ----------------------------------------
# 4.1 Downloading SmolLM2-360M-Instruct Model
# ----------------------------------------
if [ ! -d "SmolLM2-360M-Instruct" ]; then
    echo "Cloning SmolLM2-360M-Instruct model repository..."
    GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct
    cd SmolLM2-360M-Instruct
    git lfs pull --include="model.safetensors"
    cd $HOME
else
    echo "SmolLM2-360M-Instruct model repository already exists."
fi

echo "Setting up Python environment for model conversion..."
cd $HOME
mkdir models
python3 -m venv ~/venv
source ~/venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
python -m pip install --upgrade -r $HOME/llama.cpp/requirements/requirements-convert_hf_to_gguf.txt

echo "Converting and quantizing model..."
python $HOME/llama.cpp/convert_hf_to_gguf.py SmolLM2-360M-Instruct --outfile $HOME/models/SmolLM2.gguf
llama-quantize $HOME/models/SmolLM2.gguf $HOME/models/SmolLM2.q8.gguf Q8_0 4
deactivate

# ----------------------------------------
# 4.2 Downloading nomic-embed-text-v1.5-GGUF Model
# ----------------------------------------
if [ ! -d "nomic-embed-text-v1.5-GGUF" ]; then
    echo "Cloning nomic-embed-text-v1.5-GGUF model repository..."
    GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF
    cd nomic-embed-text-v1.5-GGUF
    git lfs pull --include "nomic-embed-text-v1.5.Q2_K.gguf"
    mv nomic-embed-text-v1.5.Q2_K.gguf $HOME/models/nomic-embed-text-v1.5.gguf
    cd $HOME
else
    echo "nomic-embed-text-v1.5-GGUF model repository already exists."
fi

# ----------------------------------------
# 5. Create systemd service for llama-server
# ----------------------------------------
echo "Creating service for llama-server..."
if [[ "$VIRT" != "wsl" ]]; then
    nohup llama-server -m $HOME/models/SmolLM2.q8.gguf > llama-server.log 2>&1 &
else 
    sudo tee /etc/systemd/system/llama-server.service > /dev/null <<EOF
[Unit]
Description=llama-server Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/llama-server -m $HOME/models/SmolLM2.q8.gguf --host 0.0.0.0
Restart=on-abnormal
RestartSec=3
User=$USER
WorkingDirectory=$HOME
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=llama-server

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    sudo systemctl enable llama-server
    sudo systemctl start llama-server
fi

sleep 5
if curl -s -X GET http://localhost:8080/health | grep -q '"status":"ok"'; then
    echo "✅ llama-server is healthy."
else
    echo "❌ Error: llama-server health check failed."
    exit 1
fi

# ----------------------------------------
# 5.2 create embeddings server with nomic-embed-text-v1.5
# ----------------------------------------
echo "Creating service for embed-server..."
if [[ "$VIRT" != "wsl" ]]; then
    nohup llama-server --embedding --port 8000 -ngl 99 -m $HOME/models/nomic-embed-text-v1.5.gguf -c 8192 -b 8192 --rope-scaling yarn --rope-freq-scale .75 > embedding-server.log 2>&1 &
else 
    sudo tee /etc/systemd/system/embed-server.service > /dev/null <<EOF
[Unit]
Description=embed-server Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/llama-server --embedding --port 8000 -ngl 99 -m $HOME/models/nomic-embed-text-v1.5.gguf -c 8192 -b 8192 --rope-scaling yarn --rope-freq-scale .75 --host 0.0.0.0
Restart=on-abnormal
RestartSec=3
User=$USER
WorkingDirectory=$HOME
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=embed-server

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    sudo systemctl enable embed-server
    sudo systemctl start embed-server
fi

sleep 5
if curl -s -X GET http://localhost:8000/health | grep -q '"status":"ok"'; then
    echo "✅ llama-server is healthy."
else
    echo "❌ Error: llama-server health check failed."
    exit 1
fi
# ----------------------------------------
# 6. Download and Configure http-server.py
# ----------------------------------------
echo "Downloading http-server.py..."
mkdir http-server
cd http-server
curl -o http-server.py https://raw.githubusercontent.com/rajatasusual/wsl-assistant/refs/heads/master/scripts/http-server.py
chmod +x http-server.py
cd $HOME
source ~/venv/bin/activate
echo "Installing Flask..."
pip install Flask
deactivate

if [[ "$VIRT" != "wsl" ]]; then
    nohup $HOME/venv/bin/python $HOME/http-server/http-server.py > http-server.log 2>&1 &
else 
    # ----------------------------------------
    # 7. Create systemd service for http-server
    # ----------------------------------------
    echo "Creating systemd service for http-server..."
    sudo tee /etc/systemd/system/http-server.service > /dev/null <<EOF
[Unit]
Description=http-server Service
After=network.target

[Service]
Type=simple
ExecStart=$HOME/venv/bin/python $HOME/http-server/http-server.py
Restart=on-abnormal
RestartSec=3
User=$USER
WorkingDirectory=$HOME/http-server
Environment=PYTHONUNBUFFERED=1
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=http-server

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    sudo systemctl enable http-server
    sudo systemctl start http-server
fi  
    
sleep 5
if curl -s -X GET http://localhost:5000/health | grep -q '"status":"ok"'; then
    echo "✅ http-server is healthy."
else
    echo "❌ Error: http-server health check failed."
    exit 1
fi


if [[ "$VIRT" == "wsl" ]]; then
    # ----------------------------------------
    # 8. Configure Auto-Restart for Redis and Neo4j
    # ----------------------------------------
    echo "Configuring auto-restart for Redis and Neo4j..."
    sudo sed -i '/^\[Service\]/a Restart=on-abnormal\nRestartSec=5' /lib/systemd/system/neo4j.service
    sudo sed -i '/^\[Service\]/a Restart=on-abnormal\nRestartSec=5' /lib/systemd/system/redis-stack-server.service
    sudo systemctl daemon-reload
    # ----------------------------------------
    # 9. Secure the Server
    # ----------------------------------------
    echo "Securing the server..."
    sudo apt purge -y unattended-upgrades
    sudo apt install -y ufw fail2ban unattended-upgrades openssh-server
    sudo sed -i 's/^#*PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
    sudo systemctl restart ssh

    echo "Configuring UFW..."
    sudo ufw allow ssh
    sudo ufw allow 6379/tcp    # Redis
    sudo ufw allow 7474/tcp    # Neo4j
    sudo ufw allow 8080/tcp    # llama.cpp (assumed port)
    sudo ufw --force enable

    echo "Enabling unattended-upgrades..."
    sudo tee /etc/apt/apt.conf.d/50unattended-upgrades > /dev/null <<EOF
Unattended-Upgrade::Origins-Pattern {
"origin=Debian,codename=\${distro_codename},label=Debian";
"origin=Debian,codename=\${distro_codename},label=Debian-Security";
"origin=Debian,codename=\${distro_codename}-security,label=Debian-Security";
};
EOF
    sudo systemctl enable unattended-upgrades

    echo "Configuring Fail2Ban..."
    sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
    sudo sed -i '/^\[sshd\]/,/^$/c\[sshd]\nenabled = true\nbackend = systemd\n' /etc/fail2ban/jail.local
    sudo systemctl restart fail2ban

    echo "Configuring Redis persistence..."
    echo "save 900 1" | sudo tee -a /etc/redis-stack.conf
    sudo systemctl restart redis-stack-server
fi

# ----------------------------------------
# 10. Finalize Setup
# ----------------------------------------
echo "===================================="
echo "Setup complete. Please verify all services are running."
echo "You may wish to reboot your WSL2 instance for all changes to take full effect."
echo "===================================="
