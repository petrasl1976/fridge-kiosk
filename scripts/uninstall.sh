#!/bin/bash

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

# Function to print code snippet
print_code() {
    echo -e "  ${CYAN}$1${NC}"
}

# Print banner
print_header "FRIDGE KIOSK UNINSTALLATION"
echo -e "${CYAN}This script will remove the Fridge Kiosk system${NC}"
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    print_error "This script must be run as root!"
    echo "Please run: sudo ./scripts/uninstall.sh"
    exit 1
fi

# Get paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"
SUDO_USER=${SUDO_USER:-$(whoami)}
USER_HOME="/home/$SUDO_USER"

print_status "Installation directory: $INSTALL_DIR"

# Ask for confirmation
print_warning "This will remove the Fridge Kiosk installation completely!"
echo -e "Are you sure you want to continue? (y/N)"
read -r confirm
if [[ ! "$confirm" =~ ^[yY]$ ]]; then
    print_status "Uninstallation canceled."
    exit 0
fi

# Ask if user wants to remove installed packages
print_step "Package removal options"
echo -e "Do you want to remove installed packages? (y/N)"
echo -e "This will remove: chromium-browser, cage, dbus-x11, and other dependencies."
echo -e "WARNING: This might affect other applications that use these packages."
read -r remove_packages

# Stop and remove services
print_header "REMOVING SERVICES"
print_step "Stopping and removing services..."

# Backend service
if systemctl is-active --quiet fridge-kiosk-backend.service; then
    echo -e "  ${CYAN}•${NC} Stopping fridge-kiosk-backend.service..."
    systemctl stop fridge-kiosk-backend.service
fi

if systemctl is-enabled --quiet fridge-kiosk-backend.service; then
    echo -e "  ${CYAN}•${NC} Disabling fridge-kiosk-backend.service..."
    systemctl disable fridge-kiosk-backend.service
fi

if [ -f /etc/systemd/system/fridge-kiosk-backend.service ]; then
    echo -e "  ${CYAN}•${NC} Removing fridge-kiosk-backend.service..."
    rm /etc/systemd/system/fridge-kiosk-backend.service
fi

# Display service
if systemctl is-active --quiet fridge-kiosk-display.service; then
    echo -e "  ${CYAN}•${NC} Stopping fridge-kiosk-display.service..."
    systemctl stop fridge-kiosk-display.service
fi

if systemctl is-enabled --quiet fridge-kiosk-display.service; then
    echo -e "  ${CYAN}•${NC} Disabling fridge-kiosk-display.service..."
    systemctl disable fridge-kiosk-display.service
fi

if [ -f /etc/systemd/system/fridge-kiosk-display.service ]; then
    echo -e "  ${CYAN}•${NC} Removing fridge-kiosk-display.service..."
    rm /etc/systemd/system/fridge-kiosk-display.service
fi

# Legacy service removal
if systemctl is-active --quiet fridge-kiosk.service; then
    echo -e "  ${CYAN}•${NC} Stopping fridge-kiosk.service..."
    systemctl stop fridge-kiosk.service
fi

if systemctl is-enabled --quiet fridge-kiosk.service; then
    echo -e "  ${CYAN}•${NC} Disabling fridge-kiosk.service..."
    systemctl disable fridge-kiosk.service
fi

if [ -f /etc/systemd/system/fridge-kiosk.service ]; then
    echo -e "  ${CYAN}•${NC} Removing fridge-kiosk.service..."
    rm /etc/systemd/system/fridge-kiosk.service
fi

# Xvfb fallback service
if systemctl is-active --quiet xvfb.service; then
    echo -e "  ${CYAN}•${NC} Stopping xvfb.service..."
    systemctl stop xvfb.service
fi

if systemctl is-enabled --quiet xvfb.service; then
    echo -e "  ${CYAN}•${NC} Disabling xvfb.service..."
    systemctl disable xvfb.service
fi

if [ -f /etc/systemd/system/xvfb.service ]; then
    echo -e "  ${CYAN}•${NC} Removing xvfb.service..."
    rm /etc/systemd/system/xvfb.service
fi

# Reload systemd
systemctl daemon-reload

print_header "REMOVING CONFIGURATION FILES"

# Remove udev rules
print_step "Removing udev rules..."
rm -f /etc/udev/rules.d/99-drm.rules
rm -f /etc/udev/rules.d/99-renderD128.rules
rm -f /etc/udev/rules.d/99-drm-permissions.rules
udevadm control --reload-rules
udevadm trigger
echo -e "  ${CYAN}•${NC} Device rules removed"

