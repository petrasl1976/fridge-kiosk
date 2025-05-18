#!/bin/bash

# Set up environment
export XDG_RUNTIME_DIR=/tmp/xdg-runtime-dir
export WAYLAND_DISPLAY=wayland-0
export DISPLAY=:0
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"

# Set display options for Raspberry Pi
export WLR_DRM_NO_ATOMIC=1
export WLR_RENDERER=pixman
export WLR_BACKENDS=drm

# Create and configure runtime directory
mkdir -p $XDG_RUNTIME_DIR
chmod 700 $XDG_RUNTIME_DIR

# Start dbus session if not already running
if [ ! -e "$XDG_RUNTIME_DIR/bus" ]; then
    dbus-daemon --session --address="$DBUS_SESSION_BUS_ADDRESS" --nofork --nopidfile --syslog-only &
    sleep 1
fi

# Wait for backend to be ready
until curl -s http://localhost:8080 > /dev/null 2>&1; do
    echo "Waiting for backend API to be ready..."
    sleep 2
done

echo "Starting kiosk display on Raspberry Pi..."

# Launch cage and chromium
cage -d -- chromium-browser \
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

# Wait for the display to start
sleep 3

# Rotate screen - use exactly the same approach as the old code
OUTPUT=$(wlr-randr | grep -o -m 1 "^HDMI-[A-Za-z0-9\-]*")
if [ -n "$OUTPUT" ]; then
    echo "Found monitor: $OUTPUT"
    for i in {1..3}; do
        if wlr-randr --output "$OUTPUT" --transform 270; then
            echo "Screen rotated successfully"
            break
        fi
        sleep 2
    done
else
    echo "Monitor not found"
fi

# Wait for the main process
wait 