#!/bin/bash
set -e

sudo cp box.sh /usr/local/bin/box
sudo chmod +x /usr/local/bin/box
box box log_info || echo "Command failed. Check if box.sh exists and contains box log_info function."

# ---------------------------
# Global Directory Variables
# ---------------------------
MODEL_DIR="models"
HTTP_DIR="http-server"
VENV_DIR="venv"

# ---------------------------
# Begin Setup
# ---------------------------
box print_header "Starting llamabox setup..."
box run_update

# 1. Install Essential Packages
box print_header "1. Install Essential Packages"
box install_package curl wget
box log_info "Installing git-lfs..."
curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
box install_package git-lfs

# 2. Install Redis Stack Server
box print_header "2. Install Redis Stack Server"
box install_package lsb-release gpg
box download_file "https://packages.redis.io/gpg" "/tmp/redis.gpg"
sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg < /tmp/redis.gpg
sudo chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb jammy main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt update
box install_package redis-stack-server

if [[ "$VIRT" != "wsl" ]]; then
    box log_info "Starting Redis manually..."
    nohup redis-server > redis.log 2>&1 &
else
    box log_info "Enabling and starting Redis via systemd..."
    sudo systemctl enable redis-stack-server
    sudo systemctl start redis-stack-server
fi

sleep 5
if redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis Stack Server is running."
else
    echo "❌ Error: Redis Stack Server did not start correctly."
fi

# 3. Install Neo4j and JDK 21
box print_header "3. Install Neo4j"
box log_info "Installing Oracle JDK 21..."
box download_file "https://download.oracle.com/java/21/latest/jdk-21_linux-x64_bin.deb" "/tmp/jdk-21_linux-x64_bin.deb"
sudo dpkg -i /tmp/jdk-21_linux-x64_bin.deb || sudo apt-get install -f -y
box log_info "Java version: $(java --version)"

box log_info "Installing Neo4j..."
box download_file "https://debian.neo4j.com/neotechnology.gpg.key" "/tmp/neo4j.gpg.key"
sudo gpg --dearmor -o /etc/apt/keyrings/neotechnology.gpg < /tmp/neo4j.gpg.key
echo 'deb [signed-by=/etc/apt/keyrings/neotechnology.gpg] https://debian.neo4j.com stable latest' | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt update
box install_package neo4j=1:2025.02.0

box log_info "Setting initial password for Neo4j..."
sudo neo4j-admin dbms set-initial-password password

NEO4J_CONF="/etc/neo4j/neo4j.conf"
if grep -q "#server.default_listen_address=0.0.0.0" "$NEO4J_CONF"; then
    box log_info "Updating Neo4j network settings..."
    sudo sed -i 's|#server.default_listen_address=0.0.0.0|server.default_listen_address=0.0.0.0|' "$NEO4J_CONF"
fi

if [[ "$VIRT" != "wsl" ]]; then
    box log_info "Starting Neo4j manually..."
    nohup neo4j console > neo4j.log 2>&1 &
else
    box log_info "Enabling and starting Neo4j via systemd..."
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
box print_header "4. Install llama.cpp and AI Models"
box install_package git cmake ninja-build python3-venv python3-pip

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
  -DBUILD_SHARED_LIBS=OFF \
  -DLLAMA_CURL=OFF

cmake --build build --config Release -j "$(nproc)"
sudo cmake --install build --config Release

cd $HOME
mkdir -p "$MODEL_DIR"
# 4.1 Download Gemma3-1b Quantized Model
box log_info "Downloading Gemma3-1b Quantized Model..."
box download_file "https://huggingface.co/unsloth/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q2_K_L.gguf" "$HOME/$MODEL_DIR/Gemma3-1b.gguf"
# 4.2 Download nomic-embed-text-v1.5 Model
box log_info "Downloading nomic-embed-text-v1.5 Model..."
box download_file "https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF/resolve/main/nomic-embed-text-v1.5.Q4_K_S.gguf" "$HOME/$MODEL_DIR/nomic-embed-text-v1.5.gguf"
# 4.3 Download nomic-embed-text-v1.5 Model
box log_info "Downloading bge-reranker-v2-m3 Model..."
box download_file "https://huggingface.co/gpustack/bge-reranker-v2-m3-GGUF/resolve/main/bge-reranker-v2-m3-Q2_K.gguf" "$HOME/$MODEL_DIR/bge-reranker-v2-m3-Q2_K.gguf"

# 5. Create and start llama-server service
box print_header "5. Setup llama-server"
LLAMA_CMD="/usr/local/bin/llama-server -m $HOME/$MODEL_DIR/Gemma3-1b.gguf --cpu-strict 1 --host 0.0.0.0 -t 2 --no-webui --top-k 2 --n_predict 256"
box start_service "llama-server" "$LLAMA_CMD" "$MODEL_DIR"
box check_health "http://localhost:8080/health" '"status":"ok"'

