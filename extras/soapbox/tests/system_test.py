#!/usr/bin/env python3
"""
DerbyNet System Test

This script performs a comprehensive test of all DerbyNet components:
- MQTT Broker connectivity
- Finish Timer functionality
- Start Timer functionality
- Race Server states
- Display functionality
- HLS Stream health

Usage:
    python3 system_test.py [--broker 192.168.100.10] [--verbose]
"""

import os
import sys
import time
import json
import socket
import logging
import argparse
import threading
import requests
from datetime import datetime
import paho.mqtt.client as mqtt

# Add parent directory to path for imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

try:
    from infra.common.derbylogger import setup_logger, get_logger
except ImportError:
    # Fall back to standard logging if common library not available
    def setup_logger(name, **kwargs):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s'
        )
    
    def get_logger(name):
        return logging.getLogger(name)

# Set up command line arguments
parser = argparse.ArgumentParser(description='DerbyNet System Test')
parser.add_argument('--broker', default='192.168.100.10', help='MQTT broker address')
parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
parser.add_argument('--test', choices=['all', 'mqtt', 'timers', 'race', 'display', 'stream'], 
                    default='all', help='Specific test to run')
args = parser.parse_args()

# Setup logging
log_level = 'DEBUG' if args.verbose else 'INFO'
setup_logger('system_test', console=True, log_level=log_level)
logger = get_logger(__name__)

# Global test results
test_results = {
    'mqtt': {'status': 'Not Run', 'details': {}},
    'timers': {'status': 'Not Run', 'details': {}},
    'race': {'status': 'Not Run', 'details': {}},
    'display': {'status': 'Not Run', 'details': {}},
    'stream': {'status': 'Not Run', 'details': {}}
}

# Test events
mqtt_connected_event = threading.Event()
race_state_received_event = threading.Event()
timer_data_received_event = threading.Event()
display_data_received_event = threading.Event()

# Global data
mqtt_client = None
received_messages = {}
device_status = {}
race_state = None

def on_connect(client, userdata, flags, rc):
    """Callback for MQTT connection"""
    if rc == 0:
        logger.info(f"Connected to MQTT broker at {args.broker}")
        mqtt_connected_event.set()
        
        # Subscribe to relevant topics
        topics = [
            ("derbynet/race/state", 0),
            ("derbynet/device/+/status", 0),
            ("derbynet/device/+/telemetry", 0),
            ("derbynet/lane/+/led", 0),
            ("derbynet/lane/+/pinny", 0)
        ]
        client.subscribe(topics)
    else:
        logger.error(f"Failed to connect to MQTT broker, return code: {rc}")

def on_message(client, userdata, msg):
    """Callback for MQTT messages"""
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode())
    except (ValueError, TypeError):
        payload = msg.payload.decode()
    
    logger.debug(f"Received message on topic {topic}: {payload}")
    
    # Store message for analysis
    if topic not in received_messages:
        received_messages[topic] = []
    received_messages[topic].append({
        'timestamp': datetime.now().isoformat(),
        'payload': payload
    })
    
    # Process specific topics
    if topic == "derbynet/race/state":
        global race_state
        race_state = payload
        race_state_received_event.set()
    
    elif topic.startswith("derbynet/device/") and topic.endswith("/status"):
        device_id = topic.split("/")[2]
        device_status[device_id] = {
            'status': payload,
            'last_updated': datetime.now().isoformat()
        }
    
    elif topic.startswith("derbynet/device/") and topic.endswith("/telemetry"):
        device_id = topic.split("/")[2]
        if device_id.startswith(('finish-timer', 'ft')):
            timer_data_received_event.set()
        elif device_id.startswith(('display', 'kiosk')):
            display_data_received_event.set()

