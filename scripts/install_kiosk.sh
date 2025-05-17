#!/bin/bash

# Fridge Kiosk Installation Script
# This script will install and configure the Fridge Kiosk system on a Raspberry Pi.
# It combines the functionality of install.sh, setup_environment.sh and setup_service.sh

set -e  # Exit on error

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_header() { echo -e "\n${BOLD}${GREEN}==== $1 ====${NC}\n"; }
print_step() { echo -e "${CYAN}[STEP]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

print_header "FRIDGE KIOSK INSTALLER"
echo -e "${CYAN}A modular, plugin-based kiosk display system for Raspberry Pi${NC}"
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    print_error "This script must be run as root!"
    echo "Please run: sudo ./install_kiosk.sh"
    exit 1
fi

# Current directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Use parent directory as installation directory
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"
cd "$INSTALL_DIR"

print_status "Installation directory: $INSTALL_DIR"

# Set execute permissions on scripts
print_step "Setting execute permissions on scripts..."
find "$INSTALL_DIR/scripts" -name "*.sh" -exec chmod +x {} \;
print_status "Permissions set"

# Run setup_dependencies script
print_header "SETTING UP DEPENDENCIES"
print_step "Installing required packages..."
bash "$INSTALL_DIR/scripts/setup_dependencies.sh"

# ENVIRONMENT SETUP - from setup_environment.sh
print_header "SETTING UP SYSTEM ENVIRONMENT"

# Create necessary directories and files
print_step "Creating required directories and files..."
mkdir -p "$INSTALL_DIR/logs"
mkdir -p "$INSTALL_DIR/config"
echo -e "  ${CYAN}•${NC} Created directory: $INSTALL_DIR/logs"
echo -e "  ${CYAN}•${NC} Created directory: $INSTALL_DIR/config"

# Create log files
touch "$INSTALL_DIR/logs/kiosk.log"
touch "$INSTALL_DIR/logs/backend.log"
touch "$INSTALL_DIR/logs/backend-error.log"
echo -e "  ${CYAN}•${NC} Created log files in: $INSTALL_DIR/logs"

# Set permissions
print_step "Setting directory and file permissions..."

# Set owner to the user running the script (non-sudo)
if [ -n "$SUDO_USER" ]; then
    chown -R "$SUDO_USER:$SUDO_USER" "$INSTALL_DIR/logs"
    chown -R "$SUDO_USER:$SUDO_USER" "$INSTALL_DIR/config"
    chown -R "$SUDO_USER:$SUDO_USER" "$INSTALL_DIR"
    echo -e "  ${CYAN}•${NC} Set ownership of all files to: $SUDO_USER"
fi

# Ensure logs directory and files are writable
chmod -R 755 "$INSTALL_DIR/logs"
chmod 666 "$INSTALL_DIR/logs/kiosk.log"
chmod 666 "$INSTALL_DIR/logs/backend.log"
chmod 666 "$INSTALL_DIR/logs/backend-error.log"
echo -e "  ${CYAN}•${NC} Set write permissions for log files"

# Set up executable files
print_step "Setting up executable files..."
sed -i "1c #!$INSTALL_DIR/venv/bin/python3" "$INSTALL_DIR/run.py"
echo -e "  ${CYAN}•${NC} Updated run.py shebang to use virtual environment"

# Make sure scripts are executable
chmod +x "$INSTALL_DIR/run.py"
find "$INSTALL_DIR/scripts" -name "*.sh" -exec chmod +x {} \;
echo -e "  ${CYAN}•${NC} Set execute permissions for scripts"

print_header "CONFIGURING KIOSK SERVICES"

# Create groups for the kiosk user if they don't exist
print_step "Setting up necessary groups..."
groupadd -f seat
echo -e "  ${CYAN}•${NC} Created/verified group: seat"
groupadd -f render
echo -e "  ${CYAN}•${NC} Created/verified group: render"

# Add user to required groups
print_step "Adding user $SUDO_USER to required groups..."
usermod -aG video,input,seat,render,tty $SUDO_USER
echo -e "  ${CYAN}•${NC} Added user to groups: video, input, seat, render, tty"

# Set up DRI device permissions
print_step "Setting up DRI device permissions..."
if [ -e "/dev/dri/card0" ]; then
    chmod 666 /dev/dri/card0
    echo -e "  ${CYAN}•${NC} Set permissions for /dev/dri/card0"
    # Add current user to the video group
    if ! groups $SUDO_USER | grep -q "video"; then
        usermod -aG video $SUDO_USER
        echo -e "  ${CYAN}•${NC} Added $SUDO_USER to video group"
    fi
else
    print_warning "DRI device /dev/dri/card0 not found. This will cause graphics issues."
    echo -e "  ${CYAN}•${NC} Make sure the GPU driver is properly installed"
fi

if [ -e "/dev/dri/renderD128" ]; then
    chmod 666 /dev/dri/renderD128
    echo -e "  ${CYAN}•${NC} Set permissions for /dev/dri/renderD128"
    # Add current user to the render group
    if ! groups $SUDO_USER | grep -q "render"; then
        usermod -aG render $SUDO_USER
        echo -e "  ${CYAN}•${NC} Added $SUDO_USER to render group"
    fi
else
    print_warning "DRI device /dev/dri/renderD128 not found. This will cause graphics issues."
    echo -e "  ${CYAN}•${NC} Make sure the GPU driver is properly installed"
fi

# Make sure udev rules are correct for these devices
cat > /etc/udev/rules.d/99-drm-permissions.rules << EOF
SUBSYSTEM=="drm", ACTION=="add", MODE="0666", GROUP="video"
SUBSYSTEM=="graphics", ACTION=="add", MODE="0666", GROUP="video"
KERNEL=="card[0-9]*", SUBSYSTEM=="drm", MODE="0666", GROUP="video"
KERNEL=="renderD[0-9]*", SUBSYSTEM=="drm", MODE="0666", GROUP="video"
EOF
echo -e "  ${CYAN}•${NC} Created udev rules for DRM devices"

# Reload udev rules
udevadm control --reload-rules
udevadm trigger
echo -e "  ${CYAN}•${NC} Reloaded udev rules"

# Create a dummy virtual X frame buffer for systems without a GPU
if [ ! -e "/dev/dri/card0" ]; then
    print_step "Setting up Xvfb as fallback display..."
    apt-get install -y xvfb
    
    # Create a systemd service for Xvfb
    cat > /etc/systemd/system/xvfb.service << EOF
[Unit]
Description=X Virtual Frame Buffer Service
After=network.target

[Service]
ExecStart=/usr/bin/Xvfb :0 -screen 0 1920x1080x24
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable xvfb.service
    systemctl start xvfb.service
    echo -e "  ${CYAN}•${NC} Xvfb virtual display configured as fallback"
fi

# Create the kiosk start script
USER_HOME="/home/$SUDO_USER"
print_step "Creating kiosk startup script..."
cat > "$USER_HOME/start-kiosk.sh" << EOF
#!/bin/bash

# Set environment variables
export XDG_RUNTIME_DIR=/tmp/xdg-runtime-dir
export WLR_BACKENDS=drm
export WLR_DRM_NO_ATOMIC=1
export WLR_DRM_DEVICES=/dev/dri/card0
export QT_QPA_PLATFORM=wayland
export GDK_BACKEND=wayland
export WAYLAND_DISPLAY=wayland-0
export DISPLAY=:0
export DBUS_SESSION_BUS_ADDRESS="unix:path=\$XDG_RUNTIME_DIR/bus"

# Create runtime directory
mkdir -p \$XDG_RUNTIME_DIR
chmod 700 \$XDG_RUNTIME_DIR

# Start dbus session
if [ ! -e "\$XDG_RUNTIME_DIR/bus" ]; then
    dbus-daemon --session --address="\$DBUS_SESSION_BUS_ADDRESS" --nofork --nopidfile --syslog-only &
    sleep 1
fi

# Start cage and chromium
cage -d -- chromium-browser \\
    --kiosk \\
    --disable-gpu \\
    --disable-software-rasterizer \\
    --disable-dev-shm-usage \\
    --no-sandbox \\
    --disable-dbus \\
    --incognito \\
    --disable-extensions \\
    --disable-plugins \\
    --disable-popup-blocking \\
    --disable-notifications \\
    http://localhost:8080 &

# Wait for cage to start
sleep 5

# Check which monitors are connected and rotate the screen if in portrait mode
OUTPUT=\$(wlr-randr | grep -o -m 1 "^HDMI-[A-Za-z0-9\-]*")
if [ -n "\$OUTPUT" ]; then
    echo "Found monitor: \$OUTPUT"
    # Get display orientation from config file
    ORIENTATION=\$(cat "$INSTALL_DIR/config/main.json" | grep -o '"orientation":[^,]*' | cut -d '"' -f 4)
    if [ "\$ORIENTATION" = "portrait" ]; then
        for i in {1..3}; do
            if wlr-randr --output "\$OUTPUT" --transform 270; then
                echo "Screen rotated to portrait mode"
                break
            fi
            sleep 2
        done
    else
        echo "Using landscape orientation"
    fi
else
    echo "Monitor not found"
fi

# Wait for main process
wait
EOF

# Set permissions for the kiosk script
print_step "Setting permissions for startup script..."
chown $SUDO_USER:$SUDO_USER "$USER_HOME/start-kiosk.sh"
chmod +x "$USER_HOME/start-kiosk.sh"

# SERVICE SETUP - from setup_service.sh
print_header "SETTING UP SYSTEM SERVICES"

# Define service names
BACKEND_SERVICE="fridge-kiosk-backend.service"
DISPLAY_SERVICE="fridge-kiosk-display.service"

# Create the backend service file
print_step "Creating backend service ($BACKEND_SERVICE)..."
cat > /etc/systemd/system/$BACKEND_SERVICE << EOF
[Unit]
Description=Fridge Kiosk Backend Service
After=network.target

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/run.py
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
echo -e "  ${CYAN}•${NC} Created service file: /etc/systemd/system/$BACKEND_SERVICE"
print_status "Backend service file created"

# Create the kiosk display service file
print_step "Creating kiosk display service ($DISPLAY_SERVICE)..."
cat > /etc/systemd/system/$DISPLAY_SERVICE << EOF
[Unit]
Description=Fridge Kiosk Display Service
After=network.target $BACKEND_SERVICE
Requires=$BACKEND_SERVICE
BindsTo=$BACKEND_SERVICE

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
echo -e "  ${CYAN}•${NC} Created service file: /etc/systemd/system/$DISPLAY_SERVICE"
print_status "Display service file created"

# Set up log rotation for log files
print_step "Setting up log rotation..."
cat > /etc/logrotate.d/fridge-kiosk << EOF
$INSTALL_DIR/logs/*.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
    create 0644 $SUDO_USER $SUDO_USER
}
EOF

# Reload systemd daemon
print_step "Reloading systemd daemon..."
systemctl daemon-reload
print_status "Systemd daemon reloaded"

# Enable the services to start at boot
print_step "Enabling services to start at boot..."
systemctl enable $BACKEND_SERVICE
echo -e "  ${CYAN}•${NC} Enabled service: $BACKEND_SERVICE"
systemctl enable $DISPLAY_SERVICE
echo -e "  ${CYAN}•${NC} Enabled service: $DISPLAY_SERVICE"

# Start the backend service
print_step "Starting backend service ($BACKEND_SERVICE)..."
systemctl start $BACKEND_SERVICE

# Check service status
print_status "Backend service status:"
systemctl status $BACKEND_SERVICE --no-pager || true

# Create .env file if it doesn't exist
if [ ! -f "$INSTALL_DIR/config/.env" ]; then
    print_step "Creating .env file..."
    cp "$INSTALL_DIR/config/.env.example" "$INSTALL_DIR/config/.env" 2>/dev/null || touch "$INSTALL_DIR/config/.env"
    chown $SUDO_USER:$SUDO_USER "$INSTALL_DIR/config/.env"
    print_warning "Please edit the .env file to add your API keys and credentials:"
    echo -e "${YELLOW}    nano $INSTALL_DIR/config/.env${NC}"
else
    print_status "Using existing .env file"
fi

print_header "INSTALLATION COMPLETED!"
print_status "The Fridge Kiosk has been installed to: $INSTALL_DIR"
echo
print_status "Next steps:"
echo -e "  ${CYAN}1.${NC} Services have been enabled automatically. To manage them:"
echo -e "     ${CYAN}•${NC} sudo systemctl enable/disable fridge-kiosk-backend.service"
echo -e "     ${CYAN}•${NC} sudo systemctl enable/disable fridge-kiosk-display.service"
echo
echo -e "  ${CYAN}2.${NC} Configure the system by editing these files:"
echo -e "     ${CYAN}•${NC} Main configuration: $INSTALL_DIR/config/main.json"
echo -e "     ${CYAN}•${NC} Environment variables: $INSTALL_DIR/config/.env"
echo
echo -e "  ${CYAN}3.${NC} Start the services:"
echo -e "     ${CYAN}•${NC} sudo systemctl start fridge-kiosk-backend.service"
echo -e "     ${CYAN}•${NC} sudo systemctl start fridge-kiosk-display.service"
echo
echo -e "  ${CYAN}4.${NC} Monitor kiosk status:"
echo -e "     ${CYAN}•${NC} sudo systemctl status fridge-kiosk-backend.service"
echo -e "     ${CYAN}•${NC} sudo journalctl -fu fridge-kiosk-backend.service"
echo 
print_status "Reboot your system to start using the kiosk:"
echo -e "  ${CYAN}•${NC} sudo reboot"
echo
print_status "Enjoy your new kiosk system!"

exit 0 