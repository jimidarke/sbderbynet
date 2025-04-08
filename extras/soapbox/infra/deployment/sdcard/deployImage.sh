#!/bin/bash

# Check if the user provided the necessary arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 /dev/sdX name"
    exit 1
fi

SOURCE_DRIVE=$1
NAME=$2

# Check if the source drive exists
if [ ! -b "$SOURCE_DRIVE" ]; then
    echo "Error: $SOURCE_DRIVE is not a valid block device."
    exit 1
fi

# Find the latest compressed image in the current directory
LATEST_IMAGE=$(ls -t *.img 2>/dev/null | head -n 1)

if [ -z "$LATEST_IMAGE" ]; then
    echo "Error: No image file found in the current directory."
    exit 1
fi

echo "Loading image $LATEST_IMAGE to $SOURCE_DRIVE..."

# Decompress and load the image onto the SD card
#gzip -dc "$LATEST_IMAGE" | sudo dd of=$SOURCE_DRIVE bs=4M status=progress
dd if="$LATEST_IMAGE" of=$SOURCE_DRIVE bs=4M status=progress

if [ $? -ne 0 ]; then
    echo "Error: Failed to write the image."
    exit 1
fi

# Mount the boot partition to create the derbyid.txt file
BOOT_PARTITION=$(lsblk -lnpo NAME,PARTLABEL | grep -i "boot" | awk '{print $1}')

if [ -z "$BOOT_PARTITION" ]; then
    echo "Error: Boot partition not found."
    exit 1
fi

sudo mount $BOOT_PARTITION /mnt

if [ $? -ne 0 ]; then
    echo "Error: Failed to mount the boot partition."
    exit 1
fi

echo "$NAME" | sudo tee /mnt/derbyid.txt

sudo umount /mnt

echo "Image loaded successfully, and derbyid.txt created. Setup script will run on first boot."
echo "You can now safely eject the SD card."