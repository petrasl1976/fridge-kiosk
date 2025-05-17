#!/bin/bash

# Fridge Kiosk Uninstaller
# This script completely removes the Fridge Kiosk system and reverts all system changes


# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    print_error "This script must be run as root!"
    echo "Please run: sudo ./scripts/uninstall.sh"
    exit 1
fi

print_header "FRIDGE KIOSK UNINSTALLATION"
print_title "This script will completely remove the Fridge Kiosk system and revert system changes"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/utils.sh"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"

print_header "REMOVING SERVICES"
print_step "Stopping and removing services..."
SERVICES=(
    "fridge-kiosk-backend.service"
    "fridge-kiosk-display.service"
)

# all services in a loop
for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$service"; then
        print_title "Stopping $service..."
        systemctl stop "$service"
    fi

    if systemctl is-enabled --quiet "$service"; then
        print_title "Disabling $service..."
        systemctl disable "$service"
    fi

    if [ -f "/etc/systemd/system/$service" ]; then
        print_title "Removing $service..."
        rm "/etc/systemd/system/$service"
    fi
done

print_step "Disabling seatd service..."
if systemctl is-enabled --quiet seatd.service; then
    systemctl disable seatd.service
    systemctl stop seatd.service
fi

systemctl daemon-reload
print_info "All services removed"

print_header "REMOVING CONFIGURATION FILES"

print_step "Removing udev rules..."
rm -f /etc/udev/rules.d/99-drm-permissions.rules
udevadm control --reload-rules
udevadm trigger

print_step "Removing log rotation configuration..."
rm -f /etc/logrotate.d/fridge-kiosk

print_step "Removing startup script..."
rm -f "$USER_HOME/start-kiosk.sh"

print_step "Removing virtual environment..."
if [ -d "$INSTALL_DIR/venv" ]; then
    print_step "Removing Python virtual environment..."
    rm -rf "$INSTALL_DIR/venv"

fi

print_header "REMOVING PACKAGES"
print_step "Removing installed packages..."

apt-get purge -y \
    chromium-browser \
    cage \
    dbus-x11 \
    seatd \
    wlr-randr \
    jq \
    unclutter \
    python3-pip \
    python3-venv \
    ffmpeg \
    libsm6 \
    libxext6

print_step "Removing unused dependencies..."
apt-get autoremove -y
apt-get clean


print_step "Cleaning up data and log directories..."
rm -rf "$INSTALL_DIR/logs"
rm -rf /tmp/xdg-runtime-dir
rm -rf "$USER_HOME/.cache/chromium"
rm -rf "$USER_HOME/.config/chromium"

for PLUGIN_DIR in "$INSTALL_DIR/plugins/"*/; do
    if [ -d "${PLUGIN_DIR}data" ]; then
        print_title "Removing data for plugin: $(basename "$PLUGIN_DIR")"
        rm -rf "${PLUGIN_DIR}data"
    fi
done

print_step "Resetting environment variables..."
sed -i '/fridge-kiosk/d' "$USER_HOME/.profile" "$USER_HOME/.bashrc" 2>/dev/null || true
sed -i '/XDG_RUNTIME_DIR/d' "$USER_HOME/.profile" "$USER_HOME/.bashrc" 2>/dev/null || true
sed -i '/WAYLAND_DISPLAY/d' "$USER_HOME/.profile" "$USER_HOME/.bashrc" 2>/dev/null || true

print_step "Resetting user groups..."
for group in video input seat render tty; do
    if getent group $group >/dev/null; then
        print_title "Removing $SUDO_USER from group: $group"
        gpasswd -d $SUDO_USER $group 2>/dev/null || true
    fi
done

print_step "Removing groups created by install.sh..."
groupdel seat 2>/dev/null || true
groupdel render 2>/dev/null || true

print_header "UNINSTALLATION COMPLETE"
print_info "The Fridge Kiosk system has been completely removed and system changes have been reverted."
