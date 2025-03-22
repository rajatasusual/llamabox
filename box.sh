#!/usr/bin/env bash

# ---------------------------
# Global Directory Variables
# ---------------------------
MODEL_DIR="models"
HTTP_DIR="http-server"
VENV_DIR="venv"

# ---------------------------
# Environment Detection
# ---------------------------
VIRT=$(systemd-detect-virt 2>/dev/null || echo "none")
if [[ "$VIRT" == "wsl" ]]; then
    echo "[INFO] Running in WSL environment (systemd mode)."
    # ---------------------------
    # Sudo/Root Check
    # ---------------------------
    if [[ "$EUID" -eq 0 ]]; then
        echo -e "\e[31m[WARNING] Running as root or using sudo!\e[0m"
        echo "[INFO] It's recommended to run this script as a regular user unless explicitly needed."
        read -p "Do you want to continue as root? (y/N): " consent
        if [[ ! "$consent" =~ ^[Yy]$ ]]; then
            echo "Exiting..."
            exit 1
        fi
    fi

else
    echo "[INFO] Running in non-WSL environment (non-systemd mode)."
fi

# ---------------------------
# Logging Functions
# ---------------------------
log_info() {
    echo "[INFO] $1"
}

# ---------------------------
# Utility Functions
# ---------------------------
print_header() {
    echo "===================================="
    echo "$1"
    echo "===================================="
}

run_update() {
    log_info "Updating and upgrading system packages..."
    sudo apt update && sudo apt upgrade -y
}

install_package() {
    log_info "Installing package(s): $*"
    sudo apt install -y "$@"
}

download_file() {
    local url="$1"
    local dest="$2"
    log_info "Downloading from $url to $dest"
    # Use wget and fail if download fails
    wget -O "$dest" "$url"
}

start_service() {
    local service_name="$1"
    local exec_cmd="$2"
    local working_dir="$3"
    local service_file="/etc/systemd/system/${service_name}.service"

    if [[ "$VIRT" != "wsl" ]]; then
        log_info "Starting $service_name manually..."
        nohup $exec_cmd > "${service_name}.log" 2>&1 &
    else
        log_info "Creating systemd service for $service_name..."
        if [[ -f "$service_file" ]]; then
            log_info "Service $service_name already exists. Restarting it..."
            sudo systemctl restart "$service_name"
            return 0
        fi

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
WorkingDirectory=${HOME}/${working_dir}
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
    sleep 1
    if curl -s -X GET "$url" | grep -q "$expected"; then
        echo "✅ Health check passed for $url"
    else
        echo "❌ Error: Health check failed for $url"
        exit 1
    fi
}

setup_venv() {
    if [[ "$VIRT" == "wsl" ]]; then
        if [[ "$EUID" -eq 0 ]]; then
            echo -e "\e[31m[ERROR] Do not run this command as root!\e[0m"
            return 1  # Exit function with an error
        fi
    fi
    if [ ! -d "$VENV_DIR" ]; then
        log_info "Creating Python virtual environment in $VENV_DIR"
        python3 -m venv "$VENV_DIR"
    fi
    # Activate and install common packages
    log_info "Setting up Python virtual environment..."
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install rq redis flask requests
    deactivate
}

if [[ $# -lt 1 ]]; then
    echo "Usage: box <command> [arguments]"
    echo "Available commands:"
    declare -F | awk '{print " - " $3}' | grep -v "^_"  # List all functions
    exit 1
fi


COMMAND=$1
shift

if declare -f "$COMMAND" > /dev/null; then
    "$COMMAND" "$@"
else
    echo "Error: Unknown command '$COMMAND'"
    exit 1
fi
