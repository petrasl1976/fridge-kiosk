#!/bin/sh

# setup_environment.sh - Set up the system environment for the kiosk
# This script will configure the Raspberry Pi for kiosk mode operation

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

# Function to print warning messages
print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to print error messages
print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get the current directory and the install directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"

print_header "SETTING UP SYSTEM ENVIRONMENT"
print_status "Installation directory: $INSTALL_DIR"

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

# Create systemd service files
print_step "Creating systemd service files..."

# Create the backend service file
cat > /etc/systemd/system/fridge-kiosk-backend.service << EOF
[Unit]
Description=Fridge Kiosk Backend Service
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/run.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
echo -e "  ${CYAN}•${NC} Created backend service: fridge-kiosk-backend.service"

# Create the display service file
cat > /etc/systemd/system/fridge-kiosk-display.service << EOF
[Unit]
Description=Fridge Kiosk Display Service
After=network.target fridge-kiosk-backend.service
Requires=fridge-kiosk-backend.service
StartLimitIntervalSec=0

[Service]
User=$SUDO_USER
SupplementaryGroups=video render input seat tty
RuntimeDirectory=user/%U
RuntimeDirectoryMode=0700
Environment="XDG_RUNTIME_DIR=/run/user/1000"
Environment="WAYLAND_DISPLAY=wayland-0"
Environment="QT_QPA_PLATFORM=wayland"
Environment="GDK_BACKEND=wayland"
Environment="WLR_DRM_NO_ATOMIC=1"
Environment="WLR_RENDERER=pixman"
Environment="WLR_BACKENDS=drm"
Environment="DISPLAY=:0"
Environment="DBUS_SESSION_BUS_ADDRESS=unix:path=%t/user/%U/bus"
ExecStartPre=/bin/mkdir -p /run/user/1000
ExecStartPre=/bin/chmod 700 /run/user/1000
ExecStartPre=/bin/chown $SUDO_USER:$SUDO_USER /run/user/1000
ExecStart=$USER_HOME/start-kiosk.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
echo -e "  ${CYAN}•${NC} Created display service: fridge-kiosk-display.service"

# Reload systemd configuration
print_step "Reloading systemd configuration..."
systemctl daemon-reload

# Enable the services
print_step "Enabling services to start at boot..."
systemctl enable fridge-kiosk-backend.service
systemctl enable fridge-kiosk-display.service


# Start the backend service
print_step "Starting backend service..."
systemctl start fridge-kiosk-backend.service
echo -e "${BLUE}[INFO]${NC} Backend service status:"
systemctl status fridge-kiosk-backend.service --no-pager || true

print_header "SERVICE INFORMATION"
print_status "The following services have been created and enabled:"
echo -e "  ${CYAN}•${NC} fridge-kiosk-backend.service - Runs the Python backend API"
echo -e "  ${CYAN}•${NC} fridge-kiosk-display.service - Manages the kiosk display using Wayland/Cage"
echo
print_status "You can control the services with these commands:"
echo -e "  ${CYAN}•${NC} sudo systemctl start/stop/restart fridge-kiosk-backend.service"
echo -e "  ${CYAN}•${NC} sudo systemctl start/stop/restart fridge-kiosk-display.service"
echo -e "  ${CYAN}•${NC} sudo journalctl -fu fridge-kiosk-backend.service"

# Read enabled plugins from config to display in summary
print_header "CONFIGURATION SUMMARY"
CONFIG_FILE="$INSTALL_DIR/config/main.json"
if [ -f "$CONFIG_FILE" ]; then
    # Read enabled plugins from config file
    print_step "Reading enabled plugins from config file..."
    ENABLED_PLUGINS=$(jq -r '.enabled_plugins[]' "$CONFIG_FILE" 2>/dev/null | tr '\n' ' ')
    
    if [ $? -ne 0 ] || [ -z "$ENABLED_PLUGINS" ]; then
        print_warning "No enabled plugins found in config."
        # Get all plugin directories
        AVAILABLE_PLUGINS=$(find "$INSTALL_DIR/plugins" -maxdepth 1 -type d -not -path "$INSTALL_DIR/plugins" -exec basename {} \; | tr '\n' ' ')
        print_status "Available plugins that can be enabled in the config:"
        echo -e "  ${CYAN}•${NC} $AVAILABLE_PLUGINS"
    else
        print_status "Enabled plugins: $ENABLED_PLUGINS"
    fi
else
    print_warning "Config file not found."
    # Get all plugin directories
    AVAILABLE_PLUGINS=$(find "$INSTALL_DIR/plugins" -maxdepth 1 -type d -not -path "$INSTALL_DIR/plugins" -exec basename {} \; | tr '\n' ' ')
    print_status "Available plugins that can be enabled once you create a config:"
    echo -e "  ${CYAN}•${NC} $AVAILABLE_PLUGINS"
fi

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

print_header "INSTALLATION COMPLETE"
print_status "To start the kiosk immediately, run:"
echo -e "  ${CYAN}sudo systemctl start fridge-kiosk-display.service${NC}"
echo

exit 0 