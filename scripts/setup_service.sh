#!/bin/bash

# setup_service.sh - Set up systemd services for the backend and kiosk
# This script creates and enables systemd services for Fridge Kiosk

set -e  # Exit on error

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Function to print status messages
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to print section headers
print_header() {
    echo
    echo -e "${BOLD}${GREEN}==== $1 ====${NC}"
    echo
}

# Function to print step information
print_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Function to print warning messages
print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to print error messages
print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get the current directory and the install directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"

print_header "SETTING UP SYSTEM SERVICES"
print_status "Installation directory: $INSTALL_DIR"

# Create the backend service file
print_step "Creating backend service..."
cat > /etc/systemd/system/fridge-kiosk-backend.service << EOF
[Unit]
Description=Fridge Kiosk Backend Service
After=network.target

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/backend/app.py
Restart=always
RestartSec=5
StandardOutput=append:$INSTALL_DIR/logs/backend.log
StandardError=append:$INSTALL_DIR/logs/backend-error.log
Environment="PYTHONUNBUFFERED=1"
# Permissions to read temperature data
ReadWritePaths=/sys/class/thermal/thermal_zone0
ProtectSystem=true

[Install]
WantedBy=multi-user.target
EOF
print_status "Backend service file created"

# Create the kiosk service file
print_step "Creating kiosk display service..."
cat > /etc/systemd/system/fridge-kiosk-display.service << EOF
[Unit]
Description=Fridge Kiosk Display Service
After=network.target fridge-kiosk-backend.service
Requires=fridge-kiosk-backend.service
BindsTo=fridge-kiosk-backend.service

[Service]
User=$SUDO_USER
SupplementaryGroups=video render input seat tty
RuntimeDirectory=user/%U
RuntimeDirectoryMode=0700
Environment="XDG_RUNTIME_DIR=/tmp/xdg-runtime-dir"
Environment="WAYLAND_DISPLAY=wayland-0"
Environment="QT_QPA_PLATFORM=wayland"
Environment="GDK_BACKEND=wayland"
Environment="WLR_DRM_NO_ATOMIC=1"
Environment="WLR_RENDERER=pixman"
Environment="WLR_BACKENDS=drm"
Environment="DISPLAY=:0"
Environment="DBUS_SESSION_BUS_ADDRESS=unix:path=%t/user/%U/bus"
ExecStartPre=/bin/mkdir -p /tmp/xdg-runtime-dir
ExecStartPre=/bin/chmod 700 /tmp/xdg-runtime-dir
ExecStartPre=/bin/chown $SUDO_USER:$SUDO_USER /tmp/xdg-runtime-dir
ExecStartPre=/bin/bash -c "until curl -s http://localhost:8080 > /dev/null 2>&1; do sleep 2; done"
ExecStart=/home/$SUDO_USER/start-kiosk.sh
Restart=always

[Install]
WantedBy=multi-user.target
EOF
print_status "Display service file created"

# Create a startup service to tie everything together
print_step "Creating main kiosk service..."
cat > /etc/systemd/system/fridge-kiosk.service << EOF
[Unit]
Description=Fridge Kiosk System
Requires=fridge-kiosk-backend.service fridge-kiosk-display.service
After=fridge-kiosk-backend.service fridge-kiosk-display.service
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/true
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
print_status "Main service file created"

# Reload systemd daemon
print_step "Reloading systemd daemon..."
systemctl daemon-reload
print_status "Systemd daemon reloaded"

# Enable the services to start at boot
print_step "Enabling services to start at boot..."
systemctl enable fridge-kiosk-backend.service
systemctl enable fridge-kiosk-display.service
systemctl enable fridge-kiosk.service
print_success "Services enabled to start at boot"

# Start the backend service
print_step "Starting backend service..."
systemctl start fridge-kiosk-backend.service

# Check service status
print_status "Backend service status:"
systemctl status fridge-kiosk-backend.service --no-pager

print_header "SERVICE SETUP COMPLETE"
print_success "Services set up successfully!"
echo
print_status "The Fridge Kiosk backend service will start automatically on boot."
print_status "The display service will start after the backend is ready."
echo
print_status "You can control the services with these commands:"
echo -e "  ${CYAN}•${NC} sudo systemctl start/stop/restart fridge-kiosk"
echo -e "  ${CYAN}•${NC} sudo systemctl status fridge-kiosk"
echo -e "  ${CYAN}•${NC} sudo journalctl -fu fridge-kiosk-backend.service"
echo

exit 0 