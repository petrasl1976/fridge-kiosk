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
echo -e "${CYAN}This script will completely remove the Fridge Kiosk system and revert system changes${NC}"
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
print_warning "This will completely remove the Fridge Kiosk installation and revert system changes!"
echo -e "Are you sure you want to continue? (y/N)"
read -r confirm
if [[ ! "$confirm" =~ ^[yY]$ ]]; then
    print_status "Uninstallation canceled."
    exit 0
fi

# Ask if user wants to remove installed packages
print_step "Package removal options"
echo -e "Do you want to remove ALL installed packages? (y/N)"
echo -e "This will remove: chromium-browser, cage, dbus-x11, python packages and ALL dependencies."
echo -e "WARNING: This might affect other applications that use these packages."
read -r remove_packages

# Stop and remove services
print_header "REMOVING SERVICES"
print_step "Stopping and removing services..."

# List of services to remove - includes only what we actually create
SERVICES=(
    "fridge-kiosk-backend.service"
    "fridge-kiosk-display.service"
    "xvfb.service"
)

# Handle all services in a loop
for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$service"; then
        echo -e "  ${CYAN}•${NC} Stopping $service..."
        systemctl stop "$service"
    fi

    if systemctl is-enabled --quiet "$service"; then
        echo -e "  ${CYAN}•${NC} Disabling $service..."
        systemctl disable "$service"
    fi

    if [ -f "/etc/systemd/system/$service" ]; then
        echo -e "  ${CYAN}•${NC} Removing $service..."
        rm "/etc/systemd/system/$service"
    fi
done

# Disable seatd service if it was enabled by our script
if systemctl is-enabled --quiet seatd.service; then
    echo -e "  ${CYAN}•${NC} Disabling seatd service..."
    systemctl disable seatd.service
    systemctl stop seatd.service
fi

# Reload systemd
systemctl daemon-reload
print_status "All services removed"

print_header "REMOVING CONFIGURATION FILES"

# Remove udev rules
print_step "Removing udev rules..."
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

    # Full list of packages from setup_dependencies.sh
    apt-get remove -y \
        chromium-browser \
        cage \
        dbus-x11 \
        seatd \
        wlr-randr \
        xvfb \
        pulseaudio \
        jq \
        unclutter \
        python3-pip \
        python3-venv \
        ffmpeg \
        libsm6 \
        libxext6 \
        alsa-utils \
        portaudio19-dev \
        libasound2-dev
    
    echo -e "  ${CYAN}•${NC} Packages removed"
    
    # Run autoremove to clean up dependencies
    print_step "Removing unused dependencies..."
    apt-get autoremove -y
    apt-get clean
    echo -e "  ${CYAN}•${NC} Dependencies cleaned up"
    
    print_step "Purging package configurations..."
    # Purge configs for critical components
    apt-get purge -y cage chromium-browser seatd
    echo -e "  ${CYAN}•${NC} Package configurations purged"
fi

print_header "CLEANING UP DATA"

# Remove data, logs, and temporary directories
print_step "Cleaning up data and log directories..."
rm -rf "$INSTALL_DIR/logs"
rm -rf /tmp/xdg-runtime-dir
# Clean chromium cache and data for the user
rm -rf "$USER_HOME/.cache/chromium"
rm -rf "$USER_HOME/.config/chromium"

# Clean up plugin data directories
for PLUGIN_DIR in "$INSTALL_DIR/plugins/"*/; do
    if [ -d "${PLUGIN_DIR}data" ]; then
        echo -e "  ${CYAN}•${NC} Removing data for plugin: $(basename "$PLUGIN_DIR")"
        rm -rf "${PLUGIN_DIR}data"
    fi
done
echo -e "  ${CYAN}•${NC} Data directories cleaned"

# Reset environment variables
print_step "Resetting environment variables..."
# Clean any environment configuration that might have been added to profile or bashrc
sed -i '/fridge-kiosk/d' "$USER_HOME/.profile" "$USER_HOME/.bashrc" 2>/dev/null || true
sed -i '/XDG_RUNTIME_DIR/d' "$USER_HOME/.profile" "$USER_HOME/.bashrc" 2>/dev/null || true
sed -i '/WAYLAND_DISPLAY/d' "$USER_HOME/.profile" "$USER_HOME/.bashrc" 2>/dev/null || true
echo -e "  ${CYAN}•${NC} Environment variables reset"

