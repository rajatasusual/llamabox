#!/bin/bash
set -e

# Determine environment (WSL/systemd vs. non-systemd)
VIRT=$(systemd-detect-virt 2>/dev/null || echo "none")
if [[ "$VIRT" == "wsl" ]]; then
    echo "[INFO] Running in WSL environment (systemd mode). Please ensure systemd is enabled in your WSL2 configuration."
else
    echo "[INFO] Running in non-WSL environment (non-systemd mode)."
fi

# Utility functions
print_header() {
    echo "===================================="
    echo "$1"
    echo "===================================="
}

run_update() {
    echo "[INFO] Updating and upgrading system packages..."
    sudo apt update && sudo apt upgrade -y
}

install_package() {
    echo "[INFO] Installing package(s): $*"
    sudo apt install -y "$@"
}

start_service() {
    local service_name="$1"
    local exec_cmd="$2"
    if [[ "$VIRT" != "wsl" ]]; then
        echo "[INFO] Starting $service_name manually..."
        nohup $exec_cmd > "${service_name}.log" 2>&1 &
    else
        echo "[INFO] Setting up systemd service for $service_name..."
        local service_file="/etc/systemd/system/${service_name}.service"
        sudo tee "$service_file" > /dev/null <<EOF
[Unit]
Description=${service_name} Service
After=network.target

[Service]
Type=simple
ExecStart=${exec_cmd}
Restart=on-abnormal
RestartSec=3
User=${USER}
WorkingDirectory=${HOME}
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=${service_name}

[Install]
WantedBy=multi-user.target
EOF
        sudo systemctl daemon-reload
        sudo systemctl enable "${service_name}"
        sudo systemctl start "${service_name}"
    fi
}

check_health() {
    local url="$1"
    local expected="$2"
    sleep 5
    if curl -s -X GET "$url" | grep -q "$expected"; then
        echo "✅ Health check passed for $url"
    else
        echo "❌ Error: Health check failed for $url"
        exit 1
    fi
}

# ------------------------------------------------------------
print_header "Starting wsl-assistant setup..."
run_update

# 1. Install Essential Packages
print_header "1. Install Essential Packages"
install_package curl wget
echo "[INFO] Installing git-lfs..."
curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
install_package git-lfs

# 2. Install Redis Stack Server
print_header "2. Install Redis Stack Server"
install_package lsb-release gpg
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
sudo chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb jammy main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt update
install_package redis-stack-server

if [[ "$VIRT" != "wsl" ]]; then
    echo "[INFO] Starting Redis manually..."
    nohup redis-server > redis.log 2>&1 &
else
    echo "[INFO] Enabling and starting Redis via systemd..."
    sudo systemctl enable redis-stack-server
    sudo systemctl start redis-stack-server
fi

sleep 5
if redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis Stack Server is running."
else
    echo "❌ Error: Redis Stack Server did not start correctly."
fi

# 3. Install Neo4j
print_header "3. Install Neo4j"
echo "[INFO] Installing Oracle JDK 21..."
wget https://download.oracle.com/java/21/latest/jdk-21_linux-x64_bin.deb -O /tmp/jdk-21_linux-x64_bin.deb
sudo dpkg -i /tmp/jdk-21_linux-x64_bin.deb || sudo apt-get install -f -y
echo "[INFO] Java version: $(java --version)"

echo "[INFO] Installing Neo4j..."
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/neotechnology.gpg
echo 'deb [signed-by=/etc/apt/keyrings/neotechnology.gpg] https://debian.neo4j.com stable latest' | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt-get update
install_package neo4j=1:2025.02.0

echo "[INFO] Setting initial password for Neo4j..."
sudo neo4j-admin dbms set-initial-password password

NEO4J_CONF="/etc/neo4j/neo4j.conf"
if grep -q "# server.default_listen_address=0.0.0.0" "$NEO4J_CONF"; then
    echo "[INFO] Updating Neo4j network settings..."
    sudo sed -i 's|# server.default_listen_address=0.0.0.0|server.default_listen_address=0.0.0.0|' "$NEO4J_CONF"
fi

if [[ "$VIRT" != "wsl" ]]; then
    echo "[INFO] Starting Neo4j manually..."
    nohup neo4j console > neo4j.log 2>&1 &
else
    echo "[INFO] Enabling and starting Neo4j via systemd..."
    sudo systemctl enable neo4j
    sudo systemctl start neo4j
fi

sleep 5
if neo4j status | grep -q "is running"; then
    echo "✅ Neo4j is running."
else
    echo "❌ Error: Neo4j did not start correctly."
fi

# 4. Install llama.cpp and AI Models
print_header "4. Install llama.cpp and AI Models"
install_package git cmake ninja-build python3-venv python3-pip

cd "$HOME"
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

cmake --build build --config Release -j "$(nproc)"
sudo cmake --install build --config Release

