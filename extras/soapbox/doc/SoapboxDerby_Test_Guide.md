# Soapbox Derby System Test Guide

This document provides a comprehensive test guide for validating the Soapbox Derby race management system, including core functionality and custom features.

## Component Tests

| ID | Segment | Title | Description | Expected Results |
|----|---------|-------|-------------|------------------|
| **CT-001** | Core System | System Boot Sequence | 1. Power up the main race server<br>2. Start components in order: derbyrace, derbyTime, finishtimer, derbydisplay, hlsfeed<br>3. Observe startup logs on each component | - All services start without errors<br>- Version 0.5.0 appears in logs<br>- Components establish MQTT connections<br>- Service discovery successful via mDNS |
| **CT-002** | Race Server | Race State Transitions | 1. Access coordinator interface<br>2. Verify STOPPED state<br>3. Click "Stage" button<br>4. Click "Start" button<br>5. Verify race completes | - Server transitions STOPPED→STAGING→RACING→STOPPED<br>- MQTT messages published to derbynet/race/state<br>- All displays update to show current state |
| **CT-003** | Timer Integration | Timer Protocol Heartbeat | 1. Start finish timer service<br>2. Monitor logs for 60-second heartbeat<br>3. Wait for 3 minutes observing heartbeats | - Timer maintains CONNECTED state<br>- 60-second heartbeat messages sent<br>- DerbyNet shows timer as connected |
| **CT-004** | MQTT Communication | Topic Structure Validation | 1. Use MQTT client tool to subscribe to derbynet/# topics<br>2. Trigger various system events<br>3. Analyze message format and content | - Messages follow schema in MQTT_API.md<br>- All required fields present in telemetry<br>- QoS levels correct per topic specifications |
| **CT-005** | Finish Timer | Lane Finish Detection | 1. Verify finish timer hardware is online<br>2. Trigger toggle switch for each lane<br>3. Observe LED state changes<br>4. Check message transmission | - LEDs change from red to purple when triggered<br>- MQTT messages sent with correct lane ID<br>- Timestamp data accurate and consistent |
| **CT-006** | Start Timer | Start Detection | 1. Verify start timer is online<br>2. Trigger start gate mechanism<br>3. Observe race state transition | - "GO" message published to MQTT<br>- Race state changes to RACING<br>- Timer starts counting on displays |
| **CT-007** | HLS Feed | Stream Availability | 1. Start HLS feed service<br>2. Access the M3U8 URL via browser<br>3. Check stream segments<br>4. Test with VLC player | - M3U8 file accessible at configured URL<br>- Stream contains valid segments<br>- Video plays with minimal latency |
| **CT-008** | Derby Display | Status Dashboard | 1. Start derby display service<br>2. Access status dashboard page<br>3. Verify real-time status updates | - Dashboard shows all connected devices<br>- Status updates in real-time<br>- Telemetry data displayed correctly |
| **CT-009** | DerbyNet Integration | DerbyNet Timer Connection | 1. Start race server and timer services<br>2. Access coordinator interface<br>3. Verify timer state in web interface<br>4. Trigger state transitions | - DerbyNet shows timer as CONNECTED<br>- State transitions propagate correctly<br>- Times recorded in database |

## Integration Tests

| ID | Segment | Title | Description | Expected Results |
|----|---------|-------|-------------|------------------|
| **IT-001** | Race Workflow | Full Race Cycle | 1. Register test racers<br>2. Check them in<br>3. Generate schedule<br>4. Run complete race with automatic timing | - Racers properly scheduled<br>- Race times recorded correctly<br>- Results stored and displayed |
| **IT-002** | Triple Elimination | Advancement Logic | 1. Configure system for triple elimination<br>2. Run preliminary round with 24+ racers<br>3. Verify advancement to semi-finals<br>4. Complete semi-finals and finals | - Top 21 racers advance to semi-finals<br>- Top 3 racers advance to finals<br>- Winners correctly determined |
| **IT-003** | Timer Integration | Race Timing End-to-End | 1. Start a race from coordinator<br>2. Trigger start timer<br>3. Trigger finish timers in sequence<br>4. Verify time recording | - Start event correctly recorded<br>- Lane finish times accurate<br>- Race results stored with correct times |
| **IT-004** | Display Integration | Display Updates | 1. Configure various kiosk types<br>2. Start race and run through completion<br>3. Observe kiosk updates | - All kiosks update with current information<br>- Now-racing display shows race in progress<br>- Results displays update when race completes |
| **IT-005** | HLS Replay | Replay Functionality | 1. Configure replay settings<br>2. Complete a race<br>3. Observe automatic replay<br>4. Test manual replay trigger | - Race replay shown on configured displays<br>- Replay uses HLS stream<br>- Replay parameters match configuration |
| **IT-006** | Video Storage | Race Video Capture | 1. Enable video storage<br>2. Run a race with replay<br>3. Check video directory | - MKV file saved with correct naming<br>- ClassA_Round1_Heat01.mkv format<br>- Video content playable with expected duration |