# 5.2 Create and start embed-server service
box print_header "5.2 Setup embed-server"
EMBED_CMD="/usr/local/bin/llama-server --embedding --port 8000 -ngl 99 -m $HOME/$MODEL_DIR/nomic-embed-text-v1.5.gguf -c 8192 -b 8192 --rope-scaling yarn --rope-freq-scale .75 --host 0.0.0.0"
box start_service "embed-server" "$EMBED_CMD" "$MODEL_DIR"
box check_health "http://localhost:8000/health" '"status":"ok"'

# 5.3 Create and start rerank-server service
box print_header "5.3 Setup rerank-server"
EMBED_CMD="/usr/local/bin/llama-server -m models/bge-reranker-v2-m3-Q2_K.gguf --port 8008 --host 0.0.0.0 --reranking"
box start_service "rerank-server" "$EMBED_CMD" "$MODEL_DIR"
box check_health "http://localhost:8008/health" '"status":"ok"'

# 6. Download and Configure Redis Worker
box print_header "6. Setup Redis Worker"
mkdir -p "$HTTP_DIR"
cd "$HTTP_DIR"
box download_file "https://raw.githubusercontent.com/rajatasusual/llamabox/refs/heads/master/scripts/worker.py" "worker.py"
box download_file "https://raw.githubusercontent.com/rajatasusual/llamabox/refs/heads/master/scripts/helper.py" "helper.py"

chmod +x worker.py
chmod +x helper.py
cd $HOME

box setup_venv

WORKER_CMD="$HOME/$VENV_DIR/bin/rq worker -u redis://localhost:6379 snippet_queue"
if [[ "$VIRT" != "wsl" ]]; then
    nohup $WORKER_CMD > worker.log 2>&1 &
else
    box log_info "Creating systemd service for Redis worker..."
    box start_service "redis-worker" "$WORKER_CMD" "$HTTP_DIR"
fi

sleep 5
if "$HOME/$VENV_DIR/bin/rq" info --url redis://localhost:6379 | grep -q "snippet_queue"; then
    echo "✅ Redis worker is healthy."
else
    echo "❌ Error: Redis worker health check failed."
    exit 1
fi

# 7. Download and Configure http-server
box print_header "7. Setup http-server"
cd "$HTTP_DIR"
box download_file "https://raw.githubusercontent.com/rajatasusual/llamabox/refs/heads/master/scripts/http-server.py" "http-server.py"
chmod +x http-server.py
cd $HOME

HTTP_CMD="$HOME/$VENV_DIR/bin/python $HOME/$HTTP_DIR/http-server.py"
if [[ "$VIRT" != "wsl" ]]; then
    nohup $HTTP_CMD > http-server.log 2>&1 &
else
    box log_info "Creating systemd service for HTTP server..."
    box start_service "http-server" "$HTTP_CMD" "$HTTP_DIR"
fi
box check_health "http://localhost:5000/health" '"status":"ok"'

# 8. (WSL Only) Configure auto-restart, security, and additional settings
if [[ "$VIRT" == "wsl" ]]; then
    box print_header "8. WSL-specific Configuration"
    
    # Copy neo4j.service if needed (clarify the purpose via comments)
    box log_info "Copying neo4j.service for multi-user.target compatibility..."
    sudo cp /etc/systemd/system/multi-user.target.wants/neo4j.service /etc/systemd/system/
    
    box log_info "Configuring auto-restart for Redis via systemd..."
    sudo sed -i '/^\[Service\]/a Restart=on-abnormal\nRestartSec=5' /etc/systemd/system/redis-stack-server.service
    sudo systemctl daemon-reload

    box log_info "Securing the server..."
    sudo apt purge -y unattended-upgrades
    box install_package ufw fail2ban unattended-upgrades
    
    box log_info "Configuring UFW..."
    sudo ufw allow ssh
    sudo ufw allow 6379/tcp    # Redis
    sudo ufw allow 7474/tcp    # Neo4j
    sudo ufw allow 7687/tcp    # Neo4j
    sudo ufw allow 8080/tcp    # llama.cpp
    sudo ufw allow 8000/tcp    # embed-server
    sudo ufw allow 5000/tcp    # http-server
    sudo ufw allow 8008/tcp    # rerank-server
    sudo ufw --force enable

    box log_info "Enabling unattended-upgrades..."
    sudo tee /etc/apt/apt.conf.d/50unattended-upgrades > /dev/null <<EOF
Unattended-Upgrade::Origins-Pattern {
    "origin=Debian,codename=\${distro_codename},label=Debian";
    "origin=Debian,codename=\${distro_codename},label=Debian-Security";
    "origin=Debian,codename=\${distro_codename}-security,label=Debian-Security";
};
EOF
    sudo systemctl enable unattended-upgrades

    box log_info "Configuring Fail2Ban..."
    sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
    sudo sed -i '/^\[sshd\]/,/^$/c\[sshd]\nenabled = true\nbackend = systemd\n' /etc/fail2ban/jail.local
    sudo sed -i '/^backend = %(sshd_backend)s/d' /etc/fail2ban/jail.local
    sudo systemctl restart fail2ban
fi

box print_header "Setup Complete"
box log_info "Setup complete. Please verify all services are running."
box log_info "You may wish to reboot your WSL2 instance for all changes to take full effect."
