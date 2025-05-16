#!/bin/bash

echo "=================================================="
echo "   FRIDGE KIOSK UNINSTALLATION SCRIPT             "
echo "=================================================="
echo
echo "This script will:"
echo "  • Stop and remove all kiosk services"
echo "  • Remove system dependencies (optional)"
echo "  • Remove udev rules"
echo "  • Remove log rotation configuration"
echo "  • Clean up all created files"
echo
echo "WARNING: This will completely remove the kiosk system!"
echo "=================================================="
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root!"
    echo "Please run: sudo ./uninstall.sh"
    exit 1
fi

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$SCRIPT_DIR"
SUDO_USER=${SUDO_USER:-$(whoami)}
USER_HOME="/home/$SUDO_USER"

# Ask for confirmation
echo "This will completely remove the Fridge Kiosk installation at:"
echo "$INSTALL_DIR"
echo
echo "Are you sure you want to continue? (y/N)"
read -r confirm
if [[ ! "$confirm" =~ ^[yY]$ ]]; then
    echo "Uninstallation canceled."
    exit 0
fi

# Ask if user wants to remove installed packages
echo
echo "Do you want to remove installed packages? (y/N)"
echo "This will remove: chromium-browser, cage, dbus-x11, seatd, wlr-randr, etc."
echo "WARNING: This might affect other applications that use these packages."
read -r remove_packages
echo

echo "Stopping and disabling services..."
# Stop and disable services
systemctl stop fridge-kiosk-display.service 2>/dev/null || true
systemctl stop fridge-kiosk-backend.service 2>/dev/null || true
systemctl stop fridge-kiosk.service 2>/dev/null || true
systemctl stop xvfb.service 2>/dev/null || true

systemctl disable fridge-kiosk-display.service 2>/dev/null || true
systemctl disable fridge-kiosk-backend.service 2>/dev/null || true
systemctl disable fridge-kiosk.service 2>/dev/null || true
systemctl disable xvfb.service 2>/dev/null || true

echo "Removing service files..."
# Remove service files
rm -f /etc/systemd/system/fridge-kiosk-display.service
rm -f /etc/systemd/system/fridge-kiosk-backend.service
rm -f /etc/systemd/system/fridge-kiosk.service
rm -f /etc/systemd/system/xvfb.service

# Reload systemd
systemctl daemon-reload

echo "Removing udev rules..."
# Remove udev rules
rm -f /etc/udev/rules.d/99-drm.rules
rm -f /etc/udev/rules.d/99-renderD128.rules
rm -f /etc/udev/rules.d/99-drm-permissions.rules
udevadm control --reload-rules
udevadm trigger

echo "Removing log rotation configuration..."
# Remove logrotate configuration
rm -f /etc/logrotate.d/fridge-kiosk

# Remove startup script
echo "Removing startup script..."
rm -f "$USER_HOME/start-kiosk.sh"

# Remove virtual environment if it exists
if [ -d "$INSTALL_DIR/venv" ]; then
    echo "Removing Python virtual environment..."
    rm -rf "$INSTALL_DIR/venv"
fi

# If user chose to remove packages
if [[ "$remove_packages" =~ ^[yY]$ ]]; then
    echo "Removing installed packages..."
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
    
    echo "You may want to run 'apt autoremove' to remove unused dependencies."
fi

echo "Cleaning up data and log directories..."
# Remove data and logs directories
rm -rf "$INSTALL_DIR/data"
rm -rf "$INSTALL_DIR/logs"

echo "Resetting user groups..."
# We can't completely undo group changes, but we can try to remove from specific groups
# Note: This can't guarantee original state restoration
for group in seat render; do
    if getent group $group >/dev/null; then
        gpasswd -d $SUDO_USER $group 2>/dev/null || true
    fi
done

echo "Pulling latest updates from git repository..."
# Make sure we're in the installation directory
cd "$INSTALL_DIR"

# Reset any local changes to ensure clean pull
git reset --hard HEAD

# Pull the latest changes from the remote repository
if ! su -c "git pull" $SUDO_USER; then
    echo "WARNING: Failed to pull latest updates from git. You may need to do this manually."
    echo "Run: cd $INSTALL_DIR && git pull"
fi

echo "=================================================="
echo "UNINSTALLATION COMPLETE"
echo "=================================================="
echo
echo "The following may need manual cleanup:"
echo " • User groups (your user may still be a member of video, input, tty)"
echo " • Any remaining log files in the system"
echo " • Browser cache and preferences"
echo
echo "For a complete system reset, consider reinstalling Raspberry Pi OS."

exit 0 