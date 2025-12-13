#!/bin/bash
# DerbyNet Camera Manager
# Version: 0.8.0
# 
# This script provides tools for managing multi-camera setup including:
# - Camera discovery and testing
# - Configuration validation
# - Stream health monitoring
# - Quality profile management

VERSION="0.8.0"

# Default paths
CONFIG_FILE="/opt/hlsfeed/multicam-config.env"
LOG_DIR="/var/log/hlsfeed"
SERVICE_NAME="multicam-service"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
DerbyNet Camera Manager v${VERSION}

Usage: $0 [COMMAND] [OPTIONS]

COMMANDS:
    discover         Discover available cameras (RTSP and USB)
    test <camera_id> Test a specific camera stream
    validate         Validate camera configuration
    status           Show service and camera status
    quality <level>  Change video quality profile (HIGH/MEDIUM/LOW)
    restart          Restart the camera service
    logs [camera_id] Show logs (all or specific camera)
    setup            Interactive setup wizard
    benchmark        Test system performance with different profiles

OPTIONS:
    --config FILE    Use alternate configuration file
    --verbose        Enable verbose output
    --help           Show this help message

EXAMPLES:
    $0 discover                    # Find all available cameras
    $0 test finish                 # Test the finish line camera
    $0 quality MEDIUM             # Switch to medium quality profile
    $0 status                     # Show current service status
    $0 setup                      # Run interactive setup

EOF
}

# Load configuration
load_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    # Source the config file
    source "$CONFIG_FILE"
    log "Loaded configuration from $CONFIG_FILE"
}

# Discover RTSP cameras on network
discover_rtsp_cameras() {
    log "Discovering RTSP cameras on network..."
    
    # Common RTSP ports
    RTSP_PORTS=(554 8554)
    NETWORK_BASE="192.168.100"
    
    echo "Scanning network ${NETWORK_BASE}.0/24 for RTSP cameras..."
    
    for port in "${RTSP_PORTS[@]}"; do
        echo "Checking port $port..."
        
        # Use nmap to scan for open RTSP ports
        if command -v nmap >/dev/null; then
            nmap -p "$port" --open "${NETWORK_BASE}.1-254" 2>/dev/null | \
            grep -B1 "open" | grep "Nmap scan report" | \
            while read -r line; do
                ip=$(echo "$line" | awk '{print $5}')
                echo "  Found potential RTSP camera at: $ip:$port"
                
                # Try to get camera info
                timeout 5 ffprobe -v quiet -print_format json -show_streams \
                    "rtsp://$ip:$port/" 2>/dev/null && \
                    echo "    ✓ RTSP stream confirmed" || \
                    echo "    ✗ No valid RTSP stream"
            done
        else
            warning "nmap not installed. Install with: sudo apt install nmap"
        fi
    done
}

# Discover USB cameras
discover_usb_cameras() {
    log "Discovering USB cameras..."
    
    # Find video devices
    for device in /dev/video*; do
        if [[ -e "$device" ]]; then
            echo "Found video device: $device"
            
            # Get device info
            if command -v v4l2-ctl >/dev/null; then
                device_info=$(v4l2-ctl --device="$device" --info 2>/dev/null)
                if [[ $? -eq 0 ]]; then
                    echo "  Device info:"
                    echo "$device_info" | grep -E "(Card type|Driver name)" | sed 's/^/    /'
                    
                    # List supported formats
                    echo "  Supported formats:"
                    v4l2-ctl --device="$device" --list-formats-ext 2>/dev/null | \
                        grep -E "(Index|Size|Interval)" | head -10 | sed 's/^/    /'
                else
                    echo "  ✗ Unable to query device"
                fi
            else
                echo "  Install v4l-utils for detailed info: sudo apt install v4l-utils"
            fi
            
            # Test if FFmpeg can read from device
            echo "  Testing FFmpeg compatibility..."
            timeout 3 ffprobe -v quiet -f v4l2 "$device" 2>/dev/null && \
                echo "    ✓ FFmpeg compatible" || \
                echo "    ✗ FFmpeg cannot read device"
        fi
    done
}

