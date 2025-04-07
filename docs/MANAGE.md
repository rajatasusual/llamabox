# 🔧 Managing Your Llamabox

This document provides a structured, easy-to-follow reference of helpful **Debian** and **Windows PowerShell** commands, especially useful when managing your **Llamabox** installed via [SETUP.md](./SETUP.md). Whether you're monitoring system resources, debugging services, or tweaking performance, this guide has you covered.

---

## 🖥️ 1. Debian System Management

These commands are run inside your **Debian WSL2 environment**, and help you monitor, debug, and optimize your system.

### 📊 System Monitoring & Diagnostics

Use these commands to keep an eye on system health and performance.

```bash
df -h /                       # View disk usage on root
du -sh /path/to/dir           # Check size of specific directory

free -h                       # Show memory usage
top                           # Real-time process monitor
vmstat                        # Virtual memory stats

uptime                        # Show how long the system has been running
uname -a                      # Kernel info and system architecture
lscpu                         # Detailed CPU information

ss -l                         # List all listening ports
ps xw                         # View all active processes with details
```

> 🔍 **Tip:** Use these regularly after setting up services like `llama.cpp`, `Redis`, and `Neo4j` to spot any performance bottlenecks.

---

### 📦 Package Management (APT)

Essential for installing, upgrading, and cleaning packages in your Debian system.

```bash
apt update                    # Refresh package index
apt upgrade                   # Upgrade installed packages
apt search <package>          # Search for a package
apt show <package>            # Display package details

apt autoremove                # Remove unused packages
apt clean                     # Remove downloaded archives
apt autoclean                 # Remove outdated archives

dpkg -l                       # List all installed packages
```

> ✅ **Useful After:** Adding or modifying software during setup (e.g., `git-lfs`, `fail2ban`, `llama.cpp`).

---

### 🔁 Service Control (Systemd)

These are vital when working with services you've configured during setup (e.g., `llama-server`, `redis-stack-server`, `neo4j`, etc.).

```bash
# Check service status
systemctl status <service>

# List all active services
systemctl list-units

# Show any failed services
systemctl --failed

# View real-time system logs
journalctl -xe

# View logs for a specific service (e.g., llama-server)
journalctl --unit=llama-server.service -n 100 --no-pager
```

> 🛠️ **Use When:** Debugging service failures or confirming everything is running post-reboot.

---

## 💻 2. Windows PowerShell for WSL2

These PowerShell commands help you interact with your WSL2 environment *from the Windows side*, especially helpful for networking, VHD management, or troubleshooting.

---

### 🌐 Network & Connectivity

Check if your local services (inside WSL2) are reachable from Windows.

```powershell
Test-NetConnection <WSL_IP> -p 6379    # Test Redis connection
Test-NetConnection <WSL_IP> -p 7474    # Test Neo4j connection
Test-NetConnection <WSL_IP> -p 8080    # Test llama.cpp server
```

> 💡 **Find your WSL IP with:** `wsl hostname -I`

---

### 🗂️ WSL VHD Location (WSL2 Disk)

Want to find where your WSL2 Debian filesystem lives?

```powershell
(Get-ChildItem -Path HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss | 
 Where-Object { $_.GetValue("DistributionName") -eq 'Debian' }).GetValue("BasePath") + "\ext4.vhdx"
```

> 🔒 **Pro Tip:** Back up this `.vhdx` file regularly if your setup is critical.

---

### ⚙️ Manage WSL Itself

General WSL2 control commands.

```powershell
wsl --list --verbose         # List WSL distros and running state
wsl hostname -I              # Get current WSL IP
wsl --shutdown               # Gracefully shut down all running WSL instances
wsl --update                 # Update WSL kernel to latest version
```

> 🚨 **Run After:** Major updates or if networking breaks after reboot.

---

## 📌 Final Notes

- Combine this guide with your [INSTALLATION.md](/docs/INSTALLATION.md) for a full lifecycle view: from installation to long-term operation.
- Always verify services are healthy after a system update or reboot.
- Use logs generously—`journalctl` and `systemctl status` are your best friends when something seems off.