# Derby Finish Timer

## Overview

The Derby Finish Timer is a critical component of the Soapbox Derby race management system. It is responsible for detecting when cars cross the finish line and communicating this information to the central race server. The system uses reliable hardware inputs and MQTT communication to ensure accurate and timely race results.

## Features

- **Lane Finish Detection**: Uses hardware toggle switches to detect when cars cross the finish line
- **LED Status Indicators**: Visual feedback of timer state (red, blue, green, purple)
- **Numeric Display**: Shows lane number, racer number, and diagnostic messages
- **Telemetry Reporting**: Sends battery level, WiFi signal, CPU usage and other status information
- **Network Resilience**: Robust handling of network interruptions and reconnection
- **Message Persistence**: Stores critical race events during network outages
- **Automatic Recovery**: Reconnects automatically with exponential backoff
- **Status Visualization**: Indicates connection status through LED and display
- **Race Protocol**: Manages timing events according to race protocol

## Hardware

The finish timer utilizes the DerbyNet PCB v1 hardware with the following components:
- Raspberry Pi-based controller
- Physical toggle switch for finish line detection
- RGB LED for status indication
- 4-digit 7-segment display
- DIP switches for lane configuration
- Battery monitoring circuitry

### PCB V1 Hardware Pinout

| NAME | GPIO PIN | HW PIN | FUNCTION |
|------|----------|--------|----------|
| TOGGLE | 24 | 18 | INPUT |
| SDA | 2 | 3 | I2C (ADC) |
| SCL | 3 | 5 | I2C (ADC) |
| DIP1 | 6 | 31 | INPUT |
| DIP2 | 13 | 33 | INPUT |
| DIP3 | 19 | 35 | INPUT |
| DIP4 | 26 | 37 | INPUT |
| CLK | 18 | 12 | DISPLAY |
| DIO | 23 | 16 | DISPLAY |
| REDLED | 8 | 24 | OUTPUT |
| GREENLED | 7 | 26 | OUTPUT |
| BLUELED | 1 | 28 | OUTPUT |

## Communication Protocol

The finish timer communicates with the central server using MQTT protocol with the following topics:

### Topics Published By Timer
- `derbynet/device/{hwid}/state` - Toggle state and timestamp (QoS 2)
- `derbynet/device/{hwid}/telemetry` - Telemetry data (QoS 1)
- `derbynet/device/{hwid}/status` - Online/offline status (QoS 1, retained)

### Topics Subscribed By Timer
- `derbynet/lane/{lane}/led` - LED color control
- `derbynet/lane/{lane}/pinny` - Numeric display control
- `derbynet/device/{hwid}/update` - Firmware update trigger

## Network Resilience Features

The finish timer includes several features to ensure reliability even in challenging network conditions:

1. **Connection Resilience**
   - Exponential backoff reconnection (5s initial delay, max 5 minutes)
   - Configurable retry parameters
   - Visual feedback during reconnection attempts

2. **Message Persistence**
   - Local storage of critical messages during network outages
   - Disk-based queue for events when offline
   - Message prioritization based on importance

3. **State Recovery**
   - Automatic state synchronization after reconnection
   - Tracking of offline duration for diagnostics
   - Replay of missed critical events

4. **Heartbeat Monitoring**
   - Regular status reporting (every 2 seconds)
   - Connection status visualization
   - Battery and WiFi signal strength reporting

## LED Status Indicators

| Color | Meaning |
|-------|---------|
| Red | Race stopped/not ready |
| Blue | Ready to race (toggle must be up) |
| Green | Race in progress |
| Purple | Lane has finished |
| Yellow | Connection/hardware error |
| White | Initial power-on/diagnostic mode |

## Display Codes

| Code | Meaning |
|------|---------|
| LAN1-4 | Lane number configuration |
| ---- | Standby/idle |
| FLIP | Toggle needs to be in up position |
| COnn | Attempting to connect |
| BATT | Low battery warning |
| Err0-9 | Error conditions |
| rt## | Reconnection attempt number |

## Server Coordination

The finish timer works closely with the Derby Race server component which:
- Coordinates with multiple timers
- Manages race state transitions
- Handles timing calculations and results
- Provides timer synchronization
- Monitors timer health through heartbeats
- Detects and handles timer timeouts

## Deployment

1. The finish timer is deployed as a system service: `finishtimer.service`
2. It automatically starts on boot and reconnects as needed
3. Each timer identifies its lane through DIP switch settings

## Setup and Configuration

The timer lane configuration is set via DIP switches:
- Lane 1: DIP settings `1000`
- Lane 2: DIP settings `1001`
- Lane 3: DIP settings `1010`
- Lane 4: DIP settings `1011`

## Diagnostics

The finish timer logs extensive diagnostic information:
- All logs are sent to local file `/var/log/derbynet.log`
- Logs are also sent to central syslog server (192.168.100.10:514)
- Each log entry includes hardware ID for easy identification

## Device Startup Sequence

1. Hardware initialization and self-test
2. Visual LED and display test sequence
3. MQTT connection establishment
4. Status reporting
5. Subscription to control topics
6. Ready for race events

## Race Sequence

1. Server sends blue LED command when race is staged
2. Timer shows "FLIP" if toggle is not in ready position
3. When race starts, server sends green LED command
4. Timer detects toggle state change when car crosses finish line
5. Timer sends toggle event with precise timestamp
6. Server calculates race times and updates displays
7. Timer LED changes to purple when lane has finished

## Troubleshooting

Common error indicators:
- Yellow LED: Connection or hardware error
- Flashing LED: Connection retry in progress
- Err0: Unhandled exception
- Err1: Main loop error
- Err4/5: MQTT connection error
- BATT display: Low battery warning (under 20%)