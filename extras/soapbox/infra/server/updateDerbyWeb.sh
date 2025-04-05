#!/bin/bash

# Navigate to the sbderbynet directory
cd /home/derby/sbderbynet || { echo "Directory /home/derby/sbderbynet not found."; exit 1; }

# Stopping the NGINX service   
echo "Stopping NGINX service..."
sudo systemctl stop nginx || { echo "Failed to stop NGINX service."; exit 1; }
echo "NGINX service stopped successfully."

# Perform git operations
echo "Fetching latest changes from remote..."
git fetch || { echo "Failed to fetch changes."; exit 1; }

echo "Checking out branch 'rahul-dev'..."
git checkout rahul-dev || { echo "Failed to checkout branch 'rahul-dev'."; exit 1; }

echo "Pulling latest changes from 'rahul-dev' branch..."
git pull || { echo "Failed to pull changes."; exit 1; }

# Copy website contents to the web server directory
echo "Copying website contents to /var/www/html/derbynet/..."
rsync -av /home/derby/sbderbynet/website/ /var/www/html/derbynet/ || { echo "Failed to copy website contents."; exit 1; }

# Restart the NGINX service
echo "Restarting NGINX service..."
sudo systemctl start nginx || { echo "Failed to restart NGINX service."; exit 1; }
echo "NGINX service restarted successfully."

echo "Update completed successfully."