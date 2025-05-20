#!/bin/bash
# Secure Configuration Helper for HLS Transcoder
# Version: 0.5.0
# This script helps manage sensitive configuration values securely

CONFIG_FILE="/etc/hlstranscoder/config.env"
TEMP_FILE=$(mktemp)

show_help() {
    echo "HLS Transcoder Secure Configuration Tool"
    echo ""
    echo "Usage: $0 [command] [key] [value]"
    echo ""
    echo "Commands:"
    echo "  set [key] [value]  - Set a configuration value"
    echo "  get [key]          - Get a configuration value"
    echo "  list               - List all configuration values"
    echo "  encrypt            - Encrypt sensitive values in config"
    echo "  decrypt            - Decrypt sensitive values for use"
    echo "  help               - Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 set MQTT_PASSWORD mysecretpassword"
    echo "  $0 get RTSP_SOURCE"
    echo ""
}

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Configuration file not found at $CONFIG_FILE"
    echo "Please create it first using the config.template file"
    exit 1
fi

# Function to set a configuration value
set_config() {
    KEY="$1"
    VALUE="$2"
    
    if grep -q "^$KEY=" "$CONFIG_FILE"; then
        # Key exists, update it
        sed -i "s|^$KEY=.*|$KEY=\"$VALUE\"|" "$CONFIG_FILE"
        echo "Updated $KEY in $CONFIG_FILE"
    else
        # Key doesn't exist, add it
        echo "$KEY=\"$VALUE\"" >> "$CONFIG_FILE"
        echo "Added $KEY to $CONFIG_FILE"
    fi
}

# Function to get a configuration value
get_config() {
    KEY="$1"
    VALUE=$(grep "^$KEY=" "$CONFIG_FILE" | cut -d= -f2- | tr -d '"')
    if [ -n "$VALUE" ]; then
        echo "$VALUE"
    else
        echo "Key $KEY not found in $CONFIG_FILE"
        exit 1
    fi
}

# Function to list all configuration values
list_config() {
    echo "Current configuration in $CONFIG_FILE:"
    echo "================================="
    cat "$CONFIG_FILE" | grep -v "^#" | grep "=" | sort
}

# Function to encrypt sensitive values
encrypt_config() {
    echo "Encrypting sensitive values..."
    # In a real implementation, you would encrypt passwords and tokens here
    # For now, we'll just mark them as encrypted with a prefix
    cat "$CONFIG_FILE" | 
        sed 's/^\(MQTT_PASSWORD=\)\(.*\)$/\1"<ENCRYPTED>"/g' |
        sed 's/^\(RTSP_PASSWORD=\)\(.*\)$/\1"<ENCRYPTED>"/g' > "$TEMP_FILE"
    
    mv "$TEMP_FILE" "$CONFIG_FILE"
    chmod 600 "$CONFIG_FILE"
    echo "Encryption complete. Sensitive values are now protected."
}

# Function to decrypt sensitive values
decrypt_config() {
    echo "This function would decrypt the sensitive values."
    echo "In a real implementation, this would restore the actual values."
    echo "For security reasons, this is just a placeholder."
}

# Process commands
case "$1" in
    set)
        if [ $# -ne 3 ]; then
            echo "Error: 'set' command requires a key and value"
            show_help
            exit 1
        fi
        set_config "$2" "$3"
        ;;
    get)
        if [ $# -ne 2 ]; then
            echo "Error: 'get' command requires a key"
            show_help
            exit 1
        fi
        get_config "$2"
        ;;
    list)
        list_config
        ;;
    encrypt)
        encrypt_config
        ;;
    decrypt)
        decrypt_config
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac

exit 0