#!/bin/bash

# Set up environment
export XDG_RUNTIME_DIR=/run/user/1000
export WLR_BACKENDS=drm
export WLR_DRM_NO_ATOMIC=1
export WLR_DRM_DEVICES=/dev/dri/card0
export QT_QPA_PLATFORM=wayland
export GDK_BACKEND=wayland
export WAYLAND_DISPLAY=wayland-0
export DISPLAY=:0
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"

# Check for required files
if [ ! -f "/home/kiosk/fridge-kiosk/backend/run.py" ]; then
    echo "Error: backend/run.py file not found"
    exit 1
fi

# Create and configure runtime directory with sudo
sudo mkdir -p $XDG_RUNTIME_DIR
sudo chown kiosk:kiosk $XDG_RUNTIME_DIR
sudo chmod 700 $XDG_RUNTIME_DIR

# Set DRI permissions
sudo chmod 666 /dev/dri/renderD128
sudo usermod -aG render,video kiosk

# Start dbus session if not already running
if [ ! -e "$XDG_RUNTIME_DIR/bus" ]; then
    dbus-daemon --session --address="$DBUS_SESSION_BUS_ADDRESS" --nofork --nopidfile --syslog-only &
    sleep 1
fi

# Wait for the backend API to be ready
until curl -s http://localhost:8080 > /dev/null 2>&1; do
    echo "Waiting for backend API to be ready..."
    sleep 2
done

# Launch cage and chromium
cage -m last -- chromium-browser \
    --kiosk \
    --disable-gpu \
    --disable-software-rasterizer \
    --disable-dev-shm-usage \
    --no-sandbox \
    --disable-dbus \
    --incognito \
    --disable-extensions \
    --disable-plugins \
    --disable-popup-blocking \
    --disable-notifications \
    http://localhost:8080 &

# Wait for cage to launch
sleep 3

# Try to rotate the screen if needed
WAYLAND_DISPLAY=$WAYLAND_DISPLAY XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR wlr-randr --output HDMI-A-1 --transform 270

# Wait for the main process
wait 