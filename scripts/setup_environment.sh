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
mkdir -p "$INSTALL_DIR/data"

# Set permissions
print_step "Setting directory permissions..."
chown -R $SUDO_USER:$SUDO_USER "$INSTALL_DIR/logs"
chown -R $SUDO_USER:$SUDO_USER "$INSTALL_DIR/data"
print_status "Directories created and permissions set"

print_header "CONFIGURING KIOSK SERVICES"

# Create groups for the kiosk user if they don't exist
print_step "Setting up necessary groups..."
groupadd -f seat
groupadd -f render
print_success "Groups created"

# Add user to required groups
print_step "Adding user $SUDO_USER to required groups..."
usermod -aG video,input,seat,render,tty $SUDO_USER
print_success "User added to groups"

# Create the kiosk start script
USER_HOME="/home/$SUDO_USER"
print_step "Creating kiosk startup script..."
cat > "$USER_HOME/start-kiosk.sh" << EOF
#!/bin/bash

# Nustatome aplinką
export XDG_RUNTIME_DIR=/run/user/1000
export WLR_BACKENDS=drm
export WLR_DRM_NO_ATOMIC=1
export WLR_DRM_DEVICES=/dev/dri/card0
export QT_QPA_PLATFORM=wayland
export GDK_BACKEND=wayland
export WAYLAND_DISPLAY=wayland-0
export DISPLAY=:0
export DBUS_SESSION_BUS_ADDRESS="unix:path=\$XDG_RUNTIME_DIR/bus"

# Tikriname ar yra reikalingi failai
if [ ! -f "$INSTALL_DIR/run.py" ]; then
    echo "Klaida: Nerastas run.py failas"
    exit 1
fi

# Sukuriame ir nustatome runtime direktoriją su sudo
sudo mkdir -p \$XDG_RUNTIME_DIR
sudo chown $SUDO_USER:$SUDO_USER \$XDG_RUNTIME_DIR
sudo chmod 700 \$XDG_RUNTIME_DIR

# Nustatome DRI teises
sudo chmod 666 /dev/dri/renderD128
sudo usermod -aG render,video $SUDO_USER

# Paleidžiame dbus sesiją
if [ ! -e "\$XDG_RUNTIME_DIR/bus" ]; then
    dbus-daemon --session --address="\$DBUS_SESSION_BUS_ADDRESS" --nofork --nopidfile --syslog-only &
    sleep 1
fi

# Paleidžiame aplikaciją fone
cd $INSTALL_DIR
python3 run.py &

# Laukiame kol aplikacija pasileis
sleep 3

# Paleidžiame cage ir chromium
cage -m last -- chromium-browser \\
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

# Laukiame kol cage pasileis
sleep 3

# Get display orientation from config file
ORIENTATION=\$(python3 -c "import json; print(json.load(open('$INSTALL_DIR/config/main.json')).get('system', {}).get('orientation', 'landscape'))")

# Bandome pasukti ekraną
if [ "\$ORIENTATION" = "portrait" ]; then
    WAYLAND_DISPLAY=\$WAYLAND_DISPLAY XDG_RUNTIME_DIR=\$XDG_RUNTIME_DIR wlr-randr --output HDMI-A-1 --transform 270
fi

# Laukiame pagrindinio proceso
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

print_header "SETTING UP PLUGIN DATA DIRECTORIES"
# Load main config to determine which plugins are enabled
CONFIG_FILE="$INSTALL_DIR/config/main.json"
if [ -f "$CONFIG_FILE" ]; then
    # Read enabled plugins from config file
    print_step "Reading enabled plugins from config file..."
    ENABLED_PLUGINS=$(jq -r '.enabledPlugins[]' "$CONFIG_FILE" 2>/dev/null)
    
    # If jq fails or config doesn't exist, setup all plugins
    if [ $? -ne 0 ] || [ -z "$ENABLED_PLUGINS" ]; then
        print_warning "Could not determine enabled plugins from config, setting up all plugins."
        # Get all plugin directories
        ENABLED_PLUGINS=$(find "$INSTALL_DIR/plugins" -maxdepth 1 -type d -not -path "$INSTALL_DIR/plugins" -exec basename {} \;)
    else
        print_status "Found enabled plugins: $ENABLED_PLUGINS"
    fi
else
    print_warning "Config file not found, setting up all plugins."
    # Get all plugin directories
    ENABLED_PLUGINS=$(find "$INSTALL_DIR/plugins" -maxdepth 1 -type d -not -path "$INSTALL_DIR/plugins" -exec basename {} \;)
fi

# Create data directories for each enabled plugin
print_step "Creating plugin data directories..."
for plugin in $ENABLED_PLUGINS; do
    PLUGIN_DATA_DIR="$INSTALL_DIR/data/$plugin"
    mkdir -p "$PLUGIN_DATA_DIR"
    chown -R $SUDO_USER:$SUDO_USER "$PLUGIN_DATA_DIR"
    print_status "Created data directory for: $plugin"
done

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
print_status "The following plugins are enabled:"
for plugin in $ENABLED_PLUGINS; do
    echo -e "  ${CYAN}•${NC} $plugin"
done
echo
print_status "To start the kiosk immediately, run:"
echo -e "  ${CYAN}sudo systemctl start fridge-kiosk.service${NC}"
echo

exit 0 