cd "$HOME"
mkdir -p models
# 4.1 Download Gemma3-1b Quantized Model
echo "[INFO] Downloading Gemma3-1b Quantized Model..."
wget -O models/Gemma3-1b.gguf https://huggingface.co/unsloth/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q2_K_L.gguf 
# 4.2 Download nomic-embed-text-v1.5 Model
echo "[INFO] Downloading nomic-embed-text-v1.5 Model..."
wget -O models/nomic-embed-text-v1.5.gguf https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF/resolve/main/nomic-embed-text-v1.5.Q4_K_S.gguf

# 5. Create and start llama-server service
print_header "5. Setup llama-server"
LLAMA_CMD="/usr/local/bin/llama-server -m $HOME/models/Gemma3-1b.gguf --host 0.0.0.0"
start_service "llama-server" "$LLAMA_CMD"
check_health "http://localhost:8080/health" '"status":"ok"'

# 5.2 Create and start embed-server service
print_header "5.2 Setup embed-server"
EMBED_CMD="/usr/local/bin/llama-server --embedding --port 8000 -ngl 99 -m $HOME/models/nomic-embed-text-v1.5.gguf -c 8192 -b 8192 --rope-scaling yarn --rope-freq-scale .75 --host 0.0.0.0"
start_service "embed-server" "$EMBED_CMD"
check_health "http://localhost:8000/health" '"status":"ok"'

# 6. Download and Configure Redis Worker
print_header "6. Setup Redis Worker"
cd "$HOME"
mkdir -p http-server
cd http-server
curl -o worker.py https://raw.githubusercontent.com/rajatasusual/wsl-assistant/refs/heads/master/scripts/worker.py
chmod +x worker.py
cd "$HOME"
# Create and activate Python virtual environment if not already present
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source ~/venv/bin/activate
pip install rq redis flask requests
deactivate

WORKER_CMD="$HOME/venv/bin/rq worker -u redis://localhost:6379 snippet_queue"
if [[ "$VIRT" != "wsl" ]]; then
    nohup $WORKER_CMD > worker.log 2>&1 &
else
    # Create systemd service for worker
    sudo tee /etc/systemd/system/worker.service > /dev/null <<EOF
[Unit]
Description=RQ Worker Service
After=network.target redis.service

[Service]
Type=simple
User=${USER}
Environment=HOME=${HOME}
ExecStart=${WORKER_CMD}
Restart=on-abnormal
RestartSec=3s

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    sudo systemctl enable worker
    sudo systemctl start worker
fi  

sleep 5
if "$HOME/venv/bin/rq" info --url redis://localhost:6379 | grep -q "snippet_queue"; then
    echo "✅ Redis worker is healthy."
else
    echo "❌ Error: Redis worker health check failed."
    exit 1
fi

# 7. Download and Configure http-server
print_header "7. Setup http-server"
cd "$HOME/http-server"
curl -o http-server.py https://raw.githubusercontent.com/rajatasusual/wsl-assistant/refs/heads/master/scripts/http-server.py
chmod +x http-server.py
cd "$HOME"
source ~/venv/bin/activate
pip install flask
deactivate

HTTP_CMD="$HOME/venv/bin/python $HOME/http-server/http-server.py"
start_service "http-server" "$HTTP_CMD"
check_health "http://localhost:5000/health" '"status":"ok"'

# 8. (WSL Only) Configure auto-restart, security, and Redis persistence
if [[ "$VIRT" == "wsl" ]]; then
    print_header "8. WSL-specific Configuration"
    sudo cp /etc/systemd/system/multi-user.target.wants/neo4j.service /etc/systemd/system/
    echo "[INFO] Configuring auto-restart for Redis..."
    sudo sed -i '/^\[Service\]/a Restart=on-abnormal\nRestartSec=5' /etc/systemd/system/redis-stack-server.service
    sudo systemctl daemon-reload

    echo "[INFO] Securing the server..."
    sudo apt purge -y unattended-upgrades
    install_package ufw fail2ban unattended-upgrades
    sudo sed -i 's/^#*PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config

    echo "[INFO] Configuring UFW..."
    sudo ufw allow ssh
    sudo ufw allow 6379/tcp    # Redis
    sudo ufw allow 7474/tcp    # Neo4j
    sudo ufw allow 8080/tcp    # llama.cpp
    sudo ufw allow 8000/tcp    # embed-server
    sudo ufw allow 5000/tcp    # http-server
    sudo ufw --force enable

    echo "[INFO] Enabling unattended-upgrades..."
    sudo tee /etc/apt/apt.conf.d/50unattended-upgrades > /dev/null <<EOF
Unattended-Upgrade::Origins-Pattern {
    "origin=Debian,codename=\${distro_codename},label=Debian";
    "origin=Debian,codename=\${distro_codename},label=Debian-Security";
    "origin=Debian,codename=\${distro_codename}-security,label=Debian-Security";
};
EOF
    sudo systemctl enable unattended-upgrades

    echo "[INFO] Configuring Fail2Ban..."
    sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
    sudo systemctl restart fail2ban
fi

print_header "Setup Complete"
echo "[INFO] Setup complete. Please verify all services are running."
echo "[INFO] You may wish to reboot your WSL2 instance for all changes to take full effect."