# Reset user groups
print_step "Resetting user groups..."
# Remove user from all groups added by the installation
for group in video input seat render tty; do
    if getent group $group >/dev/null; then
        echo -e "  ${CYAN}•${NC} Removing $SUDO_USER from group: $group"
        gpasswd -d $SUDO_USER $group 2>/dev/null || true
    fi
done

# Remove groups if created by our script
for group in seat render; do
    if getent group $group >/dev/null; then
        echo -e "  ${CYAN}•${NC} Checking if group $group can be removed..."
        # Only remove if no users are in the group
        if [ -z "$(getent group $group | cut -d: -f4)" ]; then
            echo -e "  ${CYAN}•${NC} Removing empty group: $group"
            groupdel $group 2>/dev/null || true
        else
            echo -e "  ${YELLOW}•${NC} Group $group still has members, not removing"
        fi
    fi
done
echo -e "  ${CYAN}•${NC} User groups reset"

# Find and restore any modified system config files
print_step "Scanning for modified system files..."
INSTALL_TIME=$(stat -c %Y "$INSTALL_DIR/scripts/install_kiosk.sh" 2>/dev/null || stat -c %Y "$INSTALL_DIR" 2>/dev/null)
if [ -n "$INSTALL_TIME" ]; then
    echo -e "  ${CYAN}•${NC} Searching for files modified since installation time: $(date -d @$INSTALL_TIME)"
    
    # Save the list to a file
    MODIFIED_FILES="$INSTALL_DIR/modified_files.txt"
    
    # Find all files in system directories modified after installation
    find /etc /lib /usr /var /bin /sbin -type f -newer "$INSTALL_DIR/scripts/install_kiosk.sh" 2>/dev/null | grep -v "^$INSTALL_DIR" > "$MODIFIED_FILES"
    
    echo -e "  ${CYAN}•${NC} Found $(wc -l < "$MODIFIED_FILES") modified system files."
    echo -e "  ${CYAN}•${NC} List saved to: $MODIFIED_FILES"
    print_status "You can review these files to check for remaining changes:"
    print_code "less $MODIFIED_FILES"
    
    # Fix permissions on the output file
    chown $SUDO_USER:$SUDO_USER "$MODIFIED_FILES"
else
    print_warning "Could not determine installation time. Skipping modified files scan."
fi

print_header "RESTORING SYSTEM DEFAULTS"

# Restore default behavior for system services if we modified them
print_step "Restoring default system configurations..."

# Restore default boot config if we modified it
if grep -q "fridge-kiosk" /boot/config.txt; then
    print_status "Restoring default boot configuration..."
    # Create backup of current config
    cp /boot/config.txt /boot/config.txt.backup
    # Remove our custom settings
    sed -i '/# fridge-kiosk/d' /boot/config.txt
    sed -i '/gpu_mem=/d' /boot/config.txt
    sed -i '/dtoverlay=vc4-kms-v3d/d' /boot/config.txt
    echo -e "  ${CYAN}•${NC} Boot configuration restored (backup at /boot/config.txt.backup)"
fi

# Restore default lightdm configuration if we modified it
if [ -f /etc/lightdm/lightdm.conf ] && grep -q "fridge-kiosk" /etc/lightdm/lightdm.conf; then
    print_status "Restoring default display manager configuration..."
    # Create backup of current config
    cp /etc/lightdm/lightdm.conf /etc/lightdm/lightdm.conf.backup
    # Remove our custom settings
    sed -i '/# fridge-kiosk/d' /etc/lightdm/lightdm.conf
    sed -i '/autologin-user=/d' /etc/lightdm/lightdm.conf
    echo -e "  ${CYAN}•${NC} Display manager configuration restored"
fi

print_header "UNINSTALLATION COMPLETE"
print_status "The Fridge Kiosk system has been completely removed and system changes have been reverted."
print_status "The following actions may be needed to completely restore the system:"
echo -e "  ${CYAN}•${NC} Reboot the system to apply all changes: sudo reboot"
echo -e "  ${CYAN}•${NC} Reinstall any packages you need that were removed"
echo -e "  ${CYAN}•${NC} Check $MODIFIED_FILES for any remaining system changes"
echo

print_warning "For a complete factory reset, consider reinstalling Raspberry Pi OS."

exit 0 