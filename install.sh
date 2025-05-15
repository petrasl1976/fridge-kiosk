#!/bin/bash

# Fridge Kiosk Installation Script
# This script will install and configure the Fridge Kiosk system on a Raspberry Pi.

set -e

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

# Print banner
print_header "FRIDGE KIOSK INSTALLER"
echo -e "${CYAN}A modular, plugin-based kiosk display system for Raspberry Pi${NC}"
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    print_error "This script must be run as root!"
    echo "Please run: sudo ./install.sh"
    exit 1
fi

# Current directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create installation directory if it doesn't exist
INSTALL_DIR="/home/$SUDO_USER/fridge-kiosk"
print_status "Installing to: $INSTALL_DIR"

# If directory already exists, ask to remove it
if [ -d "$INSTALL_DIR" ]; then
    print_warning "Installation directory already exists."
    read -p "Do you want to remove the existing installation? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "Removing existing installation..."
        rm -rf "$INSTALL_DIR"
    else
        print_error "Installation aborted."
        exit 1
    fi
fi

# Copy files to installation directory
print_step "Copying files to installation directory..."
mkdir -p "$INSTALL_DIR"
cp -r ./* "$INSTALL_DIR"
chown -R $SUDO_USER:$SUDO_USER "$INSTALL_DIR"
print_status "Files copied to $INSTALL_DIR"

# Set execute permissions on scripts
print_step "Setting execute permissions on scripts..."
find "$INSTALL_DIR/scripts" -name "*.sh" -exec chmod +x {} \;
chmod +x "$INSTALL_DIR/install.sh"
print_status "Permissions set"

# Run setup scripts in the correct order
print_header "RUNNING SETUP SCRIPTS"

print_step "Setting up dependencies..."
bash "$INSTALL_DIR/scripts/setup_dependencies.sh"

print_step "Configuring environment..."
bash "$INSTALL_DIR/scripts/setup_environment.sh"

print_step "Setting up services..."
bash "$INSTALL_DIR/scripts/setup_service.sh"

# Create .env file if it doesn't exist
if [ ! -f "$INSTALL_DIR/config/.env" ]; then
    print_step "Creating .env file..."
    cp "$INSTALL_DIR/config/.env.example" "$INSTALL_DIR/config/.env"
    chown $SUDO_USER:$SUDO_USER "$INSTALL_DIR/config/.env"
    print_warning "Please edit the .env file to add your API keys and credentials:"
    echo -e "${YELLOW}    nano $INSTALL_DIR/config/.env${NC}"
else
    print_status "Using existing .env file"
fi

print_header "INSTALLATION COMPLETED!"
print_success "The Fridge Kiosk has been installed to: $INSTALL_DIR"
echo
print_status "You can configure the system by editing:"
echo -e "  ${CYAN}•${NC} Main config: $INSTALL_DIR/config/main.json"
echo -e "  ${CYAN}•${NC} Environment: $INSTALL_DIR/config/.env"
echo
print_status "The system has been set up to start automatically on boot."
echo -e "  ${CYAN}•${NC} To start it manually, run: sudo systemctl start fridge-kiosk"
echo -e "  ${CYAN}•${NC} To check status, run: sudo systemctl status fridge-kiosk"
echo -e "  ${CYAN}•${NC} To view logs, run: journalctl -u fridge-kiosk-backend -f"
echo 
print_status "Reboot the system to start using the kiosk:"
echo -e "  ${CYAN}•${NC} sudo reboot"
echo
print_success "Enjoy your Fridge Kiosk!"

exit 0 