## Resilience Tests

| ID | Segment | Title | Description | Expected Results |
|----|---------|-------|-------------|------------------|
| **RT-001** | Network Resilience | MQTT Broker Restart | 1. Start all components<br>2. Restart MQTT broker service<br>3. Monitor component recovery | - All components detect broker outage<br>- Components automatically reconnect<br>- Operation resumes without manual intervention |
| **RT-002** | Network Resilience | Component Recovery | 1. Start race workflow<br>2. Kill finish timer process<br>3. Restart finish timer<br>4. Verify recovery | - System detects timer disconnection<br>- Timer successfully reconnects<br>- Race operation can continue |
| **RT-003** | Service Discovery | mDNS Functionality | 1. Change MQTT broker address<br>2. Restart components<br>3. Verify service discovery | - Components use service discovery to find broker<br>- Connection established on new address<br>- Telemetry messages continue flowing |
| **RT-004** | Error Handling | Finish Timer Error Recovery | 1. Disconnect finish timer hardware<br>2. Attempt to start race<br>3. Reconnect hardware<br>4. Verify recovery | - System detects hardware disconnection<br>- Error state properly reported<br>- System recovers when hardware reconnected |

## Performance Tests

| ID | Segment | Title | Description | Expected Results |
|----|---------|-------|-------------|------------------|
| **PT-001** | System Performance | Race Throughput | 1. Set up schedule with 20+ heats<br>2. Run races continuously for 30 minutes<br>3. Monitor timing performance | - System maintains consistent timing accuracy<br>- No degradation in responsiveness<br>- All race results recorded correctly |
| **PT-002** | HLS Performance | Stream Stability | 1. Configure multiple clients viewing HLS stream<br>2. Run races continuously for 30 minutes<br>3. Monitor stream performance | - Stream remains stable and continuous<br>- Replay functionality works consistently<br>- No frame drops or artifacts |
| **PT-003** | System Load | Multi-Component Load Test | 1. Run all system components<br>2. Monitor CPU, memory, network usage<br>3. Execute races, replays, and updates simultaneously | - CPU usage remains under 70%<br>- Memory usage remains stable<br>- No component crashes under load |

## Feature Tests

| ID | Segment | Title | Description | Expected Results |
|----|---------|-------|-------------|------------------|
| **FT-001** | Feature | Racer Registration | 1. Import roster from CSV<br>2. Add racers manually<br>3. Assign to racing classes<br>4. Check-in racers | - Roster imported correctly<br>- Racers assigned to proper classes<br>- Check-in status tracked accurately |
| **FT-002** | Feature | Photo/Video Management | 1. Capture racer headshots<br>2. Capture car photos<br>3. Configure HLS stream<br>4. Test replay with racer information | - Photos stored and linked to correct racers<br>- Media displays on appropriate screens<br>- HLS stream captures race action<br>- Replay shows race with racer information |
| **FT-003** | Feature | Award Management | 1. Configure awards (speed, design, etc.)<br>2. Complete races to determine winners<br>3. Test award presentation mode | - Awards properly configured<br>- Winners determined by criteria<br>- Award presentation displays correctly |
| **FT-004** | Feature | Kiosk Assignment | 1. Set up multiple display devices<br>2. Configure different kiosk types<br>3. Test display assignment from coordinator | - Kiosks register with system<br>- Assignment changes apply immediately<br>- Each kiosk shows appropriate content |

## Security Tests

| ID | Segment | Title | Description | Expected Results |
|----|---------|-------|-------------|------------------|
| **SC-001** | Security | Role-Based Access | 1. Test access with different roles (admin, racer, judge)<br>2. Attempt to access restricted functions<br>3. Verify permission enforcement | - Admin role has full access<br>- Restricted roles limited appropriately<br>- Permission failures logged |
| **SC-002** | Security | Data Validation | 1. Test API endpoints with invalid data<br>2. Attempt SQL injection in forms<br>3. Test cross-site scripting vulnerabilities | - Invalid data properly rejected<br>- No SQL injection possible<br>- XSS attempts blocked |

## Logging Tests

| ID | Segment | Title | Description | Expected Results |
|----|---------|-------|-------------|------------------|
| **LG-001** | Logging | Standardized Logging | 1. Trigger various system events<br>2. Check log output from all components<br>3. Verify log format and content | - All components use common derbylogger<br>- Structured JSON logging format used<br>- Correlation IDs present for cross-component tracking |
| **LG-002** | Monitoring | Telemetry Data | 1. Monitor MQTT telemetry topics<br>2. Verify all components publish telemetry<br>3. Check telemetry content against specification | - All required telemetry fields present<br>- Update frequency meets requirements<br>- System status correctly reflected |

## Hardware Tests

| ID | Segment | Title | Description | Expected Results |
|----|---------|-------|-------------|------------------|
| **HA-001** | Hardware | Finish Timer Hardware | 1. Test toggle switches for each lane<br>2. Verify LED indicators<br>3. Check 7-segment display<br>4. Test DIP switch configuration | - Switches register finish events<br>- LEDs indicate proper lane state<br>- Display shows correct information<br>- DIP switches configure lane correctly |
| **HA-002** | Hardware | Start Timer Hardware | 1. Test start gate switch<br>2. Verify LED indicators<br>3. Check environmental sensors<br>4. Test battery monitoring | - Start switch triggers race start<br>- LED indicates timer state<br>- Environmental data reported<br>- Battery level monitored correctly |
| **HA-003** | Hardware | Display Hardware | 1. Test screen resolution compatibility<br>2. Check browser compatibility<br>3. Verify kiosk mode operation<br>4. Test offline functionality | - Content displays correctly on all resolutions<br>- Chrome/Firefox compatibility<br>- Kiosk mode prevents user interaction<br>- Limited functionality in offline mode |

## Recovery Tests

| ID | Segment | Title | Description | Expected Results |
|----|---------|-------|-------------|------------------|
| **REC-001** | Recovery | Database Backup | 1. Create database backup<br>2. Corrupt active database<br>3. Restore from backup<br>4. Verify data integrity | - Backup process completes successfully<br>- Restoration process works<br>- All race data preserved<br>- System operational after restore |
| **REC-002** | Recovery | Power Failure | 1. Run system normally<br>2. Simulate power failure<br>3. Restore power<br>4. Check system recovery | - No data loss during power failure<br>- All components restart automatically<br>- Race state recovers appropriately<br>- Operation can continue after recovery |

## Soapbox Derby Specific Tests

