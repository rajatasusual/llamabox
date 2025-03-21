# Introduction

This document provides a structured overview of various command-line tools and commands for system management on Debian and Windows PowerShell for WSL2 environments. It includes sections for obtaining system information, managing packages, handling services, and working with WSL2 on Windows.

## 11. Helpful Debian Commands

### System Information

```bash
# Check disk space
df -h /                    # Show disk usage
du -sh /path/to/dir        # Directory size

# Memory usage
free -h                    # RAM usage
top                        # Process monitor
vmstat                     # Virtual memory stats

# System monitoring
uptime                     # System uptime
uname -a                   # Kernel info
lscpu                      # CPU info
ss -l                      # List all open ports
ps xw                      # List all running jobs
```

### Package Management

```bash
# APT commands
apt update                 # Update package list
apt upgrade                # Upgrade packages
apt search package         # Search for package
apt show package           # Show package details
apt autoremove             # Remove unused packages

# Package maintenance
dpkg -l                    # List installed packages
apt clean                  # Clear package cache
apt autoclean              # Remove old packages
```

### Service Management

```bash
# Systemctl commands
systemctl status name_of_service    # Check service status
systemctl list-units                # List all services
systemctl --failed                  # Show failed services
journalctl -xe                      # View system logs
```

## 12. Windows PowerShell Commands for WSL2

```powershell
# Test network connectivity to WSL services
Test-NetConnection WSL_IP -p 6379   # Redis
Test-NetConnection WSL_IP -p 7474   # Neo4j
Test-NetConnection WSL_IP -p 11434  # Ollama

# Find WSL2 VHD location
(Get-ChildItem -Path HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss | 
 Where-Object { $_.GetValue("DistributionName") -eq 'Debian' }).GetValue("BasePath") + "\ext4.vhdx"

# WSL management
wsl --list --verbose                # List distros with status
wsl hostname -I                     # Get WSL IP address
wsl --shutdown                     # Stop all distros
wsl --update                       # Update WSL core
```