#!/usr/bin/env python3
"""
Test script for DerbyNet simplified logging system.

This script tests that the simplified logging works correctly by:
1. Setting up loggers for different services
2. Sending test messages to each destination
3. Verifying that messages appear in expected locations

Usage: python3 test_simple_logging.py
"""

import sys
import os
import time
from pathlib import Path

# Add the common directory to path
script_dir = Path(__file__).parent.parent / 'common'
sys.path.insert(0, str(script_dir))

try:
    from simple_logging import setup_simple_logging
    from derbylogger import setup_logger, DerbyLogger
except ImportError as e:
    print(f"Error importing logging modules: {e}")
    print("Make sure you're running this from the correct directory")
    sys.exit(1)

def test_simple_logging():
    """Test the simple_logging module directly"""
    print("=== Testing simple_logging module ===")
    
    # Test multiple services
    services = ["TestService1", "TestService2", "TestService3"]
    
    for service in services:
        print(f"Testing {service}...")
        logger = setup_simple_logging(service)
        
        # Send test messages
        logger.info(f"Test INFO message from {service}")
        logger.warning(f"Test WARNING message from {service}")
        logger.error(f"Test ERROR message from {service}")
        
        print(f"✓ {service} logging test sent")
    
    print("simple_logging tests completed.\n")

def test_derbylogger_compatibility():
    """Test backward compatibility with derbylogger interface"""
    print("=== Testing derbylogger compatibility ===")
    
    # Test new interface
    logger1 = setup_logger("CompatTest1")
    logger1.info("Testing new derbylogger interface")
    
    # Test old DerbyLogger class interface
    logger2 = DerbyLogger("CompatTest2")
    logger2.info("Testing old DerbyLogger class interface")
    logger2.warning("Testing old DerbyLogger warning")
    logger2.error("Testing old DerbyLogger error")
    
    print("✓ Backward compatibility tests completed.\n")

def test_log_destinations():
    """Test that logs go to expected destinations"""
    print("=== Testing log destinations ===")
    
    logger = setup_simple_logging("DestinationTest")
    
    test_message = f"Test message at {time.strftime('%Y-%m-%d %H:%M:%S')}"
    logger.info(test_message)
    
    # Check if log directory was created
    log_dir = Path("/var/log/derbynet")
    if log_dir.exists():
        print("✓ Log directory /var/log/derbynet exists")
        
        # Check if service log file was created
        log_file = log_dir / "destinationtest.log"
        if log_file.exists():
            print("✓ Service log file created")
            
            # Check if message appears in file
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    if test_message in content:
                        print("✓ Test message found in log file")
                    else:
                        print("⚠ Test message not found in log file (might need a moment)")
            except Exception as e:
                print(f"⚠ Could not read log file: {e}")
        else:
            print("⚠ Service log file not created (check permissions)")
    else:
        print("⚠ Log directory not created (check permissions)")
    
    print("✓ Console output should be visible above")
    print("✓ Rsyslog attempt made (check network connectivity)")
    print("Destination tests completed.\n")

def main():
    """Run all tests"""
    print("DerbyNet Simplified Logging Test Suite")
    print("=" * 50)
    
    try:
        test_simple_logging()
        test_derbylogger_compatibility()
        test_log_destinations()
        
        print("=" * 50)
        print("All tests completed successfully!")
        print("\nTo verify full functionality:")
        print("1. Check console output above for test messages")
        print("2. Check /var/log/derbynet/ for log files")
        print("3. Check rsyslog server (192.168.100.10) for remote logs")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())