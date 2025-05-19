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

- [~] **Log Management**
  - [x] Add log rotation and retention policies (implemented in derbylogger.py)
  - [~] Implement centralized log aggregation (partially implemented with syslog in Start Timer)
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

## Implementation Status

### Completed Items
- [x] HLS Feed Service Optimization (Task 1 - all subtasks)
- [x] Shared Network Library implementation (Task 2.1)
- [x] Service Discovery implementation in all components (Task 2.2)
- [x] Network Resilience Testing including performance metrics and full system testing (Task 2.3)
- [x] Unified logging implementation (Task 3.1)
- [x] Log rotation and retention policies (Task 3.2 - partially completed)
- [x] User Experience improvements for Kiosk Display (Task 4.2)
- [x] Testing framework basics (Task 5.1)
- [x] README files for all major components (Task 6.1)
- [x] API Documentation for MQTT topics (Task 6.2)
- [x] Performance metrics framework (Part of Task 5.3)

### Current Priority

1. **High Priority (Stability)**
   - Complete centralized log aggregation implementation (Task 3.2)
   - Expand syslog integration to all components

2. **Medium Priority (Features)**
   - Consolidate redundant kiosk implementations
   - Refactor startup scripts for clarity
   - Create Setup Guides (Task 6.3)

3. **Lower Priority (Enhancements)**
   - Administration functionality for kiosk displays
   - Advanced testing implementation
   - Monitoring dashboard development

## Next Steps

Continue implementation focusing on high-priority stability items:

1. **✅ Service Discovery Implementation**:
   - ✅ ZeroConf/mDNS integration is now implemented in the derbynet module
   - ✅ All major components (Derby Display, Finish Timer, Server, Start Timer) now use service discovery
   - ✅ All components include appropriate fallback mechanisms

2. **✅ Network Resilience Testing**:
   - ✅ Network failure simulation scripts created (tests/network_resilience_test.py)
   - ✅ Automated tests for reconnection scenarios implemented
   - ✅ Performance metrics framework for network operations implemented
   - ✅ Resilience tests run on full system deployment with successful results

3. **Log Management** (Next focus area):
   - Expand centralized log aggregation to all components
   - Add log search and analysis tools
   - Integrate with monitoring dashboard

Once these core stability improvements are complete, we'll move to focus on code cleanup and feature enhancements as outlined in the FEATURE_ENHANCEMENTS.md document.