def test_mqtt_connectivity():
    """Test MQTT broker connectivity"""
    logger.info("Testing MQTT broker connectivity...")
    
    global mqtt_client
    mqtt_client = mqtt.Client(client_id=f"system-test-{socket.gethostname()}")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    try:
        mqtt_client.connect(args.broker, 1883, 60)
        mqtt_client.loop_start()
        
        # Wait for connection
        if mqtt_connected_event.wait(timeout=10):
            test_results['mqtt']['status'] = 'Pass'
            test_results['mqtt']['details']['connected'] = True
            test_results['mqtt']['details']['broker'] = args.broker
            return True
        else:
            test_results['mqtt']['status'] = 'Fail'
            test_results['mqtt']['details']['error'] = 'Connection timeout'
            return False
    
    except Exception as e:
        logger.error(f"MQTT connection error: {e}")
        test_results['mqtt']['status'] = 'Fail'
        test_results['mqtt']['details']['error'] = str(e)
        return False

def test_race_server():
    """Test race server functionality"""
    logger.info("Testing race server functionality...")
    
    # Send test race state request
    try:
        mqtt_client.publish("derbynet/race/command", json.dumps({
            'action': 'get_state',
            'test': True
        }))
        
        # Wait for response
        if race_state_received_event.wait(timeout=10):
            test_results['race']['status'] = 'Pass'
            test_results['race']['details']['state'] = race_state
            test_results['race']['details']['response_time'] = 'Under 10s'
            return True
        else:
            test_results['race']['status'] = 'Fail'
            test_results['race']['details']['error'] = 'No response from race server'
            return False
    
    except Exception as e:
        logger.error(f"Race server test error: {e}")
        test_results['race']['status'] = 'Fail'
        test_results['race']['details']['error'] = str(e)
        return False

def test_timers():
    """Test finish timers functionality"""
    logger.info("Testing timer functionality...")
    
    # Check for any timer data
    timer_found = False
    for device_id in device_status:
        if any(device_id.startswith(prefix) for prefix in ('finish-timer', 'ft')):
            timer_found = True
            break
    
    if not timer_found:
        # If no timers found in already received data, wait for timer data
        timer_data_received_event.wait(timeout=10)
        # Recheck for timers
        for device_id in device_status:
            if any(device_id.startswith(prefix) for prefix in ('finish-timer', 'ft')):
                timer_found = True
                break
    
    if timer_found:
        # Send test message to timer(s)
        try:
            for lane in range(1, 5):
                mqtt_client.publish(f"derbynet/lane/{lane}/led", json.dumps({
                    'color': 'green',
                    'test': True
                }))
            
            time.sleep(2)  # Give time for timers to respond
            
            timer_topics = [topic for topic in received_messages if 'finish-timer' in topic or '/ft' in topic]
            
            if timer_topics:
                test_results['timers']['status'] = 'Pass'
                test_results['timers']['details']['found'] = timer_topics
                return True
            else:
                test_results['timers']['status'] = 'Fail'
                test_results['timers']['details']['error'] = 'No timer response detected'
                return False
        
        except Exception as e:
            logger.error(f"Timer test error: {e}")
            test_results['timers']['status'] = 'Fail'
            test_results['timers']['details']['error'] = str(e)
            return False
    else:
        test_results['timers']['status'] = 'Fail'
        test_results['timers']['details']['error'] = 'No timers found in the system'
        return False

def test_displays():
    """Test display functionality"""
    logger.info("Testing display functionality...")
    
    # Check for any display data
    display_found = False
    for device_id in device_status:
        if any(device_id.startswith(prefix) for prefix in ('display', 'kiosk')):
            display_found = True
            break
    
    if not display_found:
        # If no displays found in already received data, wait for display data
        display_data_received_event.wait(timeout=10)
        # Recheck for displays
        for device_id in device_status:
            if any(device_id.startswith(prefix) for prefix in ('display', 'kiosk')):
                display_found = True
                break
    
    if display_found:
        # Get display-related topics
        display_topics = [topic for topic in received_messages 
                         if 'display' in topic or 'kiosk' in topic]
        
        if display_topics:
            test_results['display']['status'] = 'Pass'
            test_results['display']['details']['found'] = display_topics
            return True
        else:
            test_results['display']['status'] = 'Fail'
            test_results['display']['details']['error'] = 'No display response detected'
            return False
    else:
        test_results['display']['status'] = 'Fail'
        test_results['display']['details']['error'] = 'No displays found in the system'
        return False

