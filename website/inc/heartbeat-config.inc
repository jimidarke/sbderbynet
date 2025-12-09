<?php
/**
 * Centralized Heartbeat and Timeout Configuration
 *
 * This file provides standardized timeout thresholds for the race state engine.
 * All components (PHP, JavaScript, Python) should use these values for consistency.
 *
 * Timeout Cascade (should increase upward):
 *   HEARTBEAT_INTERVAL <= TIMER_RECENT_THRESHOLD < TIMER_STALE_THRESHOLD
 *   < TIMER_DISCONNECT_THRESHOLD < DEVICE_INACTIVE_THRESHOLD
 *
 * @version 0.6.4
 */

// =============================================================================
// HEARTBEAT TIMING (TIGHTENED for faster responsiveness)
// =============================================================================

// How often heartbeats are sent from Python server to DerbyNet (seconds)
define('HEARTBEAT_INTERVAL', 2);

// Maximum age (seconds) for a timer heartbeat to be considered "recent"
// Used by Python server for confirmed flag calculation
define('TIMER_RECENT_THRESHOLD', 3);

// =============================================================================
// DATABASE STALE DETECTION
// =============================================================================

// Age (seconds) at which a timer is marked as stale/not-ready in the database
// Should be slightly larger than TIMER_RECENT_THRESHOLD to allow for network latency
define('TIMER_STALE_THRESHOLD', 5);

// =============================================================================
// CONNECTION TIMEOUTS
// =============================================================================

// Time (seconds) without heartbeat before PHP considers timer disconnected
// This transitions timer_state to TIMER_NOT_CONNECTED
define('TIMER_DISCONNECT_THRESHOLD', 10);

// Time (seconds) before marking a device as inactive in DeviceStatus table
define('DEVICE_INACTIVE_THRESHOLD', 20);

// =============================================================================
// FRONTEND DISPLAY
// =============================================================================

// Time (seconds) before frontend shows timer as offline
// Should match TIMER_STALE_THRESHOLD for consistency
define('FRONTEND_OFFLINE_THRESHOLD', 5);

// =============================================================================
// RACE REQUIREMENTS
// =============================================================================

// Minimum number of finish timers required to start a race
define('MIN_TIMERS_FOR_RACE', 3);

// Whether to allow racing with fewer than MIN_TIMERS_FOR_RACE timers online
// When true: Race proceeds with warning
// When false: Race start is blocked
define('ALLOW_DEGRADED_RACE', true);

// =============================================================================
// RACE STATE INTEGRITY
// =============================================================================

// Grace period (seconds) before flagging state integrity issues
// Allows for brief state transitions without false alarms
define('INTEGRITY_GRACE_PERIOD', 3);

// Time (seconds) to keep orphan physical start records before clearing
define('ORPHAN_START_TIMEOUT', 120);

// =============================================================================
// PYTHON SERVER CONSTANTS (for reference - update derbyRace.py to match)
// =============================================================================
// HEARTBEAT_TIMEOUT should be set to TIMER_RECENT_THRESHOLD (3 seconds)
// HEARTBEAT_PULSE should be set to 1 second
// Recency check in derbyapi.py should use TIMER_RECENT_THRESHOLD (3.0 seconds)
// HEARTBEAT_INTERVAL in derbyapi.py should be 2 seconds