# Test a specific camera
test_camera() {
    local camera_id="$1"
    
    if [[ -z "$camera_id" ]]; then
        error "Camera ID required for testing"
        exit 1
    fi
    
    load_config
    
    # Get camera configuration
    local enabled_var="CAMERA_${camera_id^^}_ENABLED"
    local type_var="CAMERA_${camera_id^^}_TYPE"
    local source_var="CAMERA_${camera_id^^}_SOURCE"
    local name_var="CAMERA_${camera_id^^}_NAME"
    
    local enabled="${!enabled_var}"
    local type="${!type_var}"
    local source="${!source_var}"
    local name="${!name_var}"
    
    if [[ "$enabled" != "true" ]]; then
        error "Camera '$camera_id' is not enabled in configuration"
        exit 1
    fi
    
    log "Testing camera: $name ($camera_id)"
    log "Type: $type"
    log "Source: $source"
    
    # Build test command
    local cmd="ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,codec_name -of csv=p=0"
    
    if [[ "$type" == "RTSP" ]]; then
        cmd="$cmd -rtsp_transport tcp -timeout 10"
    elif [[ "$type" == "USB" ]]; then
        cmd="$cmd -f v4l2"
    fi
    
    cmd="$cmd \"$source\""
    
    echo "Running test command..."
    echo "Command: $cmd"
    
    # Execute test
    eval "$cmd"
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        success "Camera test passed!"
        
        # Test actual streaming for 10 seconds
        echo "Testing 10-second stream..."
        local test_output="/tmp/camera_test_${camera_id}.mp4"
        
        local stream_cmd="ffmpeg -y -v warning"
        if [[ "$type" == "RTSP" ]]; then
            stream_cmd="$stream_cmd -rtsp_transport tcp -timeout 10"
        elif [[ "$type" == "USB" ]]; then
            stream_cmd="$stream_cmd -f v4l2"
        fi
        
        stream_cmd="$stream_cmd -i \"$source\" -t 10 -c:v libx264 -preset veryfast \"$test_output\""
        
        eval "$stream_cmd"
        if [[ $? -eq 0 ]]; then
            success "10-second stream test passed!"
            echo "Test video saved to: $test_output"
            
            # Show video info
            echo "Video details:"
            ffprobe -v quiet -print_format json -show_streams "$test_output" | \
                jq -r '.streams[0] | "Resolution: \(.width)x\(.height), FPS: \(.r_frame_rate), Codec: \(.codec_name)"'
        else
            error "Stream test failed"
        fi
    else
        error "Camera test failed with exit code: $exit_code"
    fi
}

