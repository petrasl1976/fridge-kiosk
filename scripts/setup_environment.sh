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

# Configure auto-login
print_header "CONFIGURING AUTO-LOGIN"

# Check if we're using systemd (newer Raspbian)
if [ -f /lib/systemd/system/getty@.service ]; then
    print_step "Setting up automatic login for user $SUDO_USER..."
    # Configure systemd auto-login for TTY1
    mkdir -p /etc/systemd/system/getty@tty1.service.d/
    cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $SUDO_USER --noclear %I \$TERM
EOF
    print_success "Auto-login configured via systemd"
else
    print_error "Could not configure auto-login, system may not be using systemd"
    exit 1
fi

print_header "CONFIGURING DISPLAY ENVIRONMENT"
# Create startup script for Cage Wayland compositor
USER_HOME="/home/$SUDO_USER"
print_step "Creating kiosk startup script..."
cat > "$USER_HOME/start-kiosk.sh" << EOF
#!/bin/bash

# Set XDG_RUNTIME_DIR, which is needed for Wayland
export XDG_RUNTIME_DIR=/tmp/xdg-runtime-dir
mkdir -p \$XDG_RUNTIME_DIR
chmod 700 \$XDG_RUNTIME_DIR

# Start dbus session if needed
if [ ! -e "\$XDG_RUNTIME_DIR/bus" ]; then
    dbus-daemon --session --address="\$DBUS_SESSION_BUS_ADDRESS" --nofork --nopidfile --syslog-only &
    sleep 1
fi

# Start cage and chromium
echo "Starting Chromium in kiosk mode..."
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

# Wait for cage to start and create Wayland session
echo "Waiting for display compositor to initialize..."
sleep 5

# Check which monitors are connected and rotate the screen if needed
OUTPUT=\$(wlr-randr | grep -o -m 1 "^HDMI-[A-Za-z0-9\-]*")
if [ -n "\$OUTPUT" ]; then
    echo "Found monitor: \$OUTPUT"
    
    # Get display orientation from config file
    ORIENTATION=\$(jq -r '.system.display_orientation' $INSTALL_DIR/config/main.json 2>/dev/null || echo "landscape")
    
    # Apply rotation based on orientation setting
    if [ "\$ORIENTATION" = "portrait" ]; then
        echo "Setting screen orientation to portrait mode..."
        for i in {1..3}; do
            if wlr-randr --output "\$OUTPUT" --transform 270; then
                echo "Screen rotated to portrait mode successfully"
                break
            fi
            sleep 2
        done
    else
        echo "Using landscape orientation"
    fi
else
    echo "WARNING: Monitor not found, unable to configure screen orientation"
fi

# Wait for main process
echo "Kiosk display started successfully"
wait
EOF

# Set permissions
print_step "Setting permissions for startup script..."
chown $SUDO_USER:$SUDO_USER "$USER_HOME/start-kiosk.sh"
chmod +x "$USER_HOME/start-kiosk.sh"
print_success "Kiosk startup script created"

# Configure the .bash_profile to start the kiosk on login
print_step "Configuring automatic kiosk start on login..."
cat > "$USER_HOME/.bash_profile" << EOF
# Auto-start kiosk on login
if [ "\$(tty)" = "/dev/tty1" ]; then
    # If not already running, start the kiosk
    if ! pgrep -f "cage" > /dev/null; then
        echo "Starting kiosk..."
        # Wait for backend service to be ready
        until curl -s http://localhost:8080 > /dev/null 2>&1; do 
            echo "Waiting for backend to start..."
            sleep 2
        done
        exec ~/start-kiosk.sh
    fi
fi
EOF

# Set permissions
chown $SUDO_USER:$SUDO_USER "$USER_HOME/.bash_profile"
print_success "Login profile configured"

print_header "SETTING UP PLUGIN DATA DIRECTORIES"
# Load main config to determine which plugins are enabled
CONFIG_FILE="$INSTALL_DIR/config/main.json"
if [ -f "$CONFIG_FILE" ]; then
    # Read enabled plugins from config file
    print_step "Reading enabled plugins from config file..."
    ENABLED_PLUGINS=$(jq -r '.enabled_plugins[]' "$CONFIG_FILE" 2>/dev/null)
    
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

exit 0 