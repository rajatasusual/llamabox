# Setting Up a Local RAG AI Assistant in WSL2 with Debian

This guide provides step-by-step instructions for setting up a local Retrieval-Augmented Generation (RAG) AI assistant using WSL2 with Debian. The setup includes Redis for vector storage, Neo4j for knowledge graphs, and llama.cpp for AI inference capabilities.

Prerequisites:
- Windows 10/11 with WSL2 support
- At least 8GB RAM and 20GB free disk space
- Administrative access to install packages

## What We'll Set Up
- [x] WSL2 with Debian
- [x] Essential system tools
- [x] Database systems (Redis, Neo4j)
- [x] AI capabilities with llama.cpp
- [x] Security configurations
- [x] Service auto-restart settings

## Table of Contents
1. [Configure WSL](#1-configure-wsl)
2. [Install Debian on WSL2](#2-install-debian-on-wsl2)
3. [Install Essential Packages](#3-install-essential-packages)
4. [Install Redis Stack Server](#4-install-redis-stack-server)
5. [Install Neo4j](#5-install-neo4j)
6. [Install llama.cpp and AI Models](#6-install-llamacpp-and-ai-models)
7. [Auto-Restart Services on Crash](#7-auto-restart-services-on-crash)
8. [Secure the Server](#8-secure-the-server)
9. [Make Redis Persistent](#9-make-redis-persistent)
10. [Verify Setup](#10-verify-setup)
11. [Manage your setup](#11-manage-your-setup)


## **1. Configure WSL**

### **Enable WSL2**
```powershell
# Enable required Windows features
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

### **Set WSL2 as Default**
```powershell
wsl --set-default-version 2
```

Create file at `%UserProfile%\.wslconfig`:
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

## **2. Install Debian on WSL2**

### **Install Debian**
```powershell
# Install from Microsoft Store or use:
wsl --install -d Debian
```
### **First Login**
When Debian starts:
```bash
# Set username and password when prompted
# Update package list
sudo apt update && sudo apt upgrade -y
```
---

## **3. Install Essential Packages**
```bash
sudo apt install -y curl wget ufw fail2ban unattended-upgrades openssh-server
```

---

## **4. Install Redis Stack Server**
```bash
sudo apt-get install -y lsb-release curl gpg
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
sudo chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb jammy main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt update
sudo apt install -y redis-stack-server
sudo systemctl enable redis-stack-server
sudo systemctl start redis-stack-server
redis-cli ping  # Test Redis
```

---

## **5. Install Neo4j**
### **Install Java**
```bash
wget https://download.oracle.com/java/21/latest/jdk-21_linux-x64_bin.deb
sudo dpkg -i jdk-21_linux-x64_bin.deb
java --version
sudo rm jdk-21_linux-x64_bin.deb
```
### **Install Neo4j**
```bash
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/neotechnology.gpg
echo 'deb [signed-by=/etc/apt/keyrings/neotechnology.gpg] https://debian.neo4j.com stable latest' | sudo tee -a /etc/apt/sources.list.d/neo4j.list
sudo apt-get update
sudo apt-get install -y neo4j=1:2025.02.0
```
### **Set Initial Password & Enable Outside connections**
```bash
sudo neo4j-admin dbms set-initial-password password
NEO4J_CONF="/etc/neo4j/neo4j.conf"
sudo sed -i 's|# server.default_listen_address=0.0.0.0|server.default_listen_address=0.0.0.0|' "$NEO4J_CONF"    
```
### **ENable service & check status**
```bash
sudo systemctl enable neo4j
sudo systemctl start neo4j
neo4j status  # Check status
```

---

## **6. Install llama.cpp and AI Models**

### **Install Prerequisites**
```bash
sudo apt-get install -y git cmake ninja-build python3-venv python3-pip
```

### **Build llama.cpp**
```bash
git clone https://github.com/ggml-org/llama.cpp.git
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
```

### **Setup Python Environment and Download Model**
```bash
# Clone model repository
GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct
mkdir models

# Setup Python environment
python3 -m venv llama-cpp-venv
source ./llama-cpp-venv/bin/activate
python -m pip install --upgrade pip wheel setuptools

# Install conversion requirements
python -m pip install --upgrade -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt

# Convert and quantize model
python llama.cpp/convert_hf_to_gguf.py SmolLM2-360M-Instruct --outfile ./models/SmolLM2.gguf
llama-quantize ./models/SmolLM2.gguf ./models/SmolLM2.q8.gguf Q8_0 N
sudo rm ./models/SmolLM2.gguf
deactivate
```
>Note: You need to manually download the `model.safetensors` file from HuggingFace and place it in the `SmolLM2-360M-Instruct` directory.

>Important: you would need to replace "N" with the number of cores you want to setup for inference.  

### **Create Llama service**

```ini
[Unit]
Description=llama-server Service
After=network.target

[Service]
Type=simple
# Update the ExecStart path and model path as necessary
ExecStart=/usr/local/bin/llama-server -m $HOME/models/SmolLM2.q8.gguf --host 0.0.0.0
Restart=on-abnormal
RestartSec=5
User=$USER
WorkingDirectory=$HOME
# Optionally, log output to syslog
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=llama-server

[Install]
WantedBy=multi-user.target
```

---

### Instructions to Enable the Service

1. **Create the Service File:**  
   Save the above content as `/etc/systemd/system/llama-server.service`.  
   ```bash
   sudo touch /etc/systemd/system/llama-server.service 
   sudo nano /etc/systemd/system/llama-server.service
   ```

2. **Reload Systemd:**  
   After saving the file, reload systemd to pick up the new service.
   ```bash
   sudo systemctl daemon-reload
   ```

3. **Enable the Service at Boot:**  
   ```bash
   sudo systemctl enable llama-server
   ```

4. **Start the Service:**  
   ```bash
   sudo systemctl start llama-server
   ```

5. **Check Service Status:**  
   ```bash
   curl -X GET http://localhost:8080/health
   ```
---

## **7. Auto-Restart Services on Crash**
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

## **8. Secure the Server**
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
sudo ufw allow 6379/tcp  # Redis
sudo ufw allow 7474/tcp  # Neo4j
sudo ufw allow 8080/tcp  # llama.cpp
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
Check allowed IPs and restart:
```bash
sudo systemctl restart fail2ban
sudo iptables -L  # Verify rules
```

---

## **9. Make Redis Persistent**
```bash
echo "save 900 1" | sudo tee -a /etc/redis-stack.conf
sudo systemctl restart redis-stack-server
```

---

## **10. Verify Setup**
- **Check Running Processes**
  ```bash
  top
  ```
- **Confirm Services Restart on Reboot**
  ```bash
  sudo reboot
  ```

---

## **11. Manage your Setup**

For detailed commands and instructions on managing your services—including handling processes on both Debian and Windows—please refer to [MANAGE.md](MANAGE.md). This document covers system-specific commands, troubleshooting tips, and best practices for maintaining your RAG AI Assistant setup.