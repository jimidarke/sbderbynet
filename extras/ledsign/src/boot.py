"""
DerbyNet LED Sign Controller - Boot Configuration

This file runs on ESP32 startup before main.py.
Handles basic initialization and garbage collection.

Version: 1.0.0
"""

import gc
import esp

# Disable vendor OS debug output
esp.osdebug(None)

# Run garbage collection to free up memory
gc.collect()

# Print boot message
print()
print("=" * 40)
print("DerbyNet LED Sign Controller")
print("Booting...")
print("=" * 40)
print()
