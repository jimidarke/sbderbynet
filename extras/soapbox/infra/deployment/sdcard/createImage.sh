#!/bin/bash

# Check if the user provided a source drive path
if [ -z "$1" ]; then
    echo "Usage: $0 /dev/sdX"
    exit 1
fi

SOURCE_DRIVE=$1
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_IMAGE="raspberrypi_${TIMESTAMP}.img"

# Confirm the source drive exists
if [ ! -b "$SOURCE_DRIVE" ]; then
    echo "Error: $SOURCE_DRIVE is not a valid block device."
    exit 1
fi

# Create the raw image using dd
echo "Creating image from $SOURCE_DRIVE..."
sudo dd if=$SOURCE_DRIVE of=$OUTPUT_IMAGE bs=4M status=progress

if [ $? -ne 0 ]; then
    echo "Error: Failed to create the image."
    exit 1
fi

# Shrink the image using pishrink
echo "Shrinking the image..."
sudo ./pishrink $OUTPUT_IMAGE

if [ $? -ne 0 ]; then
    echo "Error: Failed to shrink the image."
    exit 1
fi

# Compress the final image
echo "Compressing the image..."
gzip -v $OUTPUT_IMAGE

if [ $? -eq 0 ]; then
    echo "Image created and compressed successfully: ${OUTPUT_IMAGE}.gz"
else
    echo "Error: Compression failed."
    exit 1
fi

sync 

# Cleanup
echo "Cleaning up..."
rm $OUTPUT_IMAGE
echo "Done."
echo "Image preparation complete."
echo "You can find the compressed image at ${OUTPUT_IMAGE}.gz"
