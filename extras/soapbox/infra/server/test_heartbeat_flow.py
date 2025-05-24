#!/usr/bin/env python3
"""
Test script to validate the heartbeat and timer status communication flow
from MQTT through derbyRace to DerbyNet API and database.

Usage: python3 test_heartbeat_flow.py
"""

import json
import time
import requests
import sys
import os

# Add the current directory to path for importing modules
sys.path.append(os.path.dirname(__file__))

from derbyapi import DerbyNetClient
from derbylogger import setup_logger

logger = setup_logger("test_heartbeat")

def test_derbynet_api_connection():
    """Test basic connectivity to DerbyNet API"""
    logger.info("Testing DerbyNet API connection...")
    
    try:
        api = DerbyNetClient("localhost")
        auth_result = api.login()
        
        if auth_result:
            logger.info("✓ DerbyNet API login successful")
            return api
        else:
            logger.error("✗ DerbyNet API login failed")
            return None
    except Exception as e:
        logger.error(f"✗ DerbyNet API connection error: {e}")
        return None

def test_timer_heartbeat(api):
    """Test timer heartbeat functionality"""
    logger.info("Testing timer heartbeat...")
    
    # Mock timer heartbeat data similar to what derbyRace.py would send
    test_heartbeats = {
        1: {'time': time.time(), 'isReady': True},
        2: {'time': time.time(), 'isReady': False}, 
        3: {'time': time.time(), 'isReady': True}
    }
    
    try:
        success = api.send_timer_heartbeat(test_heartbeats)
        if success:
            logger.info("✓ Timer heartbeat sent successfully")
            return True
        else:
            logger.error("✗ Timer heartbeat failed")
            return False
    except Exception as e:
        logger.error(f"✗ Timer heartbeat error: {e}")
        return False

def test_device_telemetry(api):
    """Test device status telemetry"""
    logger.info("Testing device telemetry...")
    
    # Mock telemetry data similar to what finish timers would send
    test_telemetry = {
        "hostname": "test-timer",
        "hwid": "TEST12345678",
        "version": "0.5.0",
        "uptime": 3600,
        "ip": "192.168.100.101",
        "mac": "00:1A:2B:3C:4D:5E",
        "wifi_rssi": -45,
        "battery_level": 95,
        "cpu_temp": 40.5,
        "memory_usage": 25.0,
        "disk": 75.0,
        "cpu_usage": 12.3
    }
    
    try:
        success = api.send_device_status(test_telemetry)
        if success:
            logger.info("✓ Device telemetry sent successfully")
            return True
        else:
            logger.error("✗ Device telemetry failed")
            return False
    except Exception as e:
        logger.error(f"✗ Device telemetry error: {e}")
        return False

def test_race_status_query(api):
    """Test race status query"""
    logger.info("Testing race status query...")
    
    try:
        race_status = api.get_race_status()
        if race_status:
            logger.info("✓ Race status query successful")
            logger.info(f"  Active: {race_status.get('active', 'N/A')}")
            logger.info(f"  Round ID: {race_status.get('roundid', 'N/A')}")
            logger.info(f"  Heat: {race_status.get('heat', 'N/A')}")
            logger.info(f"  Lane Count: {race_status.get('lane-count', 'N/A')}")
            return True
        else:
            logger.error("✗ Race status query failed")
            return False
    except Exception as e:
        logger.error(f"✗ Race status query error: {e}")
        return False

def test_database_timer_status():
    """Test if timer status data appears in database"""
    logger.info("Testing database timer status...")
    
    try:
        # Direct HTTP request to the device status API
        response = requests.get("http://localhost/derbynet/device-status-api.php", 
                              cookies={'PHPSESSID': 'test'}, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            devices = data.get('devices', [])
            logger.info(f"✓ Found {len(devices)} devices in database")
            
            for device in devices[:3]:  # Show first 3 devices
                logger.info(f"  Device: {device.get('device_name', 'N/A')} "
                          f"({device.get('serial', 'N/A')}) - "
                          f"Last updated: {device.get('last_updated', 'N/A')}")
            return True
        else:
            logger.error(f"✗ Database query failed with status {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"✗ Database query error: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting heartbeat communication flow test...")
    
    results = {
        'api_connection': False,
        'timer_heartbeat': False,
        'device_telemetry': False,
        'race_status': False,
        'database_status': False
    }
    
    # Test 1: API Connection
    api = test_derbynet_api_connection()
    if api:
        results['api_connection'] = True
        
        # Test 2: Timer Heartbeat
        results['timer_heartbeat'] = test_timer_heartbeat(api)
        
        # Test 3: Device Telemetry  
        results['device_telemetry'] = test_device_telemetry(api)
        
        # Test 4: Race Status Query
        results['race_status'] = test_race_status_query(api)
    
    # Test 5: Database Status (independent of API)
    results['database_status'] = test_database_timer_status()
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("TEST SUMMARY")
    logger.info("="*50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{test_name.replace('_', ' ').title()}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Heartbeat communication flow is working.")
        return 0
    else:
        logger.warning("⚠️  Some tests failed. Check the logs above for details.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)