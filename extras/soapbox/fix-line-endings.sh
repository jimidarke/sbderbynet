#!/bin/bash
# Fix DOS line endings in shell scripts after rsync transfer
# Run this script on the Linux target after rsync

echo "Fixing DOS line endings in shell scripts..."

# Find all .sh files and convert line endings
find . -name "*.sh" -type f -exec dos2unix {} \;

# Make shell scripts executable
find . -name "*.sh" -type f -exec chmod +x {} \;

# Also fix any Python scripts that might have been transferred
find . -name "*.py" -type f -exec dos2unix {} \;

echo "Line ending fixes complete"
echo "Files processed:"
find . -name "*.sh" -o -name "*.py" | head -10