# Validate configuration
validate_config() {
    log "Validating camera configuration..."
    
    load_config
    
    local issues=0
    local enabled_cameras=0
    
    # Check required directories
    local required_dirs=("$HLS_OUTPUT_DIR" "$REPLAY_VIDEO_DIR" "$LOG_DIR")
    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            error "Required directory does not exist: $dir"
            ((issues++))
        fi
    done
    
    # Check cameras
    for camera_var in $(env | grep "CAMERA_.*_ENABLED=true" | cut -d= -f1); do
        local camera_prefix="${camera_var%_ENABLED}"
        local camera_id="${camera_prefix#CAMERA_}"
        
        echo "Validating camera: $camera_id"
        
        # Check required variables
        local type_var="${camera_prefix}_TYPE"
        local source_var="${camera_prefix}_SOURCE"
        local name_var="${camera_prefix}_NAME"
        
        if [[ -z "${!type_var}" ]]; then
            error "  Missing TYPE for camera $camera_id"
            ((issues++))
        fi
        
        if [[ -z "${!source_var}" ]]; then
            error "  Missing SOURCE for camera $camera_id"
            ((issues++))
        fi
        
        if [[ -z "${!name_var}" ]]; then
            warning "  Missing NAME for camera $camera_id (will use default)"
        fi
        
        # Validate source format
        local source="${!source_var}"
        local type="${!type_var}"
        
        if [[ "$type" == "RTSP" ]]; then
            if [[ ! "$source" =~ ^rtsp:// ]]; then
                error "  Invalid RTSP URL format for camera $camera_id: $source"
                ((issues++))
            fi
        elif [[ "$type" == "USB" ]]; then
            if [[ ! "$source" =~ ^/dev/video ]]; then
                error "  Invalid USB device path for camera $camera_id: $source"
                ((issues++))
            elif [[ ! -e "$source" ]]; then
                error "  USB device does not exist for camera $camera_id: $source"
                ((issues++))
            fi
        else
            error "  Invalid camera type for camera $camera_id: $type (must be RTSP or USB)"
            ((issues++))
        fi
        
        ((enabled_cameras++))
    done
    
    if [[ $enabled_cameras -eq 0 ]]; then
        error "No cameras are enabled in configuration"
        ((issues++))
    fi
    
    # Check quality profile settings
    local profile="$VIDEO_QUALITY_PROFILE"
    local resolution_var="${profile}_RESOLUTION"
    if [[ -z "${!resolution_var}" ]]; then
        error "Invalid quality profile or missing resolution: $profile"
        ((issues++))
    fi
    
    # Summary
    if [[ $issues -eq 0 ]]; then
        success "Configuration validation passed!"
        echo "Found $enabled_cameras enabled camera(s)"
    else
        error "Configuration validation failed with $issues issue(s)"
        exit 1
    fi
}

# Show service status
show_status() {
    log "Checking service status..."
    
    # Service status
    if systemctl is-active "$SERVICE_NAME" >/dev/null; then
        success "Service is running"
    else
        error "Service is not running"
    fi
    
    # Process information
    local pids=$(pgrep -f "multicam-service.py")
    if [[ -n "$pids" ]]; then
        echo "Process IDs: $pids"
        
        for pid in $pids; do
            local cpu_mem=$(ps -p "$pid" -o %cpu,%mem --no-headers)
            echo "  PID $pid: CPU: $(echo $cpu_mem | awk '{print $1}')%, Memory: $(echo $cpu_mem | awk '{print $2}')%"
        done
    fi
    
    # Check camera streams
    load_config
    echo ""
    echo "Camera Status:"
    
    for camera_var in $(env | grep "CAMERA_.*_ENABLED=true" | cut -d= -f1); do
        local camera_prefix="${camera_var%_ENABLED}"
        local camera_id="${camera_prefix#CAMERA_}"
        local name_var="${camera_prefix}_NAME"
        local name="${!name_var:-Camera $camera_id}"
        
        echo "  $name ($camera_id):"
        
        # Check HLS output
        local output_dir="${HLS_OUTPUT_DIR}/camera_${camera_id,,}"
        local playlist="$output_dir/stream.m3u8"
        
        if [[ -f "$playlist" ]]; then
            local age=$(($(date +%s) - $(stat -c %Y "$playlist")))
            if [[ $age -lt 60 ]]; then
                success "    ✓ Stream active (updated ${age}s ago)"
            else
                warning "    ⚠ Stream stale (updated ${age}s ago)"
            fi
            
            # Check segment count
            local segment_count=$(ls "$output_dir"/*.ts 2>/dev/null | wc -l)
            echo "    Segments: $segment_count"
        else
            error "    ✗ No stream found"
        fi
    done
    
    # System resources
    echo ""
    echo "System Resources:"
    echo "  CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
    echo "  Memory: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
    echo "  Disk: $(df -h "${HLS_OUTPUT_DIR}" | awk 'NR==2 {print $5}')"
}

# Change quality profile
change_quality() {
    local new_profile="$1"
    
    if [[ -z "$new_profile" ]]; then
        error "Quality level required (HIGH_QUALITY/MEDIUM_QUALITY/LOW_QUALITY)"
        exit 1
    fi
    
    # Validate profile
    case "$new_profile" in
        HIGH|HIGH_QUALITY)
            new_profile="HIGH_QUALITY"
            ;;
        MEDIUM|MEDIUM_QUALITY)
            new_profile="MEDIUM_QUALITY"
            ;;
        LOW|LOW_QUALITY)
            new_profile="LOW_QUALITY"
            ;;
        *)
            error "Invalid quality profile: $new_profile"
            echo "Valid options: HIGH_QUALITY, MEDIUM_QUALITY, LOW_QUALITY"
            exit 1
            ;;
    esac
    
    log "Changing quality profile to: $new_profile"
    
    # Update configuration file
    if [[ -f "$CONFIG_FILE" ]]; then
        sed -i "s/^VIDEO_QUALITY_PROFILE=.*/VIDEO_QUALITY_PROFILE=\"$new_profile\"/" "$CONFIG_FILE"
        success "Configuration updated"
        
        # Restart service to apply changes
        log "Restarting service to apply new quality profile..."
        sudo systemctl restart "$SERVICE_NAME"
        
        if [[ $? -eq 0 ]]; then
            success "Service restarted successfully"
        else
            error "Failed to restart service"
        fi
    else
        error "Configuration file not found: $CONFIG_FILE"
    fi
}

# Show logs
show_logs() {
    local camera_id="$1"
    
    if [[ -n "$camera_id" ]]; then
        log "Showing logs for camera: $camera_id"
        # Filter logs for specific camera
        journalctl -u "$SERVICE_NAME" -f | grep -i "$camera_id"
    else
        log "Showing service logs (press Ctrl+C to exit)"
        journalctl -u "$SERVICE_NAME" -f
    fi
}

# Interactive setup wizard
setup_wizard() {
    echo "DerbyNet Multi-Camera Setup Wizard"
    echo "=================================="
    echo ""
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        error "Please run setup as non-root user with sudo access"
        exit 1
    fi
    
    # Install dependencies
    echo "Checking dependencies..."
    local missing_deps=()
    
    for cmd in ffmpeg ffprobe v4l2-ctl nmap; do
        if ! command -v "$cmd" >/dev/null; then
            missing_deps+=("$cmd")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        echo "Missing dependencies: ${missing_deps[*]}"
        read -p "Install missing dependencies? (y/n): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo apt update
            sudo apt install -y ffmpeg v4l-utils nmap python3-pip python3-psutil python3-paho-mqtt
        fi
    fi
    
    # Create directories
    echo "Creating directories..."
    sudo mkdir -p /opt/hlsfeed /var/log/hlsfeed
    sudo chown -R "$USER:$USER" /opt/hlsfeed /var/log/hlsfeed
    
    # Copy configuration template
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo "Creating configuration file..."
        cp "$(dirname "$0")/multicam-config.template" "$CONFIG_FILE"
        echo "Configuration template created at: $CONFIG_FILE"
        echo "Please edit this file to configure your cameras"
    fi
    
    # Install service
    echo "Installing systemd service..."
    sudo cp "$(dirname "$0")/multicam-service.service" /etc/systemd/system/
    sudo cp "$(dirname "$0")/multicam-service.py" /opt/hlsfeed/
    sudo chmod +x /opt/hlsfeed/multicam-service.py
    
    # Create service user
    if ! id "hlsfeed" >/dev/null 2>&1; then
        sudo useradd -r -s /bin/false -d /opt/hlsfeed hlsfeed
        sudo chown -R hlsfeed:hlsfeed /opt/hlsfeed /var/log/hlsfeed
    fi
    
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    
    success "Setup completed!"
    echo ""
    echo "Next steps:"
    echo "1. Edit configuration: sudo nano $CONFIG_FILE"
    echo "2. Discover cameras: $0 discover"
    echo "3. Test cameras: $0 test <camera_id>"
    echo "4. Start service: sudo systemctl start $SERVICE_NAME"
}

# Benchmark system performance
benchmark_system() {
    log "Running system performance benchmark..."
    
    load_config
    
    # Test different quality profiles
    local profiles=("LOW_QUALITY" "MEDIUM_QUALITY" "HIGH_QUALITY")
    local test_duration=30
    
    echo "Testing different quality profiles for $test_duration seconds each..."
    
    for profile in "${profiles[@]}"; do
        echo ""
        log "Testing profile: $profile"
        
        # Temporarily change profile
        sed -i "s/^VIDEO_QUALITY_PROFILE=.*/VIDEO_QUALITY_PROFILE=\"$profile\"/" "$CONFIG_FILE"
        
        # Start test streams
        local pids=()
        for camera_var in $(env | grep "CAMERA_.*_ENABLED=true" | cut -d= -f1 | head -2); do
            local camera_prefix="${camera_var%_ENABLED}"
            local camera_id="${camera_prefix#CAMERA_}"
            local source_var="${camera_prefix}_SOURCE"
            local type_var="${camera_prefix}_TYPE"
            local source="${!source_var}"
            local type="${!type_var}"
            
            echo "  Starting test stream for camera $camera_id..."
            
            local cmd="ffmpeg -y -v error"
            if [[ "$type" == "RTSP" ]]; then
                cmd="$cmd -rtsp_transport tcp"
            elif [[ "$type" == "USB" ]]; then
                cmd="$cmd -f v4l2"
            fi
            
            # Get quality settings
            local resolution="${profile}_RESOLUTION"
            local bitrate="${profile}_BITRATE"
            local preset="${profile}_PRESET"
            
            cmd="$cmd -i \"$source\" -t $test_duration"
            cmd="$cmd -c:v libx264 -preset ${!preset} -b:v ${!bitrate}"
            cmd="$cmd -s ${!resolution} -f null -"
            
            eval "$cmd" &
            pids+=($!)
        done
        
        # Monitor system resources
        echo "  Monitoring system resources..."
        local start_time=$(date +%s)
        local max_cpu=0
        local max_mem=0
        
        while [[ $(($(date +%s) - start_time)) -lt $test_duration ]]; do
            local cpu=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 | cut -d',' -f1)
            local mem=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
            
            if (( $(echo "$cpu > $max_cpu" | bc -l) )); then
                max_cpu=$cpu
            fi
            
            if (( $(echo "$mem > $max_mem" | bc -l) )); then
                max_mem=$mem
            fi
            
            sleep 2
        done
        
        # Wait for processes to finish
        for pid in "${pids[@]}"; do
            wait "$pid" 2>/dev/null
        done
        
        echo "  Results:"
        echo "    Max CPU: ${max_cpu}%"
        echo "    Max Memory: ${max_mem}%"
        echo "    Profile: $profile (${!resolution}, ${!bitrate})"
    done
    
    echo ""
    log "Benchmark completed"
    echo "Choose the highest quality profile your system can handle with <80% CPU usage"
}

# Main script logic
case "${1:-}" in
    discover)
        discover_rtsp_cameras
        echo ""
        discover_usb_cameras
        ;;
    test)
        test_camera "$2"
        ;;
    validate)
        validate_config
        ;;
    status)
        show_status
        ;;
    quality)
        change_quality "$2"
        ;;
    restart)
        log "Restarting camera service..."
        sudo systemctl restart "$SERVICE_NAME"
        ;;
    logs)
        show_logs "$2"
        ;;
    setup)
        setup_wizard
        ;;
    benchmark)
        benchmark_system
        ;;
    --help|help|"")
        show_help
        ;;
    *)
        error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac