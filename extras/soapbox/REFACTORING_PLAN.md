# Soapbox Derby System Refactoring Plan

This document outlines the planned improvements to enhance stability, reliability, and user experience of the Soapbox Derby race management system.

## Task List

### 1. HLS Feed Service Optimization

- [x] **Config Management**
  - [x] Move hard-coded stream parameters to configuration file
  - [x] Implement secure credential storage for camera access
  - [x] Create configurable stream quality settings

- [x] **Stream Reliability**
  - [x] Add error detection and automatic recovery
  - [x] Implement stream health monitoring
  - [x] Create alert mechanism for stream issues

- [x] **Nginx Optimization**
  - [x] Update nginx configuration for better caching
  - [x] Add proper CORS and security headers
  - [x] Implement content compression

- [x] **TS File Management**
  - [x] Create cleanup script for old TS segment files
  - [x] Add configurable retention policy
  - [x] Implement disk space monitoring

### 2. Network Stability Improvements

- [x] **Shared Network Library**
  - [x] Extract common network code into reusable library
  - [x] Standardize reconnection strategies
  - [x] Implement consistent offline operation mode

- [x] **Service Discovery**
  - [x] Add ZeroConf/mDNS implementation in derbynet module
  - [x] Implement service discovery in Derby Display
  - [x] Implement service discovery in Finish Timer
  - [x] Implement service discovery in server (derbyRace.py)
  - [x] Implement service discovery in Start Timer (ESP32)

- [x] **Resilience Testing**
  - [x] Create network failure simulation scripts (tests/network_resilience_test.py)
  - [x] Develop automated tests for reconnection scenarios
  - [x] Add performance metrics for network operations
  - [x] Run resilience tests on full system deployment

### 3. Logging Framework

- [x] **Unified Logging**
  - [x] Create standardized logging library for all components
  - [x] Implement structured JSON logging format
  - [x] Add correlation IDs for cross-component tracking

- [x] **Log Management**
  - [x] Add log rotation and retention policies (implemented in derbylogger.py)
  - [x] Implement centralized log aggregation (updated all component loggers to use common implementation)
  - [ ] Create log search and analysis tools

- [ ] **Monitoring Dashboard**
  - [ ] Develop real-time logging dashboard
  - [ ] Add alerting for critical log events
  - [ ] Create performance visualization

### 4. Kiosk Display Improvements

- [~] **Code Cleanup**
  - [ ] Consolidate redundant kiosk implementations
  - [ ] Refactor startup scripts for clarity
  - [x] Add better error handling

- [x] **User Experience**
  - [x] Create new status/monitoring display
  - [x] Implement offline mode with cached data
  - [x] Add responsive design for different screen sizes

- [ ] **Administration**
  - [ ] Add remote management capabilities
  - [ ] Create configuration UI for administrators
  - [ ] Implement kiosk health monitoring

### 5. Testing Framework

- [x] **Unit Testing**
  - [x] Set up test framework for Python components
  - [x] Write unit tests for core functionality
  - [x] Add automated test running

- [~] **Integration Testing**
  - [x] Create end-to-end test scenarios
  - [ ] Implement hardware simulation for testing
  - [x] Develop network failure testing

- [ ] **Performance Testing**
  - [~] Set up benchmarking tools (partially implemented in network_metrics.py)
  - [ ] Develop load testing scenarios
  - [ ] Create performance regression detection

### 6. Documentation

- [x] **README Files**
  - [x] Add README.md to each major component (All major components have README files)
  - [x] Document configuration options
  - [ ] Add architecture diagrams

- [x] **API Documentation**
  - [x] Document MQTT topic structure
  - [x] Create API reference for HTTP endpoints
  - [x] Document message formats

- [ ] **Setup Guides**
  - [ ] Create deployment guide
  - [ ] Add troubleshooting documentation
  - [ ] Create development environment setup guide

### 7. DerbyNet Integration Improvements

- [x] **Timer Protocol Enhancements**
  - [x] Implement full DerbyNet timer heartbeat protocol (60-second requirement)
  - [x] Add proper state transitions (CONNECTED → STAGING → RUNNING)
  - [x] Implement error state handling (UNHEALTHY, NOT_CONNECTED)
  - [x] Create resilient timer reconnection logic

