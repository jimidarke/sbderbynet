#!/bin/bash
# Debug Runner for Derby Server Components
# Usage: ./debug-run.sh <script.py> [args...]
# This enables console debug logging and disables rsyslog to avoid conflicts

if [ $# -lt 1 ]; then
    echo "Usage: $0 <script.py> [args...]"
    echo ""
    echo "Examples:"
    echo "  $0 derbyRace.py"
    echo "  $0 derbyTime.py"
    echo "  $0 lcdscreen/derbyLCD.py"
    echo ""
    echo "This script enables debug console logging and disables rsyslog"
    echo "Environment variables set:"
    echo "  DERBY_CONSOLE_LOG=true  (enables console output)"
    echo "  DERBY_DEBUG=true        (enables debug level logging)"
    exit 1
fi

SCRIPT="$1"
shift  # Remove first argument, keep the rest

if [ ! -f "$SCRIPT" ]; then
    echo "Error: Script '$SCRIPT' not found"
    exit 1
fi

echo "========================================"
echo "Derby Debug Runner"
echo "========================================"
echo "Script: $SCRIPT"
echo "Args: $*"
echo "Console logging: ENABLED"
echo "Debug level: ENABLED"
echo "Rsyslog: DISABLED (to avoid conflicts)"
echo "========================================"
echo ""

# Set environment variables for debug logging
export DERBY_CONSOLE_LOG=true
export DERBY_DEBUG=true

# Run the script with debug logging enabled
python3 "$SCRIPT" "$@"