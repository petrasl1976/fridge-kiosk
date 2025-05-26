#!/bin/bash -e

# Fridge Kiosk Installer
# This script installs all required dependencies for the system
# including system packages, Python packages, and sets up the virtual environment

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    print_error "This script must be run as root!"
    echo "Please run: sudo ./setup.sh"
    exit 1
fi

print_header "FRIDGE KIOSK INSTALLATION"
print_title "Installing dependencies and setting up Python environment"
print_info "Installation directory: $INSTALL_DIR"

print_step "Updating package lists..."
apt-get update

print_step "Installing system packages for kiosk display..."
apt-get install -y --no-install-recommends \
    git \
    python3 \
    python3-pip \
    python3-venv \
    chromium-browser \
    cage \
    dbus-x11 \
    seatd \
    wlr-randr

print_info "Installing utility packages..."
apt-get install -y --no-install-recommends \
    jq \
    unclutter

print_info "Installing media support packages..."
apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6

print_header "SETTING UP PYTHON ENVIRONMENT"
VENV_DIR="$INSTALL_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    print_step "Creating Python virtual environment at: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
    chown -R $SUDO_USER:$SUDO_USER "$VENV_DIR"
    chmod -R 755 "$VENV_DIR/bin"
    chmod +x "$VENV_DIR/bin/"*
else
    print_info "Using existing virtual environment at: $VENV_DIR"
fi

print_step "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

print_step "Installing base Python packages..."
pip install --upgrade pip

print_info "Installing core Python packages (this may take a while)..."
# Define required package versions
declare -A PACKAGE_VERSIONS=(
    ["flask"]="3.1.1"
    ["requests"]="2.32.3"
    ["google-auth"]="2.29.0"
    ["google-auth-oauthlib"]="1.2.0"
    ["google-auth-httplib2"]="0.2.0"
    ["google-api-python-client"]="2.126.0"
    ["pytz"]="2025.2"
    ["python-dotenv"]="1.1.0"
    ["schedule"]="1.2.2"
    ["jinja2"]="3.1.6"
)

# Install packages with specific versions
for package in "${!PACKAGE_VERSIONS[@]}"; do
    version="${PACKAGE_VERSIONS[$package]}"
    print_info "Installing $package==$version..."
    pip install "$package==$version"
done

print_header "INSTALLING PLUGIN DEPENDENCIES"
CONFIG_FILE="$INSTALL_DIR/config/main.json"
AVAILABLE_PLUGINS=$(find "$INSTALL_DIR/plugins" -maxdepth 1 -type d -not -path "$INSTALL_DIR/plugins" -exec basename {} \;)
print_info "Available plugins: $AVAILABLE_PLUGINS"

print_step "Reading plugins from configuration..."
if [ -f "$CONFIG_FILE" ]; then
    ENABLED_PLUGINS=$(jq -r '.enabledPlugins[]' "$CONFIG_FILE" 2>/dev/null | tr '\n' ' ' || echo "")
fi

if [ -z "$ENABLED_PLUGINS" ]; then
    print_info "No plugins enabled. Available plugins:"
else
    print_info "Enabled plugins: $ENABLED_PLUGINS"
fi

print_step "Installing dependencies for each enabled plugin..."
if [ ! -z "$ENABLED_PLUGINS" ]; then
    for plugin in $ENABLED_PLUGINS; do
        PLUGIN_DIR="$INSTALL_DIR/plugins/$plugin"
        REQUIREMENTS_FILE="$PLUGIN_DIR/requirements.txt"
        
        if [ -d "$PLUGIN_DIR" ]; then
            print_step "Installing dependencies for plugin: $plugin"
            
            if [ -f "$REQUIREMENTS_FILE" ]; then
                print_info "Installing requirements from: $REQUIREMENTS_FILE"
                # Read requirements and install with specific versions
                while IFS= read -r line || [ -n "$line" ]; do
                    # Skip empty lines and comments
                    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
                    
                    # Extract package name and version
                    if [[ "$line" =~ ([^=<>]+)([=<>].*)? ]]; then
                        package="${BASH_REMATCH[1]}"
                        version="${BASH_REMATCH[2]}"
                        print_info "Installing $package$version..."
                        pip install "$package$version"
                    fi
                done < "$REQUIREMENTS_FILE"
            else
                print_info "No requirements.txt found for plugin: $plugin"
            fi
        else
            print_warning "Plugin directory not found: $plugin"
        fi
    done
else
    print_info "No plugin dependencies will be installed."
fi

print_header "INSTALLATION COMPLETE"