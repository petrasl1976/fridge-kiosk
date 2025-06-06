#!/bin/bash -e

# Fridge Kiosk Setup Script
# This script configures the system environment, services, and permissions 
# for the Fridge Kiosk application.

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

print_header "FRIDGE KIOSK SETUP"
print_info "Setting up environment and services for the kiosk system"

cd "$INSTALL_DIR"
print_info "Installation directory: $INSTALL_DIR"

if [ ! -f "$INSTALL_DIR/config/.env" ]; then
    print_step "Creating .env file..."
    cp "$INSTALL_DIR/config/.env.example" "$INSTALL_DIR/config/.env" 2>/dev/null || touch "$INSTALL_DIR/config/.env"
# Create .env.example if it doesn't exist
if [ ! -f "$INSTALL_DIR/config/.env.example" ]; then
    print_step "Creating .env.example template..."
    cat > "$INSTALL_DIR/config/.env.example" << EOF
# Google Services
GOOGLE_CALENDAR_ID=primary
# You may also need GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
# if not using client_secret.json

# Location for Weather
LATITUDE=54.6872
LONGITUDE=25.2797
LOCATION_NAME=Vilnius, Lithuania

# Other services
EOF
fi
    print_info "Use .env file to add your API keys and credentials if needed"
    print_info "vim $INSTALL_DIR/config/.env"
else
    print_info "Using existing .env file"
fi

print_step "Setting execute permissions on scripts..."
find "$INSTALL_DIR/scripts" -name "*.sh" -exec chmod +x {} \;

for directory in logs config; do
    print_info "Creating directory: $INSTALL_DIR/$directory"
    mkdir -p "$INSTALL_DIR/$directory"
done

print_info "Creating log file: $INSTALL_DIR/logs/fridge-kiosk.log"
touch "$INSTALL_DIR/logs/fridge-kiosk.log"

if [ -n "$SUDO_USER" ]; then
    chown -R "$SUDO_USER:$SUDO_USER" "$INSTALL_DIR"
fi

print_info "Setting write permissions for log file"
chmod -R 755 "$INSTALL_DIR/logs"
chmod 666 "$INSTALL_DIR/logs/fridge-kiosk.log"

print_step "Fixing shebang in run.py..."
sed -i "1c #!$INSTALL_DIR/venv/bin/python3" "$INSTALL_DIR/backend/run.py"

print_step "Making scripts executable..."
chmod +x "$INSTALL_DIR/backend/run.py"
chmod +x "$INSTALL_DIR/scripts/"*.sh 
chmod +x "$INSTALL_DIR/scripts/fridge-kiosk-display.sh"

print_step "Enabling display compositor service (seatd)..."
systemctl enable --now seatd

print_step "Setting up system groups: seat, render"
groupadd -f seat
groupadd -f render

print_step "Adding user $SUDO_USER to groups: video, input, seat, render, tty"
usermod -aG video,input,seat,render,tty $SUDO_USER

print_step "Creating udev rules for display permissions..."
echo 'SUBSYSTEM=="drm", ACTION=="add", MODE="0660", GROUP="video"' > /etc/udev/rules.d/99-drm.rules
echo 'KERNEL=="renderD128", SUBSYSTEM=="drm", MODE="0666"' > /etc/udev/rules.d/99-renderD128.rules

print_step "Reloading udev rules..."
udevadm control --reload-rules
udevadm trigger

print_step "Checking DRI devices..."
if [ ! -e "/dev/dri/card0" ] || [ ! -e "/dev/dri/renderD128" ]; then
    print_warning "DRI devices missing. Setting up Raspberry Pi graphics configuration..."
    
    # Add VC4 KMS V3D overlay for better graphics support
    if [ -f "/boot/config.txt" ]; then
        if ! grep -q "dtoverlay=vc4-kms-v3d" "/boot/config.txt"; then
            print_info "Adding VC4 KMS V3D overlay to /boot/config.txt"
            echo "dtoverlay=vc4-kms-v3d" | sudo tee -a /boot/config.txt
            
            # Ensure proper memory split for GPU
            if ! grep -q "^gpu_mem=" "/boot/config.txt"; then
                echo "gpu_mem=128" | sudo tee -a /boot/config.txt
                print_info "Set GPU memory to 128MB"
            fi
            
            print_warning "A reboot will be required after setup to apply graphics changes"
        else
            print_info "VC4 KMS V3D overlay already configured"
        fi
    else
        print_warning "Cannot find /boot/config.txt file"
    fi
