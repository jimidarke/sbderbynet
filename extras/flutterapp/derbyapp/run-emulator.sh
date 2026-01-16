#!/bin/bash
# Quick script to launch Android emulator for SBDerbyNet app development

export JAVA_HOME="/home/jimi/Documents/android-studio/jbr"
export ANDROID_HOME="$HOME/Android/Sdk"
export PATH="$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$PATH"

echo "Starting Android emulator..."
echo "Emulator: Medium_Phone_API_36.1"
echo ""

# Launch emulator in background
$ANDROID_HOME/emulator/emulator -avd Medium_Phone_API_36.1 &

echo "Emulator starting..."
echo "Wait ~30 seconds for it to fully boot"
echo ""
echo "To run the Flutter app once emulator is ready:"
echo "  /home/jimi/flutter/bin/flutter run"
