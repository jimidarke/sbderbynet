#!/bin/bash

# Dual-purpose script for web kiosk and RTSP to HLS streaming
# Usage: sudo ./kiosk_streamer_setup.sh

# Define variables
UBUNTU_VERSION="Ubuntu 22.04.5 LTS"
RTSP_CAMERA_URL="rtsp://admin:all4theKids@192.168.100.20:554/21"
PRIMARY_DISPLAY_URL="http://192.168.100.10/derbynet/kiosk.php"
SECONDARY_DISPLAY_URL="http://192.168.100.10/derbynet/replay.php"
HLS_OUTPUT_DIR="/var/www/html/hls"
NGINX_CONF_DIR="/etc/nginx"
LOG_DIR="/var/log/kiosk_streamer"

# Function to check and install required packages
install_packages() {
    echo "Installing required packages..."
    apt-get update
    apt-get install -y nginx ffmpeg chromium-browser xdotool unclutter
}

# Function to set up the dual-display kiosk
setup_kiosk() {
    echo "Setting up dual-display kiosk..."
    # Create a script to launch Chromium in kiosk mode on both displays
    cat << EOF > /usr/local/bin/start_kiosk.sh
#!/bin/bash
export DISPLAY=:0
chromium-browser --kiosk --no-first-run $PRIMARY_DISPLAY_URL &
chromium-browser --kiosk --no-first-run $SECONDARY_DISPLAY_URL &
unclutter -idle 0.1 -root &
EOF

    chmod +x /usr/local/bin/start_kiosk.sh

    # Create a systemd service for the kiosk
    cat << EOF > /etc/systemd/system/kiosk.service
[Unit]
Description=Dual Display Kiosk
Wants=graphical.target
After=graphical.target

[Service]
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/your_username/.Xauthority
Type=simple
ExecStart=/bin/bash /usr/local/bin/start_kiosk.sh
Restart=on-abort
User=your_username

[Install]
WantedBy=graphical.target
EOF

    systemctl enable kiosk.service
    systemctl start kiosk.service
}

# Function to set up RTSP to HLS transcoding
setup_transcoding() {
    echo "Setting up RTSP to HLS transcoding..."
    mkdir -p $HLS_OUTPUT_DIR

    # Create a script for RTSP to HLS transcoding
    cat << EOF > /usr/local/bin/rtsp_to_hls.sh
#!/bin/bash
while true; do
    ffmpeg -i $RTSP_CAMERA_URL -c:v libx264 -c:a aac -f hls -hls_time 2 -hls_list_size 3 -hls_flags delete_segments $HLS_OUTPUT_DIR/stream.m3u8
    sleep 1
done
EOF

    chmod +x /usr/local/bin/rtsp_to_hls.sh

    # Create a systemd service for transcoding
    cat << EOF > /etc/systemd/system/rtsp_to_hls.service
[Unit]
Description=RTSP to HLS Transcoding
After=network.target

[Service]
ExecStart=/bin/bash /usr/local/bin/rtsp_to_hls.sh
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

    systemctl enable rtsp_to_hls.service
    systemctl start rtsp_to_hls.service
}

# Function to configure Nginx for HLS streaming
configure_nginx() {
    echo "Configuring Nginx for HLS streaming..."
    cat << EOF > $NGINX_CONF_DIR/sites-available/hls_stream
server {
    listen 80;
    server_name localhost;

    location /hls {
        types {
            application/vnd.apple.mpegurl m3u8;
            video/mp2t ts;
        }
        root /var/www/html;
        add_header Cache-Control no-cache;
        add_header Access-Control-Allow-Origin *;
    }
}
EOF

    ln -sf $NGINX_CONF_DIR/sites-available/hls_stream $NGINX_CONF_DIR/sites-enabled/
    rm -f $NGINX_CONF_DIR/sites-enabled/default
    systemctl restart nginx
}

# Function for setting up logging
setup_logging() {
    echo "Setting up logging..."
    mkdir -p $LOG_DIR

    # Configure rsyslog
    echo "local0.* $LOG_DIR/kiosk_streamer.log" > /etc/rsyslog.d/kiosk_streamer.conf
    systemctl restart rsyslog
}

# Function for setting up cleanup of old streaming files
setup_cleanup() {
    echo "Setting up cleanup for HLS files..."
    # Create a cleanup script
    cat << EOF > /usr/local/bin/hls_cleanup.sh
#!/bin/bash
find $HLS_OUTPUT_DIR -type f -name "*.ts" -mmin +5 -delete
EOF

    chmod +x /usr/local/bin/hls_cleanup.sh

    # Add a cron job to run the cleanup script every 5 minutes
    echo "*/5 * * * * root /usr/local/bin/hls_cleanup.sh" > /etc/cron.d/hls_cleanup
}

# Main function to run all the setup functions
main() {
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        echo "Please run as root or with sudo"
        exit 1
    fi
     
    # Check Ubuntu version
    if ! grep -q "$UBUNTU_VERSION" /etc/os-release; then
        echo "Warning: This script was designed for $UBUNTU_VERSION. Your version may differ."
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    echo "Starting setup for dual-purpose kiosk and streaming system..."
    
    install_packages
    setup_kiosk
    setup_transcoding
    configure_nginx
    setup_logging
    setup_cleanup
    
    echo "Setup completed successfully!"
}

# Run the main function
main

echo "Script completed. Please reboot the system to start the kiosk and streaming service."