fi

print_header "CONFIGURING KIOSK SERVICES"
BACKEND_SERVICE="fridge-kiosk-backend.service"
DISPLAY_SERVICE="fridge-kiosk-display.service"

# Create the backend service file
print_step "Creating backend service ($BACKEND_SERVICE)..."
cat > /etc/systemd/system/$BACKEND_SERVICE << EOF
[Unit]
Description=Fridge Kiosk Backend Service
After=network.target

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/backend/run.py
Restart=always
RestartSec=5
StandardOutput=append:$INSTALL_DIR/logs/fridge-kiosk.log
StandardError=append:$INSTALL_DIR/logs/fridge-kiosk.log
Environment="PYTHONUNBUFFERED=1"
# Permissions to read temperature data
ReadWritePaths=/sys/class/thermal/thermal_zone0
ProtectSystem=true

[Install]
WantedBy=multi-user.target
EOF
print_info "Created service file: /etc/systemd/system/$BACKEND_SERVICE"
print_info "Backend service file created"

print_step "Creating kiosk display service ($DISPLAY_SERVICE)..."
cat > /etc/systemd/system/$DISPLAY_SERVICE << EOF
[Unit]
Description=Fridge Kiosk Display Service
After=network.target $BACKEND_SERVICE
Requires=$BACKEND_SERVICE
BindsTo=$BACKEND_SERVICE

[Service]
User=$SUDO_USER
SupplementaryGroups=video render input seat tty
RuntimeDirectory=user/%U
RuntimeDirectoryMode=0700
Environment="XDG_RUNTIME_DIR=/tmp/xdg-runtime-dir"
Environment="WAYLAND_DISPLAY=wayland-0"
Environment="QT_QPA_PLATFORM=wayland"
Environment="GDK_BACKEND=wayland"
Environment="WLR_DRM_NO_ATOMIC=1"
Environment="WLR_RENDERER=pixman"
Environment="WLR_BACKENDS=drm"
Environment="DISPLAY=:0"
Environment="DBUS_SESSION_BUS_ADDRESS=unix:path=%t/user/%U/bus"
ExecStartPre=/bin/mkdir -p /tmp/xdg-runtime-dir
ExecStartPre=/bin/chmod 700 /tmp/xdg-runtime-dir
ExecStartPre=/bin/chown $SUDO_USER:$SUDO_USER /tmp/xdg-runtime-dir
ExecStartPre=/bin/bash -c "until curl -s http://localhost:8080 > /dev/null 2>&1; do sleep 2; done"
ExecStart=$INSTALL_DIR/scripts/fridge-kiosk-display.sh
Restart=always

[Install]
WantedBy=multi-user.target
EOF
print_info "Created service file: /etc/systemd/system/$DISPLAY_SERVICE"
print_info "Display service file created"

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

print_step "Reloading systemd daemon..."
systemctl daemon-reload

print_step "Enabling and starting $BACKEND_SERVICE"
systemctl enable $BACKEND_SERVICE
systemctl start $BACKEND_SERVICE
print_step "Enabling and starting $DISPLAY_SERVICE"
systemctl enable $DISPLAY_SERVICE

print_header "SETUP COMPLETED!"
echo
print_info "Next steps:"
echo -e "  ${CYAN}1.${NC} Services have been enabled automatically. To manage them:"
echo -e "     ${CYAN}•${NC} sudo systemctl enable/disable fridge-kiosk-backend.service"
echo -e "     ${CYAN}•${NC} sudo systemctl enable/disable fridge-kiosk-display.service"
echo
echo -e "  ${CYAN}2.${NC} Configure the system by editing these files:"
echo -e "     ${CYAN}•${NC} Main configuration: $INSTALL_DIR/config/main.json"
echo -e "     ${CYAN}•${NC} Environment variables: $INSTALL_DIR/config/.env"
echo 
print_info "Reboot your system to start using the kiosk:"
print_info "sudo reboot"