- [x] **HLS Replay Integration**
  - [x] Standardize HLS stream URL to match DerbyNet expectations (http://derbynetpi:8037/hls/stream.m3u8)
  - [x] Implement proper replay command handling (START, REPLAY, RACE_STARTS, CANCEL)
  - [x] Add support for configurable replay parameters (duration, speed, repeat count)
  - [x] Create video storage with DerbyNet-compatible naming (ClassA_Round1_Heat01.mkv)

- [ ] **Kiosk Compatibility**
  - [ ] Implement compatibility with DerbyNet kiosk assignment system
  - [ ] Create adapters for different kiosk types (now-racing, standings, ondeck, results-by-racer)
  - [ ] Implement polling mechanism for updates
  - [ ] Add support for WebSocket updates where available

## Implementation Status

### Completed Items
- [x] HLS Feed Service Optimization (Task 1 - all subtasks)
- [x] Shared Network Library implementation (Task 2.1)
- [x] Service Discovery implementation in all components (Task 2.2)
- [x] Network Resilience Testing including performance metrics and full system testing (Task 2.3)
- [x] Unified logging implementation (Task 3.1)
- [x] Log Management - centralized log aggregation (Task 3.2)
- [x] User Experience improvements for Kiosk Display (Task 4.2)
- [x] Testing framework basics (Task 5.1)
- [x] README files for all major components (Task 6.1)
- [x] API Documentation for MQTT topics (Task 6.2)
- [x] Performance metrics framework (Part of Task 5.3)
- [x] DerbyNet Timer Protocol Enhancements (Task 7.1)
- [x] HLS Replay Integration (Task 7.2)

### Current Priority

1. **High Priority (Stability)**
   - [x] Complete centralized log aggregation implementation (Task 3.2)
   - [x] Expand syslog integration to all components
   - [x] Implement DerbyNet timer protocol enhancements (Task 7.1)
   - [ ] Create log search and analysis tools (remaining part of Task 3.2)

2. **Medium Priority (Features)**
   - [x] Implement HLS replay integration with DerbyNet (Task 7.2)
   - [ ] Implement kiosk compatibility with DerbyNet (Task 7.3)
   - [ ] Consolidate redundant kiosk implementations
   - [ ] Refactor startup scripts for clarity
   - [ ] Create Setup Guides (Task 6.3)

3. **Lower Priority (Enhancements)**
   - [ ] Administration functionality for kiosk displays
   - [ ] Advanced testing implementation
   - [ ] Monitoring dashboard development

## Next Steps

Our previous focus on high-priority stability items has been successful:

1. **✅ Service Discovery Implementation**:
   - ✅ ZeroConf/mDNS integration is now implemented in the derbynet module
   - ✅ All major components (Derby Display, Finish Timer, Server, Start Timer) now use service discovery
   - ✅ All components include appropriate fallback mechanisms

2. **✅ Network Resilience Testing**:
   - ✅ Network failure simulation scripts created (tests/network_resilience_test.py)
   - ✅ Automated tests for reconnection scenarios implemented
   - ✅ Performance metrics framework for network operations implemented
   - ✅ Resilience tests run on full system deployment with successful results

3. **✅ Log Management and DerbyNet Integration**:
   - ✅ Expanded centralized log aggregation to all components 
   - ✅ Implemented full DerbyNet timer protocol with proper state handling
   - ✅ Standardized HLS configuration for DerbyNet compatibility
   - ✅ Created HLS replay handler for DerbyNet replay commands

### Current Focus Areas:

1. **Log Analysis and Monitoring**:
   - Add log search and analysis tools
   - Integrate with monitoring dashboard

2. **Kiosk Compatibility and Display Improvements**:
   - Implement compatibility with DerbyNet kiosk assignment system
   - Consolidate redundant kiosk implementations
   - Create adapters for different DerbyNet kiosk types

3. **Documentation and Testing**:
   - Create deployment guides based on recent integration improvements
   - Add troubleshooting documentation for DerbyNet integration
   - Implement hardware simulation for integration testing

## Recent Updates (May 2025)

### DerbyNet Integration Improvements
We've made significant progress in integrating our system with DerbyNet:

1. **Logging System Standardization**:
   - Updated all component loggers to use the common derbylogger implementation
   - Added fallback mechanisms for compatibility with existing code
   - Implemented structured JSON logging across all components
   - Added correlation IDs for cross-component tracking
   
2. **Timer Protocol Enhancement**:
   - Implemented proper timer state management (CONNECTED, STAGING, RUNNING, UNHEALTHY, NOT_CONNECTED)
   - Added state transition validation to prevent invalid state changes
   - Implemented 60-second heartbeat protocol required by DerbyNet
   - Enhanced error handling for API communication failures
   
3. **HLS Replay System**:
   - Standardized HLS stream URL to match DerbyNet's expected format
   - Created a dedicated replay handler service for DerbyNet replay commands
   - Implemented video recording with DerbyNet-compatible naming
   - Added configurable replay parameters matching DerbyNet defaults
   
These improvements significantly enhance our integration with DerbyNet while maintaining compatibility with the existing system architecture. The logging enhancements will make it easier to diagnose integration issues, while the timer protocol and HLS replay improvements ensure seamless operation with the DerbyNet web application.