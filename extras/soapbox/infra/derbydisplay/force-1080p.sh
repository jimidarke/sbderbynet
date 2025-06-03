#!/bin/bash
# Force 1080p Resolution Script for DerbyNet Display
# This script can be run manually to force 1080p resolution on TVs

echo "DerbyNet Display - Force 1080p Resolution"
echo "=========================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)" 
   exit 1
fi

# Function to set HDMI resolution using tvservice (if available)
set_tvservice_resolution() {
    if command -v tvservice >/dev/null 2>&1; then
        echo "Setting HDMI resolution using tvservice..."
        tvservice -e "CEA 16 HDMI"  # 1920x1080 @ 60Hz
        sleep 2
        fbset -depth 8
        fbset -depth 32
        return 0
    else
        echo "tvservice not available"
        return 1
    fi
}

# Function to set resolution using xrandr (if in X session)
set_xrandr_resolution() {
    if command -v xrandr >/dev/null 2>&1 && [ -n "$DISPLAY" ]; then
        echo "Setting resolution using xrandr..."
        # Get the connected display name
        DISPLAY_NAME=$(xrandr | grep " connected" | cut -d " " -f1 | head -1)
        if [ -n "$DISPLAY_NAME" ]; then
            echo "Setting $DISPLAY_NAME to 1920x1080..."
            xrandr --output "$DISPLAY_NAME" --mode 1920x1080 --rate 60
            return 0
        else
            echo "No connected display found via xrandr"
            return 1
        fi
    else
        echo "xrandr not available or no DISPLAY set"
        return 1
    fi
}

# Function to restart X server with proper resolution
restart_x_with_resolution() {
    echo "Restarting X server to apply resolution changes..."
    
    # Kill any existing X sessions
    pkill -f "xinit\|startx\|Xorg"
    sleep 2
    
    # Wait for X to fully stop
    while pgrep -f "Xorg" >/dev/null; do
        sleep 1
    done
    
    # Start X with specific resolution
    if [ -f /home/kioskuser/.xinitrc ]; then
        echo "Starting X session as kioskuser..."
        sudo -u kioskuser startx /home/kioskuser/.xinitrc -- -keeptty -verbose 3 &
        echo "X server restarted"
    else
        echo "No .xinitrc found for kioskuser"
        return 1
    fi
}

# Main execution
echo "Attempting to force 1080p resolution..."

# Try tvservice first (Raspberry Pi specific)
if set_tvservice_resolution; then
    echo "Resolution set via tvservice"
elif set_xrandr_resolution; then
    echo "Resolution set via xrandr"
else
    echo "Direct resolution setting failed, restarting X server..."
    restart_x_with_resolution
fi

# Verify resolution
echo ""
echo "Current resolution information:"
if command -v tvservice >/dev/null 2>&1; then
    echo "HDMI status:"
    tvservice -s
fi

if command -v xrandr >/dev/null 2>&1 && [ -n "$DISPLAY" ]; then
    echo "X11 resolution:"
    xrandr | grep "*"
fi

echo ""
echo "If the display is still not correct:"
echo "1. Check TV settings - disable overscan/zoom"
echo "2. Try different HDMI ports on the TV"
echo "3. Restart the system: sudo reboot"
echo ""
echo "For persistent changes, run the derbydisplay setup.sh script"