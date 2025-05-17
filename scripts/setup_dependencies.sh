#!/bin/sh

# setup_dependencies.sh - Install all required dependencies for the system
# This script will install system packages, Python packages, and plugin-specific dependencies

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
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_title() { echo -e "${CYAN}•${NC} $1\n"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"

print_header "INSTALLING SYSTEM DEPENDENCIES"
print_status "Installation directory: $INSTALL_DIR"

# Update package lists
print_step "Updating package lists..."
apt-get update

# Install system dependencies - using cage instead of full X server
print_step "Installing system packages for kiosk display..."
apt-get install -y \
    git \
    python3 \
    python3-pip \
    python3-venv \
    chromium-browser \
    cage \
    dbus-x11 \
    seatd \
    wlr-randr

# Install additional utility packages
print_status "Installing utility packages..."
apt-get install -y \
    jq \
    unclutter \
    pulseaudio

print_status "Installing media support packages..."
# Install additional packages for media support
apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    alsa-utils \
    portaudio19-dev \
    libasound2-dev

print_header "CONFIGURING SYSTEM PERMISSIONS"
# Create required groups
print_step "Setting up system groups..."
groupadd -f seat
groupadd -f render

# Add user to required groups
print_step "Adding user $SUDO_USER to required groups..."
usermod -aG video,input,seat,render,tty $SUDO_USER
print_status "User $SUDO_USER added to: video, input, seat, render, tty"

# Set DRM permissions
print_step "Setting up display permissions..."
echo 'SUBSYSTEM=="drm", ACTION=="add", MODE="0660", GROUP="video"' > /etc/udev/rules.d/99-drm.rules
echo 'KERNEL=="renderD128", SUBSYSTEM=="drm", MODE="0666"' > /etc/udev/rules.d/99-renderD128.rules
udevadm control --reload-rules
udevadm trigger
print_status "DRM permissions set up successfully"

# Enable seatd service
print_step "Enabling display compositor service (seatd)..."
systemctl enable --now seatd
print_success "Display compositor service enabled"

print_header "SETTING UP PYTHON ENVIRONMENT"
# Create virtual environment if it doesn't exist
VENV_DIR="$INSTALL_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    print_step "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    chown -R $SUDO_USER:$SUDO_USER "$VENV_DIR"
    chmod -R 755 "$VENV_DIR/bin"
    # Ensure all files in bin directory are executable
    chmod +x "$VENV_DIR/bin/"*
    print_success "Virtual environment created at: $VENV_DIR"
else
    print_status "Using existing virtual environment at: $VENV_DIR"
fi

# Activate virtual environment
print_step "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
print_status "Virtual environment activated"

# Install base Python requirements
print_step "Installing base Python packages..."
pip install --upgrade pip
print_status "Installing core Python packages (this may take a while)..."
pip install \
    flask \
    requests \
    google-auth \
    google-auth-oauthlib \
    google-auth-httplib2 \
    google-api-python-client \
    pytz \
    python-dotenv \
    schedule \
    jinja2

# Add additional packages that were in the original
print_status "Installing additional Python packages from original installation..."
pip install \
    broadlink \
    PyNaCl

print_success "Base Python packages installed successfully"

print_header "INSTALLING PLUGIN DEPENDENCIES"
# Load main config to determine which plugins are enabled
CONFIG_FILE="$INSTALL_DIR/config/main.json"
AVAILABLE_PLUGINS=$(find "$INSTALL_DIR/plugins" -maxdepth 1 -type d -not -path "$INSTALL_DIR/plugins" -exec basename {} \;)

if [ -f "$CONFIG_FILE" ]; then
    # Read enabled plugins from config file
    print_step "Reading enabled plugins from config file..."
    ENABLED_PLUGINS=$(jq -r '.enabled_plugins[]' "$CONFIG_FILE" 2>/dev/null | tr '\n' ' ')
    
    # If jq fails or config doesn't exist, don't install any plugins
    if [ $? -ne 0 ] || [ -z "$ENABLED_PLUGINS" ]; then
        print_warning "No enabled plugins found in config."
        print_status "Available plugins that can be enabled in config:"
        for plugin in $AVAILABLE_PLUGINS; do
            print_title "$plugin"
        done
        ENABLED_PLUGINS=""
    else
        print_status "Found enabled plugins: $ENABLED_PLUGINS"
    fi
else
    print_warning "Config file not found at $CONFIG_FILE."
    print_status "Available plugins that can be enabled once you create a config:"
    for plugin in $AVAILABLE_PLUGINS; do
        print_title "$plugin"
    done
    ENABLED_PLUGINS=""
fi

# Install dependencies for each enabled plugin
if [ ! -z "$ENABLED_PLUGINS" ]; then
    for plugin in $ENABLED_PLUGINS; do
        PLUGIN_DIR="$INSTALL_DIR/plugins/$plugin"
        REQUIREMENTS_FILE="$PLUGIN_DIR/requirements.txt"
        
        if [ -d "$PLUGIN_DIR" ]; then
            print_step "Installing dependencies for plugin: $plugin"
            
            if [ -f "$REQUIREMENTS_FILE" ]; then
                print_status "Installing requirements from: $REQUIREMENTS_FILE"
                pip install -r "$REQUIREMENTS_FILE"
                print_success "Plugin $plugin requirements installed"
            else
                print_status "No requirements.txt found for plugin: $plugin"
            fi
            
            # Special handling for discord plugin if enabled
            if [ "$plugin" = "discord-text-channel" ]; then
                print_step "Installing Discord dependencies..."
                pip install "py-cord[voice]"
                print_success "Discord dependencies installed"
            fi
        else
            print_warning "Plugin directory not found: $plugin"
        fi
    done
else
    print_status "No plugin dependencies will be installed."
fi

print_header "INSTALLATION COMPLETE"
print_success "All dependencies installed successfully!"
echo
if [ ! -z "$ENABLED_PLUGINS" ]; then
    print_status "The following plugins are enabled:"
    print_title "$ENABLED_PLUGINS"
fi
echo

exit 0 