def test_hls_stream():
    """Test HLS stream functionality"""
    logger.info("Testing HLS stream functionality...")
    
    try:
        # Check if stream server is responding
        stream_url = f"http://{args.broker}:8037/health"
        response = requests.get(stream_url, timeout=5)
        
        if response.status_code == 200:
            # Check for actual stream file
            m3u8_url = f"http://{args.broker}:8037/hls/stream.m3u8"
            m3u8_response = requests.get(m3u8_url, timeout=5)
            
            if m3u8_response.status_code == 200:
                test_results['stream']['status'] = 'Pass'
                test_results['stream']['details']['url'] = m3u8_url
                test_results['stream']['details']['content_type'] = m3u8_response.headers.get('Content-Type')
                
                # Check if we can parse the m3u8 file
                content = m3u8_response.text
                if '#EXTM3U' in content:
                    # Count TS segments
                    ts_segments = [line for line in content.splitlines() if line.endswith('.ts')]
                    test_results['stream']['details']['segments'] = len(ts_segments)
                
                return True
            else:
                test_results['stream']['status'] = 'Fail'
                test_results['stream']['details']['error'] = f"M3U8 file not found, status: {m3u8_response.status_code}"
                return False
        else:
            test_results['stream']['status'] = 'Fail'
            test_results['stream']['details']['error'] = f"Stream server not responding, status: {response.status_code}"
            return False
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Stream test error: {e}")
        test_results['stream']['status'] = 'Fail'
        test_results['stream']['details']['error'] = str(e)
        return False

def run_tests():
    """Run all selected tests"""
    # Always test MQTT connectivity first
    mqtt_success = test_mqtt_connectivity()
    
    if not mqtt_success:
        logger.error("MQTT connectivity failed, skipping other tests")
        return
    
    # Run selected tests
    if args.test == 'mqtt' or args.test == 'all':
        # Already tested MQTT
        pass
    
    if args.test == 'race' or args.test == 'all':
        test_race_server()
    
    if args.test == 'timers' or args.test == 'all':
        test_timers()
    
    if args.test == 'display' or args.test == 'all':
        test_displays()
    
    if args.test == 'stream' or args.test == 'all':
        test_hls_stream()

def print_results():
    """Print test results in a user-friendly format"""
    print("\n" + "=" * 60)
    print(" " * 20 + "TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, result in test_results.items():
        status = result['status']
        status_color = "\033[92m" if status == 'Pass' else "\033[91m" if status == 'Fail' else "\033[93m"
        print(f"{test_name.upper():10} | {status_color}{status}\033[0m")
        
        # Print details for verbose mode
        if args.verbose:
            for key, value in result['details'].items():
                if isinstance(value, (dict, list)):
                    print(f"  {key}: {json.dumps(value, indent=2)}")
                else:
                    print(f"  {key}: {value}")
            print("-" * 40)
    
    print("\n" + "=" * 60)
    
    # Overall status
    all_passed = all(r['status'] == 'Pass' for r in test_results.values() if r['status'] != 'Not Run')
    all_run = all(r['status'] != 'Not Run' for r in test_results.values())
    
    if all_passed and all_run:
        print("\033[92mALL TESTS PASSED\033[0m")
    elif all_passed:
        print("\033[93mALL RUN TESTS PASSED (some tests were not run)\033[0m")
    else:
        print("\033[91mSOME TESTS FAILED\033[0m")
    
    print("=" * 60 + "\n")

def main():
    logger.info(f"Starting DerbyNet system test against broker {args.broker}")
    
    try:
        run_tests()
        
        # Clean up
        if mqtt_client:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        
        # Print results
        print_results()
        
        # Log results
        logger.info(f"Test completed. Overall status: {json.dumps(test_results)}")
        
        # Create output file
        output_file = os.path.join(os.path.dirname(__file__), 'system_test_results.json')
        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'broker': args.broker,
                'results': test_results
            }, f, indent=2)
        
        logger.info(f"Test results saved to {output_file}")
        
        # Exit with success code only if all tests passed
        return 0 if all(r['status'] == 'Pass' for r in test_results.values() if r['status'] != 'Not Run') else 1
    
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error during test: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())