| ID | Segment | Title | Description | Expected Results |
|----|---------|-------|-------------|------------------|
| **SB-001** | Soapbox | Preliminary Round Timing | 1. Register 30+ racers<br>2. Run preliminary round with 3 heats per racer<br>3. Verify average time calculation | - Each racer gets 3 runs in different lanes<br>- Average time calculated correctly<br>- Standings show preliminary results |
| **SB-002** | Soapbox | Semi-Final Advancement | 1. Complete preliminary round<br>2. Verify advancement of top 21 racers<br>3. Check semi-final schedule | - Exactly 21 racers advance to semi-finals<br>- Advancement based on average time<br>- Semi-final schedule generated correctly |
| **SB-003** | Soapbox | Final Round | 1. Complete semi-final round<br>2. Verify advancement of top 3 racers<br>3. Run final round<br>4. Determine final rankings | - Top 3 racers advance to finals<br>- Final standings determined by final round times<br>- 1st, 2nd, 3rd places correctly assigned |
| **SB-004** | Soapbox | Lane Status Indicators | 1. Configure LED status for each lane<br>2. Run through race cycle<br>3. Observe indicator changes | - LED state updates via MQTT<br>- Red = Ready, Green = Go, Purple = Finished<br>- All lane indicators function correctly |
| **SB-005** | Soapbox | Racer Display | 1. Configure pinny display<br>2. Test with different racer numbers<br>3. Verify display update | - MQTT topic derbynet/lane/{lane}/pinny updates<br>- 4-digit racer numbers displayed correctly<br>- Display updates for each new race |
| **SB-006** | Integration | Digital Race Brackets | 1. Test bracket visualization display<br>2. Run races and observe bracket updates<br>3. Verify advancement visualization | - Bracket shows current tournament state<br>- Visual tracking of advancement<br>- Updates in real-time as races complete |
| **SB-007** | Integration | Racer Profile System | 1. Enter detailed racer information<br>2. Import racer photos<br>3. Test display when racer is on track | - Racer information displayed when racing<br>- Photos shown with racer details<br>- Data pulled from DerbyNet database |
| **SB-008** | Integration | Announcer Support | 1. Configure race commentary dashboard<br>2. Run races with various racers<br>3. Check generated information | - Racer introduction snippets generated<br>- Real-time statistics provided<br>- Interesting facts highlighted |
| **SB-009** | Resilience | Network Metrics | 1. Run network_metrics.py<br>2. Monitor connection quality<br>3. Test under various network conditions | - Network metrics collected<br>- Performance data logged<br>- System adapts to different conditions |
| **SB-010** | Resilience | Failure Simulation | 1. Run network_resilience_test.py<br>2. Test different failure scenarios<br>3. Verify recovery behavior | - System recovers from broker restart<br>- Handles component failures<br>- Self-healing behavior works |

## Setup Instructions for Testing

1. **Environment Preparation**
   - Set up Raspberry Pi with Raspberry Pi OS
   - Configure network for 192.168.100.x subnet
   - Install required dependencies (Python, PHP, MQTT broker)

2. **Component Installation**
   - Clone repository and set up components
   - Configure services according to documentation
   - Install necessary hardware for finish line and start gate

3. **Test Data Setup**
   - Import sample race roster
   - Configure test racing format
   - Set up test kiosks and displays

4. **Testing Tools**
   - network_resilience_test.py for testing recovery
   - MQTT client tool for monitoring messages
   - system_test.py for automated component testing

## Test Execution Guidelines

1. **Order of Testing**
   - Start with Component Tests (CT-xxx)
   - Proceed to Integration Tests (IT-xxx)
   - Follow with Resilience Tests (RT-xxx)
   - Complete with Performance Tests (PT-xxx)

2. **Failure Handling**
   - Document all test failures with screenshots
   - Include detailed logs when reporting issues
   - Verify failures are not environment-related

3. **Performance Criteria**
   - System must handle 30+ racers efficiently
   - Race timing accuracy must be within 0.01 seconds
   - Display updates must occur within 1 second
   - All components must recover automatically from failures

## Automated Testing Support

The system includes Python-based testing tools in the `/extras/soapbox/tests/` directory:

1. **system_test.py**: Tests core component functionality
   ```bash
   python3 tests/system_test.py               # Run all tests
   python3 tests/system_test.py --test timers # Test specific component
   python3 tests/system_test.py --verbose     # Verbose output
   ```

2. **network_resilience_test.py**: Tests recovery from network failures
   ```bash
   python3 tests/network_resilience_test.py
   python3 tests/network_resilience_test.py --scenario broker_restart --verbose
   ```

## Common Testing Commands

```bash
# Start services for testing
sudo systemctl start derbyrace
sudo systemctl start derbyTime
sudo systemctl start finishtimer
sudo systemctl start derbydisplay
sudo systemctl start hlsfeed

# View logs during testing
sudo journalctl -u derbyrace -f
sudo journalctl -u finishtimer -f
sudo journalctl -u derbydisplay -f
sudo journalctl -u hlsfeed -f

# Monitor MQTT messages
mosquitto_sub -v -t "derbynet/#"

# Test HLS stream
curl -I http://derbynetpi:8037/hls/stream.m3u8
```

## Version Information

This test guide covers version 0.5.0 of the Soapbox Derby system, which includes:
- Race Server (derbyRace.py): 0.5.0
- Finish Timer (derbynetPCBv1.py): 0.5.0
- Start Timer (main.py): 0.5.0
- Derby Display (derbydisplay.py): 0.5.0
- HLS Feed (replay_handler.py): 0.5.0
- LCD Display (derbyLCD.py): 0.5.0