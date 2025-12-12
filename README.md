# SBDerbyNet: Comprehensive Soapbox Derby Race Management System

![SBDerbyNet](https://raw.githubusercontent.com/jeffpiazza/derbynet/master/website/img/derbynet-300.png)

SBDerbyNet is a comprehensive race management system for children's soapbox derby racing events, built by extensively modifying and extending the original DerbyNet software. While DerbyNet was originally created for Pinewood Derby racing events (small wooden cars racing down a gravity track), SBDerbyNet transforms it into a complete solution for children's Soapbox Derby events (larger gravity-powered cars with children riding in them).

**Current Version: 1.0.0** | **License: MIT** | **Original Project: [DerbyNet](https://derbynet.org)**

---

## 🏁 Pull Request Summary: Major Enhancements to DerbyNet

This project represents substantial enhancements to the original DerbyNet system, adding comprehensive soapbox derby race management capabilities. The modifications are designed to be offered as a pull request back to the original DerbyNet project.

### 📊 Change Overview

- **~40 new files** in complete hardware infrastructure (`extras/soapbox/`)
- **Major refactoring** of core scheduling engine with critical bug fixes
- **3 new database tables** for elimination tournament support
- **Advanced hardware integration** with MQTT messaging architecture
- **Professional-grade display system** with modern UI/UX
- **Backward compatible** with existing DerbyNet functionality

### 🚀 Key Technical Contributions

#### 1. **New SoapBox Infrastructure Layer (`extras/soapbox/`)**

**Central Race Server (`infra/server/`)**
- Python-based coordination system using MQTT messaging protocol
- Standardized network library with resilient connection handling and message queuing
- Real-time race coordination between multiple hardware components such as finish timers and starting triggers

**Hardware Integration (`infra/finishtimer/` & `infra/starttimer/`)**
- Raspberry Pi finish timer with toggle switch detection and LED status indicators for each lane
- ESP32 start timer for race start signal detection
- Hardware abstraction layer supporting DerbyNet PCB v1 with detailed pinout specifications
- Network resilience features including offline message persistence and automatic recovery

**Live Video Streaming (`hlsfeed/`)**
- RTSP to HLS conversion using FFmpeg for multi-camera race coverage
- Nginx-based streaming server with automatic segment cleanup
- Replay handler integration for race event recording and analysis

#### 2. **Critical Race Scheduling Engine Fixes**

**Resolved Major Bug (`website/ajax/action.schedule.generate.inc`)**
- **Fixed critical parameter interpretation**: DerbyNet's `n_times_per_lane` parameter was being misunderstood
  - Before: `n_times_per_lane = 3` generated 9 races per racer (3 per lane × 3 lanes)
  - After: `n_times_per_lane = 1` generates 3 races per racer (1 per lane × 3 lanes)
- **Custom elimination scheduling** for single-race rounds bypassing problematic rotation logic
- **Automatic tournament detection** that intelligently adapts scheduling behavior

**Enhanced Scheduling Functions (`website/inc/schedule_one_round.inc`)**
- New `schedule_elimination_single_race()` function for sequential heat assignment
- Weight-based racer grouping for competitive matchups
- Enhanced heat ordering parameters optimized for elimination tournaments
- Inspection and registration validation preventing invalid racers from being scheduled

#### 3. **JSON-Based Elimination Tournament System**

**Configuration Architecture (`website/inc/elimination-configs/`)**
- Hardcoded tournament formats replacing complex UI configuration
- Age-group pattern matching using regex for automatic class detection
- Predefined race parameters (races per racer, advancement rules, scoring methods)
- Four tournament formats: Ages 6-8, Ages 9-11, Ages 12-14, and VIP brackets

**Database Schema (`website/sql/sqlite/elimination-tables.inc`)**
- `EliminationTournaments` - Tournament state and configuration tracking
- `EliminationRoundState` - Round progression and status management  
- `EliminationAdvancement` - Advancement audit trail and scoring history

**Tournament Management (`website/inc/elimination-config.inc`)**
- Configuration validation ensuring tournament integrity
- Tournament state persistence surviving system restarts
- API endpoints for tournament initialization and advancement

**Tournament Setup UI (`website/racing-groups.php`, `website/elimination-config-editor.php`)**
- Integrated Tournament Setup section on Racing Groups page for initializing tournaments
- Dedicated Configuration Editor with collapsible sections, auto-generated keys, and help tooltips
- Batch tournament status query (`query.elimination.tournament.all-status.inc`) for efficient page loads
- Real-time status display showing round progress and locked state

#### 4. **Enhanced Kiosk and Display System**

**Professional Elimination Displays (`website/kiosks/`)**
- `elimination-standings.kiosk` - Tournament standings with auto-scroll and modern gradient styling
- `elimination-results.kiosk` - Round-by-round race results with tournament context
- Real-time updates with 5-second auto-refresh cycles
- Color-coded status indicators (green "ADVANCING", red "ELIMINATED" badges)

**Visual Enhancements (`website/css/elimination-kiosks.css`)**
- Stunning gradient backgrounds with elegant card layouts
- Professional typography and smooth animations
- Responsive design adapting to different screen sizes
- Auto-scroll animation for long racer lists

#### 5. **Core DerbyNet System Enhancements**

**Broadcast Messaging System**
- Real-time text announcements to all active kiosk displays
- Overlay messaging with configurable duration (1-300 seconds)
- API endpoints for sending and clearing broadcast messages

**Smart Coordinator Interface**
- Schedule modal that automatically detects elimination tournaments
- Visual feedback when elimination tournaments are detected
- Preserved manual control while adding intelligent automation

**Scene Management Integration**
- Coordinator page integration for centralized scene control during races
- Real-time scene updates across all connected kiosks

### 🎯 Benefits for Original DerbyNet Project

#### **Universal Improvements (All DerbyNet Users)**
1. **Critical Bug Fixes**: Scheduling engine parameter fixes benefit all users
2. **Enhanced Kiosk Architecture**: Improved display system with better messaging
3. **Professional UI Components**: Modern styling and responsive design elements
4. **Robust Error Handling**: Better validation and edge case management

#### **New Feature Framework (Optional for Pinewood Derby)**
1. **Tournament System**: Reusable framework adaptable to other tournament formats
2. **MQTT Infrastructure**: Scalable messaging architecture for hardware integration
3. **Elimination Displays**: Professional tournament visualization system
4. **Hardware Abstraction**: Standardized approach to timer and device integration

#### **Soapbox Derby Specific (Add-on Package)**
1. **Complete Hardware Stack**: Production-ready soapbox derby infrastructure
2. **Live Streaming**: Camera integration for race viewing and replay
3. **Outdoor Optimization**: Network resilience for outdoor racing environments

---

## 🏗️ System Architecture

### Core DerbyNet Foundation
- **PHP Web Application**: Central race management with SQLite/Access database
- **Multi-device Architecture**: Central server with connected client displays
- **Timer Integration**: Automatic time capture with hardware timer support
- **Kiosk Display System**: Configurable displays with scene management

### SBDerbyNet Extensions

#### **Hardware Infrastructure Layer**
1. **Race Server** (`extras/soapbox/infra/server/derbyRace.py`): Central orchestration service managing race state, DerbyNet API communication, and timer coordination via MQTT
2. **Finish Timer** (`extras/soapbox/infra/finishtimer/`): Raspberry Pi-based lane finish detection using GPIO toggle switches with LED status indication
3. **Start Timer** (`extras/soapbox/infra/starttimer/`): ESP32-based race start signal detection and MQTT broadcasting
4. **Derby Display** (`extras/soapbox/infra/derbydisplay/`): Real-time race information display updating via MQTT
5. **HLS Feed Service** (`extras/soapbox/hlsfeed/`): RTSP/HLS video streaming for race viewing with automatic cleanup
6. **Race Simulation** (`extras/soapbox/infra/server/simulate_racing.py`): Comprehensive testing framework for system validation

#### **Enhanced Race Management**
- **Elimination Tournament Engine**: JSON-configured tournament formats with automatic progression
- **Advanced Scheduling**: Weight-based grouping, consecutive race avoidance, lane optimization
- **Professional Displays**: Tournament standings, bracket visualization, auto-scroll capabilities
- **Broadcast Messaging**: Real-time announcements across all connected displays

---

## 📋 System Requirements

### Core DerbyNet Requirements
- **Web Server**: PHP 7.0+ (Apache recommended)
- **Database**: SQLite or Microsoft Access
- **Client**: Modern web browsers for administration and display

### SBDerbyNet Hardware Components
- **Processing**: Raspberry Pi devices (3B+ or newer) for race coordination
- **Networking**: MQTT broker (Mosquitto recommended), WiFi/Ethernet infrastructure
- **Displays**: HDMI-compatible displays for kiosk systems (Raspberry Pi 4+)
- **Race Hardware**: 
  - ESP32 microcontroller for start detection
  - Toggle switches for finish line detection
  - LED indicators for race status
  - Camera systems for live streaming (optional)

### Network Configuration
- **Subnet**: 192.168.100.x recommended for isolated race network
- **MQTT Broker**: Central message coordination (192.168.100.10 default)
- **Bandwidth**: Sufficient for multiple video streams and real-time messaging

---

## 🚀 Installation & Quick Start

### Core DerbyNet Installation

#### **Option 1: Docker Development (Recommended)**
```bash
# Install Apache Ant
sudo apt-get update && sudo apt-get install ant

# Build the project
ant generated

# Optional: Build timer interfaces
ant timer-in-browser  # Web-based timer
ant timer-jar        # Java timer application

# Run with Docker (replace paths as needed)
docker run --detach -p 80:80 -p 443:443 \
  --volume /path/to/your/data:/var/lib/derbynet \
  --mount type=bind,src=/path/to/repository/website,target=/var/www/html,readonly \
  jeffpiazza/derbynet_server
```

#### **Option 2: Manual Installation**
Refer to installation guides in `docs/` directory:
- **Linux**: Debian/Ubuntu installation guide
- **Windows**: Windows-specific setup instructions  
- **macOS**: Mac installation procedures
- **Docker**: Container deployment guide

### SBDerbyNet Hardware Setup

#### **1. Raspberry Pi Preparation**
```bash
# Flash SD cards with Raspberry Pi OS
# Configure network for 192.168.100.x subnet
# Install required dependencies
sudo apt-get update
sudo apt-get install python3 python3-pip mosquitto mosquitto-clients

# Install Python requirements
pip3 install paho-mqtt psutil RPi.GPIO
```

#### **2. Service Installation**
```bash
# Copy service files to appropriate locations
sudo cp extras/soapbox/infra/*/setup.sh /opt/
sudo chmod +x /opt/setup.sh && /opt/setup.sh

# Enable and start services
sudo systemctl enable derbyrace.service
sudo systemctl enable finishtimer.service
sudo systemctl enable derbydisplay.service
sudo systemctl enable hlsfeed.service

# Start all services
sudo systemctl start derbyrace
sudo systemctl start finishtimer
sudo systemctl start derbydisplay
sudo systemctl start hlsfeed
```

#### **3. Network Configuration**
```bash
# Configure MQTT broker
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

# Test MQTT connectivity
mosquitto_pub -h 192.168.100.10 -t derbynet/test -m "hello"
mosquitto_sub -h 192.168.100.10 -t derbynet/test
```

### Initial System Configuration

1. **Access Web Interface**: Navigate to `http://your-server-ip/setup.php`
2. **Database Setup**: Create or select database location
3. **Race Configuration**: Import racers or create fake roster for testing
4. **Hardware Setup**: Configure timer connections and device assignments
5. **Display Setup**: Assign kiosk displays and configure scenes

---

## 🎮 Race Management Features

### **Comprehensive Racer Management**
- **Registration System**: Import from CSV or manual entry with photo support
- **Check-in Process**: Day-of-race attendance tracking with inspection validation
- **Class Organization**: Age-based groupings with automatic tournament detection
- **Car Management**: Weight tracking, numbering system, inspection status

### **Advanced Scheduling Engine**
- **Smart Heat Generation**: Weight-based grouping, consecutive race avoidance
- **Elimination Tournaments**: JSON-configured formats with automatic progression
- **Flexible Scheduling**: Support for partial heats, dropout handling, manual overrides
- **Lane Optimization**: Balanced lane usage with bias detection and correction

### **Real-time Race Operations**
- **Live Timing**: Automatic capture from hardware timers with manual override capability
- **Result Tracking**: Instant standings calculation with multiple scoring methods
- **Heat Management**: Automatic progression with coordinator control
- **DNF Support**: Mark individual lanes as "Did Not Finish" (99.999s) from coordinator page, automatically detected by race server within 1 second
- **Broadcast Messaging**: Instant announcements to all displays

### **Professional Display System**
- **Tournament Standings**: Real-time elimination bracket visualization
- **Race Results**: Heat-by-heat result displays with advancement indicators
- **Slideshow Management**: Sponsor displays, intermission content, general announcements
- **Scene Control**: Centralized display management with one-click scene changes

---

## 🏆 Elimination Tournament System

### **Tournament Formats**

#### **Ages 6-8 (4 Rounds)**
- **Preliminary**: 3 races per racer (1 per lane), top 27 advance by total time
- **Quarter Finals**: 1 race per racer, top 9 advance by single time
- **Semi-Finals**: 1 race per racer, top 3 advance by single time
- **Finals**: 1 race, final placement by finish order

#### **Ages 9-11 (4 Rounds)**
- **Preliminary**: 3 races per racer (1 per lane), top 27 advance by total time
- **Quarter Finals**: 1 race per racer, top 9 advance by single time
- **Semi-Finals**: 1 race per racer, top 3 advance by single time
- **Finals**: 1 race, final placement by finish order

#### **Ages 12-14 (3 Rounds)**
- **Preliminary**: 3 races per racer (1 per lane), top 9 advance by total time
- **Semi-Finals**: 1 race per racer, top 3 advance by single time
- **Finals**: 1 race, final placement by finish order

### **Key Features**
- **Automatic Detection**: Tournament format applied based on class name patterns
- **State Persistence**: Tournament progress survives system restarts
- **Dropout Handling**: Partial heats with fewer racers when participants withdraw
- **Heat Optimization**: Prioritized spacing between races for adequate rest periods
- **Professional Displays**: Real-time standings with advancement indicators

### **Tournament Setup (Racing Groups Page)**
The Racing Groups page (`racing-groups.php`) includes a Tournament Setup section for initializing elimination tournaments:

- **Format Selection**: Choose from available tournament configurations via dropdown
- **Class-to-Age-Group Assignment**: Table showing all classes with age group selectors
- **Auto-Detection**: Classes are automatically matched to age groups based on name patterns (e.g., "Ages 6-8" matches the 6-8 age group)
- **One-Click Initialization**: Initialize tournament for each class, creating rounds and schedule structure
- **Status Persistence**: Tournament status (round progress, locked state) persists across page reloads
- **Visual Indicators**: Active tournaments show current round (e.g., "Round 1/4") and are locked from re-initialization

### **Configuration Editor (`elimination-config-editor.php`)**
A dedicated editor for creating and modifying tournament configurations:

- **Collapsible Sections**: Age groups and rounds collapse/expand for easy navigation (collapsed by default)
- **Auto-Generated Keys**: Age group keys are automatically generated from class names
- **Round Numbering**: Round numbers are automatically prepended to round names
- **Field-Level Help**: Hover tooltips explain each configuration field
- **Live Validation**: Real-time feedback on configuration errors
- **Clone/Delete**: Easily duplicate or remove configurations
- **Lock Protection**: Configurations in active use cannot be modified

### **Configuration Management**
- **JSON-Based**: Hardcoded tournament formats for reliability and predictability
- **Pattern Matching**: Automatic detection based on class names (e.g., "Ages 6-8", "6-8", "6 to 8")
- **Validation**: Comprehensive configuration validation preventing tournament errors
- **Audit Trail**: Complete advancement history with scoring details
- **Flexible Sizing**: `advance_count` acts as a maximum - smaller tournaments automatically advance all racers when below threshold (see [Configuration README](website/inc/elimination-configs/README.md) for details)

---

## 📱 Kiosk Display System

### **Core Display Types**
- **Now Racing**: Current heat information with real-time updates
- **Standings**: Overall race standings with class breakdowns
- **Results by Racer**: Individual racer performance history
- **Awards Presentation**: Ceremony display with winner announcements

### **Elimination Tournament Displays**
- **Tournament Standings**: Professional bracket visualization with gradient styling
- **Round Results**: Heat-by-heat elimination results with advancement indicators
- **Auto-refresh**: 5-second update cycles for real-time information
- **Auto-scroll**: Smooth scrolling for long racer lists with 30-second cycles

### **Slideshow System**
- **General Slideshow**: Main directory images with title slide priority
- **Sponsor Displays**: Dedicated sponsor subdirectory with custom timing
- **Intermission Content**: Safety messages and rules during race breaks
- **Configurable Timing**: Per-slideshow type duration settings

### **Broadcast Messaging**
- **Instant Announcements**: Emergency messages to all displays within 5 seconds
- **Prominent Overlay**: White text on black background covering top 20% of screen
- **Auto-expiring**: Configurable duration (1-300 seconds) with automatic cleanup
- **Permission-based**: Coordinator-level access required for message broadcast

### **Scene Management**
- **Centralized Control**: One-click scene changes from coordinator page
- **Predefined Scenes**: Common display configurations for different race phases
- **Real-time Updates**: Immediate scene changes across all connected displays
- **Coordinator Integration**: Scene selector integrated into race management interface

---

## 🛠️ Hardware Integration

### **MQTT Communication Architecture**
- **Central Broker**: Mosquitto MQTT broker for message coordination
- **Device Discovery**: Automatic registration and health monitoring
- **Message Persistence**: Offline storage during network interruptions
- **QoS Levels**: Appropriate quality of service for different message types

### **Finish Timer System**
- **Hardware Platform**: Raspberry Pi with DerbyNet PCB v1
- **Detection Method**: Physical toggle switches for reliable finish detection
- **Status Indication**: RGB LED showing connection and race status
- **Display Integration**: 4-digit 7-segment display for diagnostics and lane numbers
- **Network Resilience**: Automatic reconnection with exponential backoff

### **Start Timer System**
- **Hardware Platform**: ESP32 microcontroller for start signal detection
- **Signal Broadcasting**: MQTT message distribution to all race components
- **Battery Operation**: Portable deployment for start line positioning
- **Wireless Communication**: WiFi connectivity to race network
- **Manual Start Fallback**: When hardware start timer is unavailable, the Race Coordinator page displays a green "Start" button in the Timer Status table. Clicking this button publishes an MQTT GO signal to `derbynet/device/manualstart/state`, ensuring the race server records the start time for accurate elapsed time calculations. Requires `mosquitto_pub` on the web server.

### **Video Streaming System**
- **Camera Integration**: RTSP camera support with automatic HLS conversion
- **Stream Management**: Nginx-based serving with segment cleanup
- **Multi-camera Support**: Configurable camera positions and feeds
- **Replay Capability**: Race event recording and playback functionality

### **Display Management**
- **Centralized Control**: Python-based display coordination
- **Error Handling**: Automatic recovery from display failures
- **Status Monitoring**: Health reporting and diagnostic information
- **Content Synchronization**: Real-time updates across all display nodes

---

## 🔧 Testing & Quality Assurance

### **Core DerbyNet Testing**
```bash
# Navigate to testing directory
cd testing/

# Run basic system tests
./test-basic-racing.sh
./test-elimination-system.sh
./test-photo-upload.sh

# Database and schema validation
./test-database-schema.sh
./test-permissions.sh
```

### **SBDerbyNet Hardware Testing**
```bash
# Comprehensive system test
python3 extras/soapbox/infra/server/simulate_racing.py

# Individual component tests
python3 testing/test_mqtt_communication.py
python3 testing/test_finish_timer.py
python3 testing/test_display_system.py

# Network resilience testing
python3 testing/network_resilience_test.py
```

### **Race Simulation System**
- **Complete Race Simulation**: End-to-end race scenarios with realistic timing
- **Hardware Simulation**: Mock hardware responses for testing without physical devices
- **Load Testing**: Multiple concurrent races and high racer counts
- **Edge Case Testing**: Dropout scenarios, network failures, timing conflicts

### **Quality Metrics**
- **Code Coverage**: Comprehensive test coverage for critical race management functions
- **Performance Testing**: Response time validation under race day load conditions
- **Reliability Testing**: 24-hour continuous operation validation
- **Security Testing**: Input validation and permission boundary testing

---

## 📚 Comprehensive Documentation

### **User Guides**
- **Race Director Guide**: Complete race day operations manual
- **Setup Instructions**: Step-by-step installation and configuration
- **Troubleshooting Guide**: Common issues and resolution procedures
- **Feature Reference**: Detailed feature documentation with examples

### **Technical Documentation**
- **API Reference**: Complete MQTT API and HTTP endpoint documentation
- **Database Schema**: Table structure and relationship documentation
- **Hardware Specifications**: Detailed hardware requirements and pinout information
- **Architecture Overview**: System design and component interaction diagrams

### **Developer Resources**
- **Contributing Guidelines**: Code standards and contribution procedures
- **Testing Framework**: Test suite documentation and best practices
- **Deployment Guide**: Production deployment recommendations
- **Performance Optimization**: Tuning guidelines for large-scale events

---

## 🛡️ Security & Reliability

### **Permission System**
- **Role-based Access**: Granular permissions for different user types
- **Session Management**: Secure authentication with timeout handling
- **API Protection**: Endpoint protection with proper authorization checks
- **Audit Logging**: Complete activity logging for security monitoring

### **Data Protection**
- **Database Backup**: Automatic backup creation with restore procedures
- **Race Data Integrity**: Transaction-based updates with rollback capability
- **Photo Management**: Secure image storage with access controls
- **Export Capabilities**: Complete data export for record keeping

### **Network Security**
- **Isolated Network**: Recommendation for dedicated race network
- **MQTT Security**: Username/password authentication for MQTT broker
- **Encrypted Communications**: TLS support for sensitive communications
- **Access Controls**: Network-level restrictions for race components

### **Reliability Features**
- **Automatic Recovery**: System restart and reconnection handling
- **Graceful Degradation**: Continued operation during component failures
- **Health Monitoring**: Proactive monitoring with alert capabilities
- **Backup Systems**: Redundant timer and display capabilities

---

## 🤝 Contributing & Support

### **Getting Started with Development**
1. **Fork Repository**: Create your own fork for development
2. **Development Environment**: Set up local testing environment
3. **Test Suite**: Run comprehensive tests before submitting changes
4. **Documentation**: Update documentation for new features

### **Contribution Guidelines**
- **Code Standards**: Follow existing code style and conventions
- **Testing Requirements**: All new features must include appropriate tests
- **Documentation**: Update relevant documentation for changes
- **Backward Compatibility**: Maintain compatibility with existing installations

### **Bug Reports & Feature Requests**
- **Issue Templates**: Use provided templates for consistent reporting
- **Detailed Information**: Include system information and reproduction steps
- **Test Cases**: Provide specific examples and expected behavior
- **Screenshots**: Include visual documentation for UI-related issues

### **Community Support**
- **Discussion Forum**: Community support and feature discussions
- **Documentation Wiki**: Collaborative documentation improvement
- **Best Practices**: Shared experiences and optimization techniques
- **Event Showcases**: Real-world implementation examples and success stories

---

## 📄 License & Credits

### **Licensing**
This project is released under the **MIT License**, maintaining compatibility with the original DerbyNet project. See the `MIT-LICENSE.txt` file for complete license details.

### **Original Project Credits**
- **DerbyNet**: Created by Jeff Piazza and the DerbyNet community
- **Website**: [https://derbynet.org](https://derbynet.org)
- **Repository**: [https://github.com/jeffpiazza/derbynet](https://github.com/jeffpiazza/derbynet)

### **SBDerbyNet Development**
- **Enhancement Development**: Extensive modifications for soapbox derby racing
- **Hardware Integration**: Custom hardware stack for outdoor racing events
- **Tournament System**: JSON-based elimination tournament framework
- **Professional Displays**: Modern UI/UX for race visualization

### **Acknowledgments**
- **DerbyNet Community**: Foundation and ongoing development of core race management system
- **Soapbox Derby Community**: Requirements gathering and real-world testing feedback
- **Open Source Contributors**: Various libraries and tools that make this system possible

---

## 🔗 Quick Links

### **Essential Documentation**
- [Installation Guide](docs/) - Platform-specific setup instructions
- [Race Director Manual](extras/soapbox/doc/SoapboxDerby_Test_Guide.md) - Complete operations guide
- [Hardware Setup](extras/soapbox/infra/) - Component installation and configuration
- [Troubleshooting](extras/soapbox/doc/HLS_REPLAY_DOCUMENTATION.md#comprehensive-troubleshooting) - Common issues and solutions

### **Technical References**
- [MQTT API Documentation](extras/soapbox/doc/MQTT_API.md) - Message protocol specification
- [Database Schema](website/sql/) - Table structure and relationships
- [Elimination Tournaments](website/inc/elimination-configs/) - Tournament configuration examples
- [Kiosk System](website/kiosks/) - Display configuration and customization

### **Development Resources**
- [Contributing Guidelines](CONTRIBUTING.md) - Code standards and procedures
- [Testing Framework](testing/) - Test suite and validation procedures
- [API Reference](website/ajax/) - HTTP endpoint documentation
- [Hardware Specifications](extras/soapbox/infra/finishtimer/README.md) - Detailed hardware requirements

**Ready to get started?** Begin with the [Installation Guide](docs/) and join the growing community of race directors using SBDerbyNet for professional soapbox derby events!