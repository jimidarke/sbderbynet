#!/bin/bash

# Secure Configuration Management for HLS Feed
# Handles secure credential storage and config file generation

# Constants
SECURE_ENV_DIR="/opt/hlsfeed/secure"
CREDENTIALS_FILE="$SECURE_ENV_DIR/credentials.enc"
KEY_FILE="$SECURE_ENV_DIR/key.bin"
CONFIG_TEMPLATE="/opt/hlsfeed/config.template"
CONFIG_OUTPUT="/opt/hlsfeed/config.env"

# Create secure directory if it doesn't exist
mkdir -p $SECURE_ENV_DIR
chmod 700 $SECURE_ENV_DIR

usage() {
  echo "Usage: $0 [command]"
  echo "Commands:"
  echo "  setup     - Initial setup for secure credentials"
  echo "  update    - Update an existing credential"
  echo "  decrypt   - Decrypt and generate config file"
  echo "  rotate    - Rotate encryption key"
  echo "  list      - List available credential variables (without values)"
}

# Check if OpenSSL is installed
check_openssl() {
  if ! command -v openssl &> /dev/null; then
    echo "Error: OpenSSL is not installed. Please install it to use secure credentials."
    exit 1
  fi
}

# Generate a random key for encryption
generate_key() {
  openssl rand -base64 32 > "$KEY_FILE"
  chmod 600 "$KEY_FILE"
  echo "Encryption key generated at $KEY_FILE"
}

# Encrypt credentials
encrypt_credentials() {
  local temp_file="$SECURE_ENV_DIR/temp_creds.env"
  
  # Save credentials to temporary file
  cat > "$temp_file"
  
  # Encrypt the file
  openssl enc -aes-256-cbc -salt -pbkdf2 -in "$temp_file" -out "$CREDENTIALS_FILE" -pass file:"$KEY_FILE"
  
  # Remove temporary file
  rm "$temp_file"
  
  chmod 600 "$CREDENTIALS_FILE"
  echo "Credentials encrypted successfully"
}

# Decrypt credentials
decrypt_credentials() {
  if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "Error: Credentials file not found"
    return 1
  fi
  
  openssl enc -d -aes-256-cbc -pbkdf2 -in "$CREDENTIALS_FILE" -pass file:"$KEY_FILE"
}

# Setup initial secure credentials
setup_credentials() {
  if [ -f "$CREDENTIALS_FILE" ]; then
    echo "Credentials file already exists. Use 'update' to modify credentials."
    return 1
  fi
  
  # Generate encryption key if it doesn't exist
  if [ ! -f "$KEY_FILE" ]; then
    generate_key
  fi
  
  echo "Enter secure credentials (format: VARIABLE=value, one per line)"
  echo "Enter 'END' on a line by itself when finished:"
  
  # Collect credentials
  while IFS= read -r line; do
    [ "$line" = "END" ] && break
    echo "$line"
  done | encrypt_credentials
  
  echo "Secure credentials stored successfully"
}

# Update an existing credential
update_credential() {
  if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "No credentials file found. Run 'setup' first."
    return 1
  fi
  
  read -p "Enter variable name to update: " var_name
  read -p "Enter new value: " var_value
  
  # Get existing credentials
  local temp_file="$SECURE_ENV_DIR/temp_update.env"
  decrypt_credentials > "$temp_file"
  
  # Check if variable exists
  if grep -q "^$var_name=" "$temp_file"; then
    # Update existing variable
    sed -i "s|^$var_name=.*|$var_name=$var_value|" "$temp_file"
  else
    # Add new variable
    echo "$var_name=$var_value" >> "$temp_file"
  fi
  
  # Re-encrypt the updated file
  cat "$temp_file" | encrypt_credentials
  
  # Clean up
  rm "$temp_file"
  
  echo "Credential '$var_name' updated successfully"
}

# List available credentials (names only)
list_credentials() {
  if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "No credentials file found."
    return 1
  fi
  
  echo "Available secure credentials:"
  decrypt_credentials | cut -d= -f1
}

# Generate config file from template and credentials
generate_config() {
  if [ ! -f "$CONFIG_TEMPLATE" ]; then
    echo "Error: Config template file not found at $CONFIG_TEMPLATE"
    return 1
  fi
  
  if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "Warning: No secure credentials found, using template as-is"
    cp "$CONFIG_TEMPLATE" "$CONFIG_OUTPUT"
    return 0
  fi
  
  # Create a temporary file for credential substitution
  local temp_config="$SECURE_ENV_DIR/temp_config.env"
  cp "$CONFIG_TEMPLATE" "$temp_config"
  
  # Get credentials
  local creds=$(decrypt_credentials)
  
  # Replace placeholders in the template
  while IFS= read -r line; do
    if [[ $line =~ ^([A-Za-z0-9_]+)= ]]; then
      var_name="${BASH_REMATCH[1]}"
      var_value=$(echo "$creds" | grep "^$var_name=" | cut -d= -f2-)
      
      if [ -n "$var_value" ]; then
        # Replace the variable in the config file
        sed -i "s|^$var_name=.*|$var_name=$var_value|" "$temp_config"
      fi
    fi
  done < "$temp_config"
  
  # Move the completed file to the final location
  mv "$temp_config" "$CONFIG_OUTPUT"
  chmod 640 "$CONFIG_OUTPUT"
  
  echo "Config file generated at $CONFIG_OUTPUT"
}

# Rotate encryption key
rotate_key() {
  if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "No credentials file found. Nothing to rotate."
    return 1
  fi
  
  # Decrypt with current key
  local temp_creds="$SECURE_ENV_DIR/temp_rotate.env"
  decrypt_credentials > "$temp_creds"
  
  # Create backup of old key
  cp "$KEY_FILE" "${KEY_FILE}.bak"
  
  # Generate new key
  generate_key
  
  # Re-encrypt with new key
  cat "$temp_creds" | encrypt_credentials
  
  # Clean up
  rm "$temp_creds"
  
  echo "Encryption key rotated successfully."
  echo "Backup of old key saved as ${KEY_FILE}.bak"
}

# Main execution
check_openssl

case "$1" in
  setup)
    setup_credentials
    ;;
  update)
    update_credential
    ;;
  decrypt)
    generate_config
    ;;
  rotate)
    rotate_key
    ;;
  list)
    list_credentials
    ;;
  *)
    usage
    ;;
esac

exit 0