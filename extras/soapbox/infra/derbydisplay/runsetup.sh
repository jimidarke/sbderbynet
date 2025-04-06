#!/bin/bash

# This script is used to update the hostname and download the derbynet files from the server and is run on boot

# Customized for the display setup

#  sudo rsync -avz --delete rsync://192.168.100.10/derbynet/derbydisplay/ /opt/derbynet/

# Path to the derbyid.txt file
DERBY_ID_FILE="/boot/firmware/derbyid.txt"
SERVER_IP="192.168.100.10"
RSYNC_SERVER="rsync://$SERVER_IP/derbynet/derbydisplay/"
LOCAL_DIR="/opt/derbynet/"

# checks if /opt/derbynet (LOCAL_DIR) folder exists, if not creates
if [ ! -d $LOCAL_DIR ]; then
    sudo mkdir $LOCAL_DIR
    sudo chown derby:derby -R $LOCAL_DIR 
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


# checks if display specific features were added to the /boot/firmware/config.txt file
#if ! grep -q "#DERBYNET" /boot/firmware/config.txt; then
#    echo "Adding Derby Display settings to boot config."
#    sudo bash -c "echo '#DERBYNET' >> /boot/firmware/config.txt"
#    sudo bash -c "echo 'hdmi_force_hotplug=1' >> /boot/firmware/config.txt"
#    sudo bash -c "echo 'hdmi_group=2' >> /boot/firmware/config.txt"
#    sudo bash -c "echo 'hdmi_mode=82' >> /boot/firmware/config.txt"
#    sudo bash -c "echo 'disable_overscan=1' >> /boot/firmware/config.txt"
#    sudo bash -c "echo 'gpu_mem=128' >> /boot/firmware/config.txt"
#    sudo bash -c "echo 'dtoverlay=disable-bt' >> /boot/firmware/config.txt"
#    sudo systemctl disable --now systemd-journald
#    sudo systemctl disable --now rsyslog
#    sudo systemctl disable --now logrotate 
#    sudo systemctl disable --now cron
#    sudo systemctl mask tmp.mount
#    TOREBOOT=1
#fi

# perform system update only if internet is available and /boot/updated file is missing
if [ ! -f /boot/firmware/updated ]; then
    echo "Updated file missing. Checking for internet connection."
    if ping -q -c 1 -W 1 google.com >/dev/null; then
        echo "Internet connection available. Updating system."
        sudo apt update
        sudo apt upgrade -y #sudo apt install -y 
        sudo apt install -y rsync python3 python3-pip mosquitto-clients unclutter epiphany-browser x11-xserver-utils xautomation unclutter
        sudo pip install paho-mqtt psutil raspberrypi-tm1637 --break
        sudo apt autoremove -y
        sudo apt clean
        sudo touch /boot/firmware/updated
        TOREBOOT=1
    else
        echo "No internet connection available. Skipping system update."
    fi
else
    echo "Update file found. Skipping system update."
fi

# checks if the local user is set to login automatically (display user)
#if [ ! -d /etc/systemd/system/getty@tty1.service.d ]; then
#    echo "Updating getty@tty1 service for automatic login."
#    # Create the displayuser with no password
#    sudo adduser --disabled-password --gecos "" displayuser
#    # Add the user to necessary groups
#    sudo usermod -aG sudo,tty,dialout,video,audio,plugdev,netdev displayuser
#    sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
#    sudo mkdir -p /home/displayuser/derbydisplay
#    sudo bash -c "echo [Service] >> /etc/systemd/system/getty@tty1.service.d/override.conf"
#    sudo bash -c "echo ExecStart=  >> /etc/systemd/system/getty@tty1.service.d/override.conf"
#    sudo bash -c "echo ExecStart=-/sbin/agetty --autologin displayuser --noclear %I $TERM >> /etc/systemd/system/getty@tty1.service.d/override.conf"
#    sudo bash -c "echo Type=idle >> /etc/systemd/system/getty@tty1.service.d/override.conf"
#    sudo bash -c "echo DenyUsers displayuser >> /etc/ssh/sshd_config"
#    sudo systemctl restart ssh
#    sudo systemctl daemon-reload
#    sudo systemctl enable getty@tty1.service
#    # Autostart Openbox session
#    sudo mkdir -p /home/displayuser/.config/openbox
#    sudo bash -c "echo xset -dpms >> /home/displayuser/.config/openbox/autostart"
#    sudo bash -c "echo xset s off >> /home/displayuser/.config/openbox/autostart"
#    sudo bash -c "echo xset s noblank >> /home/displayuser/.config/openbox/autostart"
#    sudo bash -c "echo unclutter -idle 0.5 -root & >> /home/displayuser/.config/openbox/autostart" 
#    TOREBOOT=1
#else
#    echo "getty@tty1 service already configured for automatic login."
#fi

# downloads the derbynet files from the server with rsync
sudo rsync -avz --delete ${RSYNC_SERVER} ${LOCAL_DIR}

# checks if the derbydisplay service is installed and running, if not installs and starts them
if [ ! -f /etc/systemd/system/derbydisplay.service ]; then
    echo "DerbyDisplay service not found. Installing and starting the service."
    sudo cp ${LOCAL_DIR}files/derbydisplay.service /etc/systemd/system/
    sudo systemctl enable derbydisplay
    sudo systemctl start derbydisplay
    TOREBOOT=1
else
    echo "DerbyDisplay service found. Starting."
    sudo systemctl restart derbydisplay
fi

# reboots if TOREBOOT is set to 1
if [ $TOREBOOT -eq 1 ]; then
    echo "Rebooting system."
    sudo reboot
fi 