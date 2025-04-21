#!/bin/bash

# Path to the derbyid.txt file
DERBY_ID_FILE="/boot/firmware/derbyid.txt"
SERVER_IP="192.168.100.10"
RSYNC_SERVER="rsync://$SERVER_IP/derbynet/derbydisplay/"
LOCAL_DIR="/opt/derbynet/"

# checks if /opt/derbynet (LOCAL_DIR) folder exists, if not creates
if [ ! -d $LOCAL_DIR ]; then
    sudo mkdir $LOCAL_DIR
    sudo chown $KIOSK_USER:$KIOSK_USER -R $LOCAL_DIR
    sudo chmod 775 -R $LOCAL_DIR
fi

# Check if the derbyid.txt file exists
if [ ! -f "$DERBY_ID_FILE" ]; then
    echo "Error: $DERBY_ID_FILE not found."
    exit 1
fi

# Read the derby ID from the file
DERBY_ID=$(cat "$DERBY_ID_FILE")
echo "Derby ID: $DERBY_ID"
# Get the current hostname
CURRENT_HOSTNAME=$(hostname)

TOREBOOT=0

# Apply system time settings 
# Ensure systemd-timesyncd is installed
if ! command -v systemctl &> /dev/null; then
    echo "systemd-timesyncd is not installed. Installing..."
    sudo apt update && sudo apt install -y systemd-timesyncd
fi

if ! grep -q "$SERVER_IP" /etc/systemd/timesyncd.conf; then
    echo "Time server not found in /etc/systemd/timesyncd.conf. Adding..."
    sudo bash -c "echo 'NTP=$SERVER_IP' >> /etc/systemd/timesyncd.conf"
    sudo systemctl restart systemd-timesyncd
    TOREBOOT=1
fi
timedatectl show-timesync --all

# checks if power saving features were added to the /boot/firmware/config.txt file
if ! grep -q "#DERBYNET" /boot/firmware/config.txt; then
    sudo bash -c "echo '#DERBYNET' >> /boot/firmware/config.txt"
    sudo bash -c "echo 'dtparam=audio=off' >> /boot/firmware/config.txt"
    sudo bash -c "echo 'dtparam=uart=off' >> /boot/firmware/config.txt"
    sudo bash -c "echo 'dtoverlay=disable-bt' >> /boot/firmware/config.txt"
    sudo bash -c "echo 'hdmi_force_hotplug=1' >> /boot/firmware/config.txt"
    sudo bash -c "echo 'hdmi_group=2' >> /boot/firmware/config.txt"
    sudo bash -c "echo 'hdmi_mode=82' >> /boot/firmware/config.txt" # 1920x1080 @ 60Hz
    sudo bash -c "echo 'disable_overscan=1' >> /boot/firmware/config.txt"
    sudo systemctl disable --now systemd-journald
    sudo systemctl disable --now rsyslog
    sudo systemctl disable --now logrotate 
    sudo systemctl disable --now cron
    sudo systemctl mask tmp.mount
    TOREBOOT=1
fi

# Check if the current hostname matches the derby ID
if [ "$CURRENT_HOSTNAME" != "$DERBY_ID" ]; then
    echo "Hostname does not match derby ID. Updating hostname to $DERBY_ID."
    # Set the new hostname
    sudo hostnamectl set-hostname "$DERBY_ID"
    sudo bash -c "echo '127.0.1.1   $DERBY_ID' >> /etc/hosts"
    TOREBOOT=1
else
    echo "Hostname matches derby ID. No changes needed."
fi


# downloads the derbynet files from the server with rsync
sudo rsync -avz --delete ${RSYNC_SERVER} ${LOCAL_DIR}

# perform system update only if internet is available and /boot/updated file is missing
if [ ! -f /boot/firmware/updated ]; then
    echo "Updated file missing. Checking for internet connection."
    if ping -q -c 1 -W 1 google.com >/dev/null; then
        echo "Internet connection available. Updating system."
        sudo apt update
        sudo apt install -y --no-install-recommends \
            chromium-browser xserver-xorg xinit x11-xserver-utils openbox unclutter feh upower dbus unclutter-xfixes
        sudo apt install -y rsync python3-pip mosquitto-clients
        sudo pip install paho-mqtt psutil raspberrypi-tm1637 --break
        sudo apt autoremove -y
        sudo apt clean
        #run kiosk.sh 
        sudo chmod +x /opt/derbynet/kiosk.sh
        # run the kiosk.sh script in the background but wait for it to finish
        sudo /opt/derbynet/kiosk.sh &
        # wait for the script to finish 
        wait $!
        # create the updated file to indicate that the system has been updated
        sudo touch /boot/firmware/updated
        TOREBOOT=1
    else
        echo "No internet connection available. Skipping system update."
    fi
else
    echo "Update file not found. Skipping system update."
fi

# checks if the display service is installed and running, if not installs and starts them
if [ ! -f /etc/systemd/system/derbydisplay.service ]; then
    echo "DerbyNet Display service not found. Installing and starting the service."
    sudo cp ${LOCAL_DIR}derbydisplay.service /etc/systemd/system/
    sudo systemctl enable derbydisplay
    sudo systemctl start derbydisplay
    TOREBOOT=1
else
    echo "DerbyNet Derby Display service found. Starting."
    sudo systemctl restart derbydisplay
fi

# reboots if TOREBOOT is set to 1
if [ $TOREBOOT -eq 1 ]; then
    echo "Rebooting system."
    sudo reboot
fi 