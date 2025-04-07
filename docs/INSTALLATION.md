# **Setting Up Llamabox in WSL2 with Debian**

This guide walks you through installing a full **Retrieval-Augmented Generation (RAG)** assistant locally using **WSL2 with Debian**, **Redis Stack**, **Neo4j**, **llama.cpp**, and **embedding models** — complete with systemd-managed services and security best practices.

---

## 🔧 Prerequisites

- Windows 10/11 with **WSL2 support**
- At least **4GB RAM (8GB recommended)** and **20GB free disk space**
- **Admin privileges**
- [Install Windows Terminal](https://aka.ms/terminal) for a better experience

---

## What You'll Set Up

To create a functional, resilient, and secure AI assistant, you'll install the following stack:

- WSL2 with Debian for a Linux-based environment on Windows
- Redis Stack for high-speed data retrieval and caching
- Neo4j for graph-based knowledge storage
- `llama.cpp` for efficient local LLM inference
- Model servers for embeddings and reranking
- Python-based APIs and background workers
- Linux security and system service management tools

---

## 📖 Table of Contents

1. [Configure WSL](#1-configure-wsl)  
2. [Install Debian](#2-install-debian-on-wsl2)  
3. [Install Essentials](#3-install-essential-packages)  
4. [Install Redis Stack](#4-install-redis-stack-server)  
5. [Install Neo4j](#5-install-neo4j)  
6. [Install llama.cpp and Download AI Models](#6-install-llamacpp-and-ai-models)  
7. [Serve Models](#7-Serve-Models)  
8. [Configure Redis Queue Worker](#8-configure-redis-queue-worker)  
9. [Create HTTP Server Service](#9-create-http-server-service)  
10. [Auto-Restart Services](#10-auto-restart-services-on-crash)  
11. [Secure Your Setup](#11-secure-the-server)  
12. [Make Redis Persistent](#12-make-redis-persistent)  
13. [Verify Setup](#13-verify-setup)  
14. [Manage and Maintain](#14-manage-your-setup)

---

## 1. Configure WSL

WSL2 provides a Linux environment inside Windows using virtualization. You need to enable and tune it properly to support long-running AI services and Docker-like capabilities.

### Enable WSL2
```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

### Set WSL2 as Default
```powershell
wsl --set-default-version 2
```

### Optional: Configure `.wslconfig` (in `%UserProfile%`)
```ini
[wsl2]
processors=4
memory=4GB
nestedVirtualization=false
guiApplications=false
firewall=true
networkingMode=mirrored
defaultVhdSize=20GB

[experimental]
hostAddressLoopback=true
bestEffortDnsParsing=true
```

---

## 2. Install Debian on WSL2

Debian is the base OS where all your tools and services will run. It’s lightweight, stable, and widely supported — ideal for local development.

```powershell
wsl --install -d Debian
```

On first login:
```bash
# Set username and password when prompted
# Update package list
sudo apt update && sudo apt upgrade -y
```

---

## 3. Install Essential Packages

You need system tools, Python dependencies, and security basics to support upcoming services like Redis, Neo4j, and your AI servers.

```bash
sudo apt install -y curl wget ufw fail2ban openssh-server \
  git lsb-release gpg python3-venv python3-pip cmake ninja-build \
  unattended-upgrades
```

### Setup Git LFS and Models
We will need Git LFS to download information extraction pipeline models.
```bash
cd $HOME
# Setup Git LFS
curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
sudo apt-get install git-lfs
```

### Install python dependencies
```bash
python3 -m venv venv
source ~/venv/bin/activate
pip install rq redis flask requests neo4j numpy psutil retry
deactivate
```

---

## 4. Install Redis Stack Server

Redis Stack is a high-performance database ideal for managing queues, caching LLM results, and storing vector data. It’s lightweight and integrates well with Python.

```bash
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
sudo chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb jammy main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt update
sudo apt install -y redis-stack-server
sudo systemctl enable --now redis-stack-server
```

### Verify Redis Stack Server
```bash
redis-cli ping
# The outpout of the last command should be `PONG`.
```

---

## 5. Install Neo4j

Neo4j enables knowledge graphs — a powerful way to store, query, and relate data entities. This is crucial for contextual memory in RAG applications.

### Java 21
```bash
wget https://download.oracle.com/java/21/latest/jdk-21_linux-x64_bin.deb
sudo dpkg -i jdk-21_linux-x64_bin.deb
```
Test Java is installed
```bash
java --version
# The output of the last command should be `openjdk version "xxx"`
```
Remove the downloaded file
```bash
sudo rm jdk-21_linux-x64_bin.deb
```

### Neo4j
```bash
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/neotechnology.gpg
echo 'deb [signed-by=/etc/apt/keyrings/neotechnology.gpg] https://debian.neo4j.com stable latest' | sudo tee -a /etc/apt/sources.list.d/neo4j.list
sudo apt update
sudo apt install -y neo4j=1:2025.02.0
```

### Initial Config
```bash
sudo neo4j-admin dbms set-initial-password password
sudo sed -i 's|# server.default_listen_address=0.0.0.0|server.default_listen_address=0.0.0.0|' /etc/neo4j/neo4j.conf
sudo systemctl enable --now neo4j
```
Verify Neo4j is running
```bash
neo4j status  # Check status
```

---

## 6. Install llama.cpp and AI Models

`llama.cpp` is a performant LLM runtime for running local models with low resource overhead. You’ll also download embedding and reranking models to enrich query responses.

### Build llama.cpp
```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
git submodule update --init --recursive

cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_EXAMPLES=ON \
  -DLLAMA_BUILD_SERVER=ON \
  -DBUILD_SHARED_LIBS=OFF \
  -DLLAMA_CURL=OFF

cmake --build build --config Release -j $(nproc)
sudo cmake --install build --config Release
```

### Download Models

```bash
mkdir -p $HOME/$MODEL_DIR
cd $HOME/$MODEL_DIR
```

Gemma3-1b model - Our primary inference model
```bash
wget "$HOME/$MODEL_DIR/Gemma3-1b.gguf" "https://huggingface.co/unsloth/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q2_K_L.gguf" 
```
Nomic-embed-text-v1.5 model - Our embedding model
```bash
wget "$HOME/$MODEL_DIR/Nomic-embed-text-v1.5.gguf" "https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF/resolve/main/nomic-embed-text-v1.5.Q4_K_S.gguf"
```
BGE-reranker-v3-m3 model - Our reranker model
```bash
wget "$HOME/$MODEL_DIR/bge-reranker-v2-m3-Q2_K.gguf" "https://huggingface.co/gpustack/bge-reranker-v2-m3-GGUF/resolve/main/bge-reranker-v2-m3-Q2_K.gguf"
```

## **7. Serve Models**

We have three services to create, llama-server.service, embed-server.service and rerank-server.service.

Here is the reference table:

| Service Name | Working Directory | Exec Command |
|--------------|-------------------|-------------|
| llama-server | $HOME | /usr/local/bin/llama-server -m $HOME/$MODEL_DIR/Gemma3-1b.gguf --cpu-strict 1 --host 0.0.0.0 -c 2048 -t 2 --no-webui  |
| embed-server | $HOME | /usr/local/bin/llama-server --embedding --port 8000 -ngl 99 $HOME/$MODEL_DIR/Nomic-embed-text-v1.5.gguf -c 8192 -b 8192 --rope-scaling yarn --rope-freq-scale .75 --host 0.0.0.0 |
| rerank-server | $HOME | /usr/local/bin/llama-server --port 8008 -m $HOME/$MODEL_DIR/bge-reranker-v2-m3-Q2_K.gguf --host 0.0.0.0 |

To create the services we need to add the following content to the `/etc/systemd/system/{Service Name}.service` file.

```ini
[Unit]
Description=${service_name} Service
After=network.target

[Service]
Type=simple
ExecStart=${exec_cmd}
Restart=on-abnormal
RestartSec=3
User=${USER}
WorkingDirectory=${HOME}/${working_dir}
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=${service_name}

[Install]
WantedBy=multi-user.target
```

### Instructions to Enable the Service

1. **Create the Service File:**  
   Save the above content as `/etc/systemd/system/{Service Name}.service`.  
   ```bash
   sudo touch /etc/systemd/system/{Service Name}.service 
   sudo nano /etc/systemd/system/{Service Name}.service
   ```

2. **Reload Systemd:**  
   After saving the file, reload systemd to pick up the new service.
   ```bash
   sudo systemctl daemon-reload
   ```

3. **Enable the Service at Boot:**  
   ```bash
   sudo systemctl enable {Service Name}
   ```

4. **Start the Service:**  
   ```bash
   sudo systemctl start {Service Name}
   ```

5. **Check Service Status:**  
   ```bash
   curl -X GET http://localhost:8080/health
   ```
---

## **8. Configure Redis Queue Worker**

The worker handles async jobs — offloading heavy computation from the HTTP server to a background process, which increases responsiveness and system efficiency.

### **Download and Setup Worker**
```bash
# Set up worker script
mkdir http-server
cd $HOME/http-server
curl -o worker.py https://raw.githubusercontent.com/rajatasusual/llamabox/refs/heads/master/scripts/worker.py
chmod +x worker.py
cd $HOME
```

### **Create Worker Service**
Create file at `/etc/systemd/system/worker.service`:
```ini
[Unit]
Description=RQ Worker Service
After=network.target redis.service

[Service]
Type=simple
ExecStart=$HOME/venv/bin/rq worker -u redis://localhost:6379 snippet_queue
Restart=on-abnormal
RestartSec=3
User=$USER
WorkingDirectory=$HOME/http-server
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=redis-worker

[Install]
WantedBy=multi-user.target
```

### **Enable and Test Service**
```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable worker
sudo systemctl start worker

# Test worker health
$HOME/venv/bin/rq info --url redis://localhost:6379
```
## **9. Create HTTP Server Service**

The HTTP server acts as the API layer for external tools (like a UI or chatbot) to interact with your RAG system. Running it as a service keeps it always-on and auto-recovering.

```bash
# Set up HTTP server by copying the flask server script from the repository
mkdir http-server
cd http-server
curl -o http-server.py https://raw.githubusercontent.com/rajatasusual/llamabox/refs/heads/master/http-server.py
chmod +x http-server.py
cd $HOME
```

### **Create Service File**
Create file at `/etc/systemd/system/http-server.service`:

```ini
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
```

### **Instructions to Enable the Service**

1. **Reload Systemd:**
   ```bash
   sudo systemctl daemon-reload
   ```

2. **Enable and Start Service:**
   ```bash
   sudo systemctl enable http-server
   sudo systemctl start http-server
   ```

3. **Check Service Status:**
   ```bash
   curl -X GET http://localhost:5000/health
   ```

## **10. Auto-Restart Services on Crash**

Services may crash occasionally. Configuring systemd to auto-restart ensures high availability without manual intervention.

```bash
cd /etc/systemd/system/
sudo cp /lib/systemd/system/neo4j.service .
sudo nano redis-stack-server.service
sudo nano neo4j.service
```
Ensure these lines exist:
```ini
[Service]
Restart=on-abnormal
RestartSec=5
```
Reload systemd:
```bash
sudo systemctl daemon-reload
```
Check if services run after reboot:
```bash
neo4j status
redis-cli ping
curl -X GET http://localhost:8080/health
```

## **11. Secure the Server**
### **Step 1: Disable Root SSH Login**
```bash
sudo nano /etc/ssh/sshd_config
# Change this line:
PermitRootLogin no
sudo systemctl restart ssh
```

### **Step 2: Configure Firewall**
```bash
sudo ufw allow ssh
sudo ufw allow 6379/tcp    # Redis
sudo ufw allow 7474/tcp    # Neo4j
sudo ufw allow 7687/tcp    # Neo4j
sudo ufw allow 8080/tcp    # llama.cpp
sudo ufw allow 8000/tcp    # embed-server
sudo ufw allow 5000/tcp    # http-server
sudo ufw allow 8008/tcp    # rerank-server
    
sudo ufw enable
```

### **Step 3: Enable Automatic Security Updates**
```bash
sudo apt purge unattended-upgrades
sudo apt install unattended-upgrades
sudo nano /etc/apt/apt.conf.d/50unattended-upgrades
```
Ensure these lines exist:
```ini
Unattended-Upgrade::Origins-Pattern {
  "origin=Debian,codename=${distro_codename},label=Debian";
  "origin=Debian,codename=${distro_codename},label=Debian-Security";
  "origin=Debian,codename=${distro_codename}-security,label=Debian-Security";
};
```
Enable it:
```bash
sudo systemctl enable unattended-upgrades
```

### **Step 4: Install & Configure Fail2Ban**
```bash
sudo apt install fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local
```

Ensure ssh is configured with systemd backend
```bash
[sshd]
enabled = true
backend = systemd
```

Check allowed IPs and restart:
```bash
sudo systemctl restart fail2ban
sudo iptables -L  # Verify rules
```

---

## **12. Make Redis Persistent**
```bash
echo "save 900 1" | sudo tee -a /etc/redis-stack.conf
sudo systemctl restart redis-stack-server
```

---

## **13. Verify Setup**
- **Check Running Processes**
  ```bash
  top
  ```
- **Confirm Services Restart on Reboot**
  ```bash
  sudo reboot
  ```

---

## **14. Manage your Setup**

For detailed commands and instructions on managing your services—including handling processes on both Debian and Windows—please refer to [MANAGE.md](/docs/MANAGE.md). This document covers system-specific commands, troubleshooting tips, and best practices for maintaining your RAG AI Assistant setup.