# Remove logrotate configuration
print_step "Removing log rotation configuration..."
rm -f /etc/logrotate.d/fridge-kiosk
echo -e "  ${CYAN}•${NC} Log rotation config removed"

# Remove startup script
print_step "Removing startup script..."
rm -f "$USER_HOME/start-kiosk.sh"
echo -e "  ${CYAN}•${NC} Kiosk startup script removed"

# Remove virtual environment if it exists
if [ -d "$INSTALL_DIR/venv" ]; then
    print_step "Removing Python virtual environment..."
    rm -rf "$INSTALL_DIR/venv"
    echo -e "  ${CYAN}•${NC} Python virtual environment removed"
fi

# If user chose to remove packages
if [[ "$remove_packages" =~ ^[yY]$ ]]; then
    print_header "REMOVING PACKAGES"
    print_step "Removing installed packages..."
    apt-get remove -y \
        chromium-browser \
        cage \
        dbus-x11 \
        seatd \
        wlr-randr \
        xvfb \
        pulseaudio \
        jq \
        unclutter
    
    echo -e "  ${CYAN}•${NC} Packages removed"
    print_warning "You may want to run 'apt autoremove' to remove unused dependencies."
fi

print_header "CLEANING UP DATA"

# Remove data and logs directories
print_step "Cleaning up data and log directories..."
rm -rf "$INSTALL_DIR/logs"
# Clean up plugin data directories
for PLUGIN_DIR in "$INSTALL_DIR/plugins/"*/; do
    if [ -d "${PLUGIN_DIR}data" ]; then
        echo -e "  ${CYAN}•${NC} Removing data for plugin: $(basename "$PLUGIN_DIR")"
        rm -rf "${PLUGIN_DIR}data"
    fi
done
echo -e "  ${CYAN}•${NC} Data directories cleaned"

# Reset user groups
print_step "Resetting user groups..."
# We can't completely undo group changes, but we can try to remove from specific groups
for group in seat render; do
    if getent group $group >/dev/null; then
        gpasswd -d $SUDO_USER $group 2>/dev/null || true
    fi
done
echo -e "  ${CYAN}•${NC} User removed from added groups"

# Find modified files section
print_step "Scanning for modified system files..."
INSTALL_TIME=$(stat -c %Y "$INSTALL_DIR/install.sh" 2>/dev/null || stat -c %Y "$INSTALL_DIR" 2>/dev/null)
if [ -n "$INSTALL_TIME" ]; then
    echo -e "  ${CYAN}•${NC} Searching for files modified since installation time: $(date -d @$INSTALL_TIME)"
    
    # Save the list to a file
    MODIFIED_FILES="$INSTALL_DIR/modified_files.txt"
    
    # Find all files in system directories modified after installation
    find /etc /lib /usr /var /bin /sbin -type f -newer "$INSTALL_DIR/install.sh" 2>/dev/null | grep -v "^$INSTALL_DIR" > "$MODIFIED_FILES"
    
    echo -e "  ${CYAN}•${NC} Found $(wc -l < "$MODIFIED_FILES") modified system files."
    echo -e "  ${CYAN}•${NC} List saved to: $MODIFIED_FILES"
    print_status "You can review these files to check for remaining changes:"
    print_code "less $MODIFIED_FILES"
    
    # Fix permissions on the output file
    chown $SUDO_USER:$SUDO_USER "$MODIFIED_FILES"
else
    print_warning "Could not determine installation time. Skipping modified files scan."
fi

print_step "Pulling latest updates from git repository..."
# Make sure we're in the installation directory
cd "$INSTALL_DIR"

# Reset any local changes to ensure clean pull
git reset --hard HEAD

# Pull the latest changes from the remote repository
if ! su -c "git pull" $SUDO_USER; then
    print_warning "Failed to pull latest updates from git. You may need to do this manually."
    print_code "cd $INSTALL_DIR && git pull"
fi

print_header "UNINSTALLATION COMPLETE"
print_success "The Fridge Kiosk system has been removed."
print_status "The following may need manual cleanup:"
echo -e "  ${CYAN}•${NC} User groups (your user may still be a member of video, input, tty)"
echo -e "  ${CYAN}•${NC} Browser cache and preferences"
echo -e "  ${CYAN}•${NC} Any remaining log files in the system"
echo
print_warning "For a complete system reset, consider reinstalling Raspberry Pi OS."

exit 0 