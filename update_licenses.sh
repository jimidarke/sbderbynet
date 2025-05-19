#\!/bin/bash
# Script to add license headers to files

# Get the license headers
PYTHON_HEADER=$(cat /root/code/sbderbynet/LICENSE_HEADER_PYTHON.txt)
GENERAL_HEADER=$(cat /root/code/sbderbynet/LICENSE_HEADER.txt)

# Function to add header to Python files
add_python_header() {
  local file=$1
  if \! grep -q "Copyright (c)" "$file"; then
    echo "$PYTHON_HEADER" > "$file.new"
    cat "$file" >> "$file.new"
    mv "$file.new" "$file"
    echo "Added header to $file"
  else
    echo "Header already exists in $file"
  fi
}

# Function to add header to other files
add_general_header() {
  local file=$1
  if \! grep -q "Copyright (c)" "$file"; then
    echo "$GENERAL_HEADER" > "$file.new"
    cat "$file" >> "$file.new"
    mv "$file.new" "$file"
    echo "Added header to $file"
  else
    echo "Header already exists in $file"
  fi
}

# Process Python files in the soapbox directory
find /root/code/sbderbynet/extras/soapbox -name "*.py" -type f  < /dev/null |  while read -r file; do
  add_python_header "$file"
done

echo "License headers have been updated in Python files."

# Create a sample file to demonstrate adding to PHP files
echo "<?php\n\n// Sample PHP file\necho 'Hello, world\!';\n?>" > /root/code/sbderbynet/sample.php
add_general_header "/root/code/sbderbynet/sample.php"

echo "Sample created with license header."

chmod +x /root/code/sbderbynet/update_licenses.sh
