#!/usr/bin/env python3
"""
Racing Event Simulation Script

This script simulates a complete racing event by interfacing with the DerbyNet system.
It validates that the system is in STAGING state, then executes race cycles of:
start race -> 3 random lane finishes -> stop race -> repeat

File location: /var/lib/infra/app/simulate_racing.py
Usage: python3 simulate_racing.py

Version History:
- 0.1.0 - January 26, 2025 - Initial implementation for race simulation testing
"""

import random
import time
import logging
import sys
import signal
from datetime import datetime
from derbyapi import DerbyNetClient
from serverlogger import ServerLogger

# Version information
VERSION = "0.1.0"

# Initialize logging
logger = ServerLogger(
    name='RACESIM',
    log_file='/var/log/derbynet.log',
    level=logging.INFO,
).get_logger()

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame): 
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    logger.info("Shutdown signal received, finishing current race...")
    shutdown_requested = True

def validate_race_state(api_client, expected_state):
    """
    Validate that the DerbyNet system is in STAGING state (blue LED)
    
    Args:
        api_client: DerbyNetClient instance
        
    Returns:
        bool: True if system is ready to race (STAGING), False otherwise
    """
    expected_state = expected_state.lower().strip()
    try:
        race_status = api_client.get_race_status()
        if not race_status:
            logger.error("Failed to get race status from DerbyNet API")
            return False
        # Check if there's an active heat
        active = race_status.get('active', False)
        #timer_state = race_status.get('timer-state', '')
        timer_state = race_status.get('timer-state-string', '').lower().strip()
        logger.info(f"Race status - Active: {active}, Race state: {timer_state}, Expected state: {expected_state}")
        if timer_state == expected_state:
            return True
        else:
            logger.error(f"System not in expected state: {expected_state}. Current state: {timer_state}")
            return False
    except Exception as e:
        logger.error(f"Error validating state: {e}")
        return False
'''
        # System should be active and in staging or connected state
        if active and timer_state.lower() in ['staging', 'connected']:
            logger.info("System is in STAGING state and ready to race")
            return True
        elif not active:
            logger.error("No active heat - system not ready to race")
            return False
        elif timer_state.lower() == 'running':
            logger.error("Race is already running - cannot start simulation")
            return False
        else:
            logger.error(f"System not in STAGING state. Current state: {timer_state}")
            return False
            
    except Exception as e:
        logger.error(f"Error validating staging state: {e}")
        return False
'''

def simulate_single_race(api_client):
    """
    Simulate a single race with start, 3 lane finishes, and stop
    
    Args:
        api_client: DerbyNetClient instance
        
    Returns:
        bool: True if race completed successfully, False otherwise
    """
    try:
        # Get race info for logging
        race_status = api_client.get_race_status()
        roundid = race_status.get('roundid', 0)
        heat = race_status.get('heat', 0)
        class_name = race_status.get('class', 'Unknown')
        
        logger.info(f"Starting simulated race - {class_name} Round {roundid} Heat {heat}")
        
        # Send start signal
        if not api_client.send_start():
            logger.error("Failed to send start signal")
            return False
            
        start_time = time.time()
        logger.info(f"Race started at {datetime.fromtimestamp(start_time).strftime('%H:%M:%S.%f')[:-3]}")
        
        # Wait random time before first finish (5-10 seconds)
        first_delay = random.uniform(4,5)
        logger.debug(f"Waiting {first_delay:.2f} seconds before first lane finish")
        time.sleep(first_delay)
        
        # validate race is active 
        validate_race_state(api_client, 'race running')

        # Create list of available lanes and randomize finish order
        available_lanes = [1, 2, 3]
        random.shuffle(available_lanes)
        lane_times = {}
        
        # Simulate 3 lane finishes with random delays
        for finish_position in range(3):
            if shutdown_requested:
                logger.warning("Shutdown requested during race simulation")
                return False
                
            lane = available_lanes[finish_position]
            current_time = time.time()
            race_time = round(current_time - start_time, 3)
            
            # Record the lane time (simulating what derbyRace.laneFinish would do)
            lane_times[lane] = race_time
            
            logger.info(f"Lane {lane} finished at {race_time}s (position #{finish_position + 1})")
            
            # Wait before next finish (except for last lane)
            if finish_position < 2:
                finish_delay = random.uniform(0.5, 1.5)
                logger.debug(f"Waiting {finish_delay:.2f} seconds before next lane finish")
                time.sleep(finish_delay)
        
        # Send finish results to DerbyNet
        if not api_client.send_finish(roundid, heat, lane_times):
            logger.error("Failed to send finish results")
            return False
        total_race_time = time.time() - start_time
        logger.info(f"Race completed in {total_race_time:.2f} seconds. Results: {lane_times}")
        time.sleep(1)  # Give time for results to be processed
        
        return True
        
    except Exception as e:
        logger.error(f"Error during race simulation: {e}")
        return False

def main():
    """Main execution function with infinite loop for continuous race simulation"""
    global shutdown_requested
    
    logger.info(f"Derby Race Simulator v{VERSION} starting...")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize DerbyNet API client
    api_client = DerbyNetClient("localhost")
    
    # Test initial connection
    if not api_client.login():
        logger.critical("Failed to connect to DerbyNet system. Exiting.")
        sys.exit(1)
    
    logger.info("Successfully connected to DerbyNet system")
    
    race_count = 0
    
    try:
        while not shutdown_requested:
            race_count += 1
            logger.info(f"=== Starting Race Simulation #{race_count} ===")
            
            # Simulate heartbeat to keep connection alive
            if not api_client.simulate_heartbeat():
                logger.error("Failed to send heartbeat to DerbyNet system")
                break
            logger.info("Heartbeat sent successfully")
            time.sleep(1)  # Wait a bit before next operation

            # Validate system is in STAGING state
            if not validate_race_state(api_client, 'staging'):
                logger.error("System not ready for racing. Exiting simulation.")
                break
                
            # Simulate the race
            if simulate_single_race(api_client):
                logger.info(f"Race #{race_count} completed successfully")
            else:
                logger.error(f"Race #{race_count} failed")
                break
            
            # Wait between races (5-10 seconds)
            if not shutdown_requested:
                between_race_delay = random.uniform(2,3)
                logger.info(f"Waiting {between_race_delay:.2f} seconds before next race...")
                time.sleep(between_race_delay)
                
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
    finally:
        logger.info(f"Race simulation ended after {race_count} races")
        logger.info("Derby Race Simulator shutdown complete")

if __name__ == "__main__":
    main()