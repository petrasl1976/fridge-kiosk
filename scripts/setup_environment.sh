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
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"

print_header "SETTING UP SYSTEM ENVIRONMENT"
print_status "Installation directory: $INSTALL_DIR"

# Create necessary directories
print_step "Creating required directories..."
mkdir -p "$INSTALL_DIR/logs"
mkdir -p "$INSTALL_DIR/config"
touch "$INSTALL_DIR/logs/kiosk.log"
echo -e "  ${CYAN}•${NC} Created directory: $INSTALL_DIR/logs"

# Set ownership
if [ -n "$SUDO_USER" ]; then
    chown -R "$SUDO_USER:$SUDO_USER" "$INSTALL_DIR/logs"
    chown -R "$SUDO_USER:$SUDO_USER" "$INSTALL_DIR/config"
fi

# Create log files
print_step "Creating log files..."
touch "$INSTALL_DIR/logs/backend.log"
touch "$INSTALL_DIR/logs/backend-error.log"
echo -e "  ${CYAN}•${NC} Created log files in: $INSTALL_DIR/logs"

# Set permissions - ensure kiosk user has full access to the application files
print_step "Setting directory and file permissions..."
# Set owner to the user running the script (non-sudo)
chown -R $SUDO_USER:$SUDO_USER "$INSTALL_DIR"
echo -e "  ${CYAN}•${NC} Set ownership of all files to: $SUDO_USER"

# Update shebang in run.py with the actual venv path
print_step "Updating shebang in run.py..."
sed -i "1c #!$INSTALL_DIR/venv/bin/python3" "$INSTALL_DIR/run.py"
echo -e "  ${CYAN}•${NC} Updated run.py shebang to use virtual environment"

# Ensure logs directory and files are writable
chmod -R 755 "$INSTALL_DIR/logs"
chmod 666 "$INSTALL_DIR/logs/backend.log"
chmod 666 "$INSTALL_DIR/logs/backend-error.log"
echo -e "  ${CYAN}•${NC} Set write permissions for log files"

# Ensure data directory is writable
chmod -R 755 "$INSTALL_DIR/data"
echo -e "  ${CYAN}•${NC} Set permissions for data directory"

# Make sure scripts are executable
chmod +x "$INSTALL_DIR/run.py"
find "$INSTALL_DIR/scripts" -name "*.sh" -exec chmod +x {} \;
echo -e "  ${CYAN}•${NC} Set execute permissions for scripts"

print_success "Directories created and permissions set"

print_header "CONFIGURING KIOSK SERVICES"

# Create groups for the kiosk user if they don't exist
print_step "Setting up necessary groups..."
groupadd -f seat
echo -e "  ${CYAN}•${NC} Created/verified group: seat"
groupadd -f render
echo -e "  ${CYAN}•${NC} Created/verified group: render"
print_success "Groups created"

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

print_success "DRI device access configured"

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
print_success "Kiosk startup script created"

# Create systemd service files
print_step "Creating systemd service files..."

# Create the fridge-kiosk.service file
cat > /etc/systemd/system/fridge-kiosk.service << EOF
[Unit]
Description=Fridge Kiosk Service
After=network.target

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

[Install]
WantedBy=multi-user.target
EOF

print_success "Systemd service files created"

# Reload systemd configuration
print_step "Reloading systemd configuration..."
systemctl daemon-reload
print_success "Systemd configuration reloaded"

# Enable the service
print_step "Enabling the kiosk service..."
systemctl enable fridge-kiosk.service
print_success "Kiosk service enabled"

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
print_header "CONFIGURING LOG ROTATION"
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
print_success "Log rotation configured"

print_header "ENVIRONMENT SETUP COMPLETE"
print_success "System environment configured successfully!"
echo
print_status "To start the kiosk immediately, run:"
echo -e "  ${CYAN}sudo systemctl start fridge-kiosk.service${NC}"
echo

exit 0 