# ESP32 BetaBrite LED Sign Controller - Implementation Guide

**Version 1.0.0**

Complete reference for implementing a BetaBrite LED sign controller on ESP32 that integrates with the Alert Manager system.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [MQTT Communication Protocol](#mqtt-communication-protocol)
3. [Alert Message Format](#alert-message-format)
4. [BetaBrite Protocol Reference](#betabrite-protocol-reference)
5. [Configuration Mapping](#configuration-mapping)
6. [ESP32 Implementation Guide](#esp32-implementation-guide)
7. [Code Examples](#code-examples)
8. [Zone Management](#zone-management)
9. [Priority and Duration Handling](#priority-and-duration-handling)
10. [Testing and Validation](#testing-and-validation)

---

## System Architecture

### Overview

The Alert Manager system routes alerts to BetaBrite LED signs via MQTT. The ESP32 controller subscribes to zone-specific topics, receives JSON-formatted alert messages with display configurations, and translates them into BetaBrite Alpha Protocol commands.

```
Alert Source → Alert Manager → MQTT Broker → ESP32 Controller → BetaBrite Sign
                (Python)         (TLS 1.3)      (Subscribe)      (Serial/RS-232)
```

### Components

- **Alert Manager**: Python service that routes alerts to pathways
- **MQTT Broker**: Mosquitto broker with TLS certificate authentication
- **ESP32 Controller**: Subscribes to MQTT, translates JSON to BetaBrite protocol
- **BetaBrite Sign**: Receives Alpha Protocol commands via RS-232

### Communication Flow

1. Alert arrives at Alert Manager (HTTP/MQTT/SNMP)
2. Alert Manager applies routing rules
3. LED Sign Pathway processes alert and publishes to `ledSign/{zone}/message`
4. ESP32 receives JSON message with `display_config` and `message`
5. ESP32 maps JSON config to BetaBrite protocol codes
6. ESP32 sends Alpha Protocol command to BetaBrite sign

---

## MQTT Communication Protocol

### Broker Connection Details

**Production (External):**
- **Host**: `alert.d-t.pw`
- **Port**: `42690`
- **Protocol**: TLS 1.3 with mutual certificate authentication
- **Client Certificate**: Required (ca.crt, client.crt, client.key)

**Development (Local):**
- **Host**: `localhost` or `alert.d-t.pw`
- **Port**: `46942`
- **Protocol**: TLS 1.3 with mutual certificate authentication
- **Client Certificate**: Required

### MQTT Topics

#### Subscribe Topics (ESP32)
- **`ledSign/{zone}/message`** - Alert messages for specific zone
  - Example: `ledSign/kitchen/message`
  - Example: `ledSign/living_room/message`
  - Example: `ledSign/office/message`

#### Publish Topics (Optional - Status Reporting)
- **`ledSign/{zone}/status`** - Sign status updates
- **`ledSign/{zone}/health`** - Health check responses

### Connection Requirements

**Client ID Format**: `esp32-betabrite-{zone}-{mac_address}`
- Example: `esp32-betabrite-kitchen-a1b2c3d4e5f6`

**QoS Level**: 1 (at least once delivery)

**Clean Session**: False (persistent session for reliability)

**Keepalive**: 60 seconds

**Last Will Testament** (recommended):
```json
{
  "topic": "ledSign/{zone}/status",
  "message": "{\"status\": \"offline\", \"timestamp\": 0}",
  "qos": 1,
  "retain": true
}
```

### Certificate Files Required

1. **ca.crt** - Certificate Authority root certificate
2. **client.crt** - Client certificate (unique per device)
3. **client.key** - Client private key

Store in SPIFFS or LittleFS on ESP32.

---

## Alert Message Format

### JSON Message Structure

Every message published to `ledSign/{zone}/message` follows this format:

```json
{
  "timestamp": 1704045600,
  "level": "warning",
  "category": "security",
  "title": "Motion Detected",
  "message": "Front door motion sensor triggered",
  "display_config": {
    "mode": "flash",
    "mode_code": "c",
    "special_effect": "starburst",
    "effect_code": "7",
    "color": "red",
    "color_code": "1",
    "character_set": "10high",
    "charset_code": "6",
    "position": "fill",
    "position_code": "0",
    "speed": 5,
    "speed_code": "\\031",
    "priority": true,
    "duration": 60
  },
  "source": "security-system-01",
  "zone": "kitchen"
}
```

### Field Descriptions

#### Core Alert Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `timestamp` | integer | Unix epoch seconds | `1704045600` |
| `level` | string | Alert severity | `"critical"`, `"warning"`, `"info"` |
| `category` | string | Alert category | `"security"`, `"weather"`, `"news"` |
| `title` | string | Short alert title | `"Motion Detected"` |
| `message` | string | Display message text | `"Front door motion sensor triggered"` |
| `source` | string | Alert source identifier | `"security-system-01"` |
| `zone` | string | Target zone name | `"kitchen"` |

#### Alert Levels

| Level | Priority | Typical Display |
|-------|----------|----------------|
| `critical` | Highest | Flash red, large text, priority interrupt |
| `warning` | High | Amber/orange, prominent display |
| `notice` | Medium | Standard display with emphasis |
| `info` | Normal | Green, standard scrolling/rotation |
| `debug` | Lowest | Dim colors, bottom line |

#### Alert Categories

| Category | Theme | Typical Effects |
|----------|-------|----------------|
| `security` | Urgent, attention-grabbing | Starburst, bomb, flash, red |
| `system` | Professional, informational | Interlock, sparkle, amber |
| `network` | Technical, continuous | Slide, scroll, yellow |
| `weather` | Atmospheric, contextual | Snow, spray, autocolor |
| `automation` | Welcoming, smooth | Welcome, wipein, green |
| `personal` | Playful, colorful | Twinkle, rainbow, fancy fonts |
| `news` | Dynamic, prominent | Newsflash, trumpet, sparkle |
| `application` | Simple, clear | Hold, rotate, standard fonts |

### Display Configuration Object

The `display_config` object contains **both human-readable names and BetaBrite protocol codes**. The ESP32 should use the `*_code` fields directly.

#### Display Config Fields

| Field | Type | Description | Values |
|-------|------|-------------|--------|
| `mode` | string | Display mode name | `"flash"`, `"scroll"`, `"explode"` |
| `mode_code` | string | BetaBrite mode code | `"c"`, `"m"`, `"u"` |
| `special_effect` | string | Effect name | `"starburst"`, `"bomb"`, `"twinkle"` |
| `effect_code` | string | BetaBrite effect code | `"7"`, `"Z"`, `"0"` |
| `color` | string | Color name | `"red"`, `"green"`, `"amber"` |
| `color_code` | string | BetaBrite color code | `"1"`, `"2"`, `"3"` |
| `character_set` | string | Font name | `"7high"`, `"10high"`, `"7highfancy"` |
| `charset_code` | string | BetaBrite charset code | `"3"`, `"6"`, `"5"` |
| `position` | string | Position name | `"fill"`, `"topline"`, `"midline"` |
| `position_code` | string | BetaBrite position code | `"0"`, `"\""`, `" "` |
| `speed` | integer | Speed level (1-5) | `1` (slowest) to `5` (fastest) |
| `speed_code` | string | BetaBrite speed code | `"\\025"` to `"\\031"` |
| `priority` | boolean | Interrupt rotation | `true`, `false` |
| `duration` | integer | Display seconds | `60`, `30`, `15` |

**IMPORTANT**: The Alert Manager Python pathway pre-calculates all `*_code` fields. The ESP32 should extract and use these codes directly without re-mapping.

---

## BetaBrite Protocol Reference

### Alpha Protocol Overview

BetaBrite signs use the Alpha Protocol for communication over RS-232 serial:
- **Baud Rate**: 9600 bps
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 1
- **Flow Control**: None

### Command Structure

```
<NUL><NUL><NUL><NUL><NUL><SOH><Z><00><TYPE><COMMAND><STX><FILE><CTRL_CODES><TEXT><ETX>
```

**Control Characters:**
- `<NUL>` (0x00) - Null padding (5 bytes)
- `<SOH>` (0x01) - Start of Header
- `<STX>` (0x02) - Start of Text
- `<ETX>` (0x03) - End of Text
- `<Z>` (0x5A) - Sign address (Z = broadcast)
- `<00>` (0x30 0x30) - Sign type code

### Display Modes

| Mode Name | Code | Description | Use Case |
|-----------|------|-------------|----------|
| `rotate` | `a` | Cycles through text files | Default continuous display |
| `hold` | `b` | Static display | Important messages |
| `flash` | `c` | Text blinks on/off | Critical alerts |
| `scroll` | `m` | Horizontal scrolling | Long messages |
| `auto` | `o` | Sign determines method | General purpose |
| `rollup` | `e` | Rolls up from bottom | Smooth vertical |
| `rolldown` | `f` | Rolls down from top | Smooth vertical |
| `rollleft` | `g` | Rolls in from right | Horizontal sliding |
| `rollright` | `h` | Rolls in from left | Horizontal sliding |
| `rollin` | `p` | Rolls in from edges | Converging motion |
| `rollout` | `q` | Rolls out to edges | Diverging motion |
| `wipeup` | `i` | Wipes upward | Clean vertical reveal |
| `wipedown` | `j` | Wipes downward | Clean vertical reveal |
| `wipeleft` | `k` | Wipes leftward | Clean horizontal reveal |
| `wiperight` | `l` | Wipes rightward | Clean horizontal reveal |
| `wipein` | `r` | Wipes in from edges | Converging reveal |
| `wipeout` | `s` | Wipes out to edges | Diverging reveal |
| `compressedrotate` | `t` | Compact rotation | Space-efficient |
| `explode` | `u` | Text explodes outward | High-impact |
| `clock` | `v` | Time/date display | Timestamp info |
| `special` | `n` | Enables special effects | Enhanced visuals |
| `newsflash` | `A` | Breaking news style | Urgent news |

### Special Effects

| Effect Name | Code | Description | Theme |
|-------------|------|-------------|-------|
| `twinkle` | `0` | Stars twinkling | Gentle, pleasant |
| `sparkle` | `1` | Sparkling lights | Celebratory |
| `snow` | `2` | Falling snow | Weather, winter |
| `interlock` | `3` | Interlocking pattern | Mechanical |
| `switch` | `4` | Switching pattern | Toggle |
| `slide` | `5` | Sliding motion | Smooth directional |
| `spray` | `6` | Water spray | Dynamic, energetic |
| `starburst` | `7` | Explosive star | Dramatic |
| `welcome` | `8` | Welcome message | Greeting |
| `slots` | `9` | Slot machine | Random, gaming |
| `newsflash` | `A` | Breaking news | Urgent news |
| `trumpet` | `B` | Trumpet fanfare | Announcement |
| `cyclecolors` | `C` | Rotates colors | Dynamic |
| `thankyou` | `S` | Thank you | Gratitude |
| `nosmoke` | `U` | No smoking symbol | Warning |
| `nodrive` | `V` | Don't drink & drive | Safety |
| `fishimal` | `W` | Fish animation | Playful |
| `fireworks` | `X` | Fireworks | Celebration |
| `turballoon` | `Y` | Turbulent balloon | Floating |
| `bomb` | `Z` | Explosion | Extreme urgency |

### Colors

| Color Name | Code | Description | Best For |
|------------|------|-------------|----------|
| `red` | `1` | Bright red | Critical alerts |
| `green` | `2` | Bright green | Success, normal |
| `amber` | `3` | Amber/orange | Warnings |
| `dimred` | `4` | Darker red | Subdued alerts |
| `dimgreen` | `5` | Darker green | Background status |
| `brown` | `6` | Brown/dark amber | Neutral info |
| `orange` | `7` | Orange | Moderate warnings |
| `yellow` | `8` | Bright yellow | Attention, info |
| `rainbow1` | `9` | First rainbow | Multi-color cycling |
| `rainbow2` | `A` | Second rainbow | Alternative rainbow |
| `colormix` | `B` | Mixed colors | Varied display |
| `autocolor` | `C` | Automatic | Sign determines |

### Character Sets

| Set Name | Code | Description | Height | Style |
|----------|------|-------------|--------|-------|
| `5high` | `1` | Basic 5-pixel | Small | Simple |
| `5stroke` | `2` | 5-pixel stroke | Small | Outlined |
| `7high` | `3` | Standard 7-pixel | Medium | Clean |
| `7stroke` | `4` | 7-pixel stroke | Medium | Outlined |
| `7highfancy` | `5` | Decorative 7-pixel | Medium | Stylized |
| `10high` | `6` | Large 10-pixel | Large | Bold |
| `7shadow` | `7` | Shadow effect | Medium | Dimensional |
| `fhighfancy` | `8` | Full height decorative | Large | Elegant |
| `fhigh` | `9` | Full height standard | Large | Maximum size |
| `7shadowfancy` | `:` | Shadow + decoration | Medium | Ornate |
| `5wide` | `;` | 5-pixel wide | Small | Compact wide |
| `7wide` | `<` | 7-pixel wide | Medium | Standard wide |
| `7widefancy` | `=` | Decorative wide | Medium | Stylized wide |
| `5widestroke` | `>` | 5-pixel wide outline | Small | Outlined wide |

### Positions

| Position Name | Code | Description | Usage |
|---------------|------|-------------|-------|
| `topline` | `"` | Upper portion | Headers, titles |
| `midline` | ` ` | Center (space) | Main content |
| `botline` | `&` | Lower portion | Status, footers |
| `fill` | `0` | Full display area | Maximum visibility |
| `left` | `1` | Left-aligned | Standard text |
| `right` | `2` | Right-aligned | Numbers, timestamps |

### Speed Codes

| Speed Level | Code | Description | Rate |
|-------------|------|-------------|------|
| 1 | `\025` | Slowest | Deliberate, readable |
| 2 | `\026` | Slow | Comfortable reading |
| 3 | `\027` | Medium | Standard pace |
| 4 | `\030` | Fast | Quick updates |
| 5 | `\031` | Fastest | Rapid attention |

---

## Configuration Mapping

### JSON to BetaBrite Protocol Translation

The Alert Manager pathway pre-calculates all protocol codes and includes them in the `display_config` object. The ESP32 should extract these codes directly.

#### Example: Critical Security Alert

**Incoming JSON:**
```json
{
  "level": "critical",
  "category": "security",
  "title": "Intruder Alert",
  "message": "Motion detected at front door",
  "display_config": {
    "mode": "flash",
    "mode_code": "c",
    "special_effect": "bomb",
    "effect_code": "Z",
    "color": "red",
    "color_code": "1",
    "character_set": "10high",
    "charset_code": "6",
    "position": "fill",
    "position_code": "0",
    "speed": 5,
    "speed_code": "\\031",
    "priority": true,
    "duration": 60
  }
}
```

**BetaBrite Command:**
```
<NUL><NUL><NUL><NUL><NUL><SOH>Z00<TYPE>A<STX>A<MODE_CODE><POSITION_CODE><COLOR_CODE><CHARSET_CODE><EFFECT_CODE><SPEED_CODE>Intruder Alert: Motion detected at front door<ETX>
```

**With actual codes:**
```
\x00\x00\x00\x00\x00\x01Z00AA\x02Ac016Z\031Intruder Alert: Motion detected at front door\x03
```

### Recommended Fallback Defaults

If any `display_config` field is missing, use these defaults:

```c
const char* DEFAULT_MODE_CODE = "a";        // rotate
const char* DEFAULT_COLOR_CODE = "2";       // green
const char* DEFAULT_CHARSET_CODE = "3";     // 7high
const char* DEFAULT_POSITION_CODE = " ";    // midline
const char* DEFAULT_SPEED_CODE = "\027";    // medium (3)
const char* DEFAULT_EFFECT_CODE = NULL;     // no special effect
```

---

## ESP32 Implementation Guide

### Required Libraries

```cpp
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <SPIFFS.h>
```

### Hardware Serial Configuration

**For BetaBrite RS-232 Communication:**
```cpp
#define BETABRITE_SERIAL Serial2
#define BETABRITE_BAUD 9600
#define BETABRITE_RX 16
#define BETABRITE_TX 17

void setup() {
  BETABRITE_SERIAL.begin(BETABRITE_BAUD, SERIAL_8N1, BETABRITE_RX, BETABRITE_TX);
}
```

### MQTT Client Setup

```cpp
WiFiClientSecure espClient;
PubSubClient mqttClient(espClient);

// Zone configuration
const char* ZONE_NAME = "kitchen";
const char* MQTT_TOPIC = "ledSign/kitchen/message";

// MQTT broker
const char* MQTT_BROKER = "alert.d-t.pw";
const int MQTT_PORT = 42690;

// Certificate paths (stored in SPIFFS)
const char* CA_CERT_PATH = "/certs/ca.crt";
const char* CLIENT_CERT_PATH = "/certs/client.crt";
const char* CLIENT_KEY_PATH = "/certs/client.key";
```

### Certificate Loading

```cpp
bool loadCertificates() {
  if (!SPIFFS.begin(true)) {
    Serial.println("Failed to mount SPIFFS");
    return false;
  }

  // Load CA certificate
  File caFile = SPIFFS.open(CA_CERT_PATH, "r");
  if (!caFile) {
    Serial.println("Failed to open CA cert");
    return false;
  }
  String caCert = caFile.readString();
  caFile.close();

  // Load client certificate
  File certFile = SPIFFS.open(CLIENT_CERT_PATH, "r");
  if (!certFile) {
    Serial.println("Failed to open client cert");
    return false;
  }
  String clientCert = certFile.readString();
  certFile.close();

  // Load client key
  File keyFile = SPIFFS.open(CLIENT_KEY_PATH, "r");
  if (!keyFile) {
    Serial.println("Failed to open client key");
    return false;
  }
  String clientKey = keyFile.readString();
  keyFile.close();

  // Configure WiFiClientSecure
  espClient.setCACert(caCert.c_str());
  espClient.setCertificate(clientCert.c_str());
  espClient.setPrivateKey(clientKey.c_str());

  return true;
}
```

### MQTT Connection

```cpp
void connectMQTT() {
  while (!mqttClient.connected()) {
    Serial.println("Connecting to MQTT...");

    // Generate client ID
    String clientId = "esp32-betabrite-";
    clientId += ZONE_NAME;
    clientId += "-";
    clientId += String(WiFi.macAddress());
    clientId.replace(":", "");

    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("MQTT connected");
      mqttClient.subscribe(MQTT_TOPIC, 1);
      Serial.print("Subscribed to: ");
      Serial.println(MQTT_TOPIC);
    } else {
      Serial.print("MQTT connection failed, rc=");
      Serial.println(mqttClient.state());
      delay(5000);
    }
  }
}
```

### Message Parsing

```cpp
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message received on topic: ");
  Serial.println(topic);

  // Parse JSON
  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, payload, length);

  if (error) {
    Serial.print("JSON parse error: ");
    Serial.println(error.c_str());
    return;
  }

  // Extract alert fields
  const char* title = doc["title"];
  const char* message = doc["message"];
  const char* level = doc["level"];
  const char* category = doc["category"];

  // Extract display config
  JsonObject displayConfig = doc["display_config"];

  const char* modeCode = displayConfig["mode_code"] | "a";
  const char* colorCode = displayConfig["color_code"] | "2";
  const char* charsetCode = displayConfig["charset_code"] | "3";
  const char* positionCode = displayConfig["position_code"] | " ";
  const char* speedCode = displayConfig["speed_code"] | "\027";
  const char* effectCode = displayConfig["effect_code"] | nullptr;
  bool priority = displayConfig["priority"] | false;
  int duration = displayConfig["duration"] | 15;

  // Build display text
  String displayText = String(title) + ": " + String(message);

  // Send to BetaBrite
  sendToBetaBrite(displayText.c_str(), modeCode, colorCode, charsetCode,
                  positionCode, speedCode, effectCode, priority, duration);
}
```

### BetaBrite Command Generation

```cpp
void sendToBetaBrite(const char* text, const char* mode, const char* color,
                     const char* charset, const char* position,
                     const char* speed, const char* effect,
                     bool priority, int duration) {

  // Command structure
  String command = "";

  // Null padding (5 bytes)
  for (int i = 0; i < 5; i++) {
    command += (char)0x00;
  }

  // SOH + Address + Type
  command += (char)0x01;  // SOH
  command += 'Z';         // Broadcast address
  command += '0';         // Type code
  command += '0';         // Type code

  // Command type (A = Write Text File)
  command += 'A';
  command += 'A';         // File label

  // STX
  command += (char)0x02;
  command += 'A';         // File label for content

  // Display mode
  command += mode[0];

  // Position
  command += position[0];

  // Color
  command += color[0];

  // Character set
  command += charset[0];

  // Special effect (if present)
  if (effect != nullptr && strlen(effect) > 0) {
    command += effect[0];
  }

  // Speed
  command += speed;

  // Message text
  command += text;

  // ETX
  command += (char)0x03;

  // Send to sign
  BETABRITE_SERIAL.print(command);

  Serial.println("Sent to BetaBrite:");
  Serial.print("  Mode: ");
  Serial.println(mode);
  Serial.print("  Color: ");
  Serial.println(color);
  Serial.print("  Text: ");
  Serial.println(text);

  // Handle priority messages with duration
  if (priority && duration > 0) {
    // Schedule return to normal rotation after duration
    // Implementation depends on your task scheduler
    scheduleCancelPriority(duration);
  }
}
```

### Priority Message Handling

```cpp
unsigned long priorityEndTime = 0;
bool priorityActive = false;

void scheduleCancelPriority(int duration) {
  priorityEndTime = millis() + (duration * 1000);
  priorityActive = true;
  Serial.print("Priority message scheduled for ");
  Serial.print(duration);
  Serial.println(" seconds");
}

void checkPriorityTimeout() {
  if (priorityActive && millis() >= priorityEndTime) {
    cancelPriorityMessage();
    priorityActive = false;
  }
}

void cancelPriorityMessage() {
  // Send command to cancel priority and return to rotation
  String command = "";

  // Null padding
  for (int i = 0; i < 5; i++) {
    command += (char)0x00;
  }

  command += (char)0x01;  // SOH
  command += 'Z';         // Broadcast
  command += '0';
  command += '0';
  command += 'A';         // Write command
  command += 'A';         // File label
  command += (char)0x02;
  command += 'A';
  command += 'a';         // Rotate mode (normal rotation)
  command += ' ';         // Midline
  command += '2';         // Green
  command += '3';         // 7high
  command += (char)0x03;

  BETABRITE_SERIAL.print(command);
  Serial.println("Priority message cancelled, returned to rotation");
}
```

### Main Loop

```cpp
void loop() {
  if (!mqttClient.connected()) {
    connectMQTT();
  }
  mqttClient.loop();

  // Check priority timeout
  checkPriorityTimeout();

  // Other tasks...
}
```

---

## Code Examples

### Complete Minimal Example

```cpp
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* WIFI_SSID = "your-ssid";
const char* WIFI_PASSWORD = "your-password";

// MQTT configuration
const char* MQTT_BROKER = "alert.d-t.pw";
const int MQTT_PORT = 42690;
const char* ZONE_NAME = "kitchen";
const char* MQTT_TOPIC = "ledSign/kitchen/message";

// Serial for BetaBrite
#define BETABRITE_SERIAL Serial2

WiFiClientSecure espClient;
PubSubClient mqttClient(espClient);

void setup() {
  Serial.begin(115200);
  BETABRITE_SERIAL.begin(9600, SERIAL_8N1, 16, 17);

  // Connect WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");

  // Load certificates
  loadCertificates();

  // Setup MQTT
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setBufferSize(2048);

  connectMQTT();
}

void loop() {
  if (!mqttClient.connected()) {
    connectMQTT();
  }
  mqttClient.loop();
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  JsonDocument doc;
  deserializeJson(doc, payload, length);

  String message = String(doc["title"].as<const char*>()) + ": " +
                   String(doc["message"].as<const char*>());

  JsonObject config = doc["display_config"];

  sendToBetaBrite(
    message.c_str(),
    config["mode_code"] | "a",
    config["color_code"] | "2",
    config["charset_code"] | "3",
    config["position_code"] | " ",
    config["speed_code"] | "\027",
    config["effect_code"] | ""
  );
}

void sendToBetaBrite(const char* text, const char* mode, const char* color,
                     const char* charset, const char* position,
                     const char* speed, const char* effect) {
  String cmd = "";

  // Header
  for (int i = 0; i < 5; i++) cmd += (char)0x00;
  cmd += (char)0x01;
  cmd += "Z00AA";
  cmd += (char)0x02;
  cmd += "A";

  // Codes
  cmd += mode[0];
  cmd += position[0];
  cmd += color[0];
  cmd += charset[0];
  if (effect != nullptr && strlen(effect) > 0) cmd += effect[0];
  cmd += speed;

  // Text
  cmd += text;
  cmd += (char)0x03;

  BETABRITE_SERIAL.print(cmd);
}
```

### Multi-Zone Support

```cpp
struct ZoneConfig {
  const char* name;
  const char* topic;
  HardwareSerial* serial;
  int rxPin;
  int txPin;
};

ZoneConfig zones[] = {
  {"kitchen", "ledSign/kitchen/message", &Serial2, 16, 17},
  {"living_room", "ledSign/living_room/message", &Serial1, 9, 10}
};

void setup() {
  for (int i = 0; i < sizeof(zones) / sizeof(ZoneConfig); i++) {
    zones[i].serial->begin(9600, SERIAL_8N1, zones[i].rxPin, zones[i].txPin);
    mqttClient.subscribe(zones[i].topic);
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Find matching zone
  ZoneConfig* zone = nullptr;
  for (int i = 0; i < sizeof(zones) / sizeof(ZoneConfig); i++) {
    if (strcmp(topic, zones[i].topic) == 0) {
      zone = &zones[i];
      break;
    }
  }

  if (zone == nullptr) return;

  // Process message for specific zone
  processAlertForZone(zone, payload, length);
}
```

---

## Zone Management

### Zone Configuration

Each zone represents a physical BetaBrite sign. The Alert Manager routes alerts to specific zones based on:
- **Level filters**: Only display alerts of specific severity levels
- **Category filters**: Only display alerts from specific categories
- **Source filters**: Only display alerts from specific sources

**Example Zone Config (from Alert Manager):**
```json
{
  "zones": {
    "kitchen": {
      "enabled": true,
      "level_filter": ["critical", "warning", "info"],
      "category_filter": ["security", "system", "automation", "personal"],
      "format": "{title}: {message}",
      "max_message_length": 150
    },
    "garage": {
      "enabled": true,
      "level_filter": ["critical"],
      "category_filter": ["security", "automation"],
      "format": "ALERT: {message}",
      "max_message_length": 100
    }
  }
}
```

### ESP32 Zone Implementation

**Single-Zone Controller:**
- Subscribe to one topic: `ledSign/{zone}/message`
- Control one BetaBrite sign
- Simplest implementation

**Multi-Zone Controller:**
- Subscribe to multiple topics: `ledSign/*/message` or specific zones
- Control multiple BetaBrite signs via multiple serial ports
- Requires more GPIO pins and hardware serial ports

---

## Priority and Duration Handling

### Priority Messages

**Priority = true:**
- Interrupts normal display rotation
- Displays immediately
- Overrides current display content
- Remains on screen for specified duration

**Priority = false:**
- Adds to normal rotation
- Does not interrupt current display
- Cycles with other messages

### Duration Implementation

```cpp
struct PriorityMessage {
  unsigned long endTime;
  bool active;
  String originalContent;
};

PriorityMessage priorityMsg = {0, false, ""};

void handlePriorityMessage(const char* text, int duration, bool priority) {
  if (priority) {
    // Save current content (if implementing content restoration)
    priorityMsg.originalContent = getCurrentDisplayContent();

    // Display priority message
    sendToBetaBrite(text, "c", "1", "6", "0", "\031", "7");

    // Schedule end
    priorityMsg.endTime = millis() + (duration * 1000UL);
    priorityMsg.active = true;

    Serial.print("Priority message displayed for ");
    Serial.print(duration);
    Serial.println(" seconds");
  } else {
    // Normal message
    sendToBetaBrite(text, "a", "2", "3", " ", "\027", nullptr);
  }
}

void loop() {
  // Check priority timeout
  if (priorityMsg.active && millis() >= priorityMsg.endTime) {
    // Cancel priority and restore normal display
    sendToBetaBrite("", "a", "2", "3", " ", "\027", nullptr);
    priorityMsg.active = false;

    Serial.println("Priority message expired, returning to normal rotation");
  }

  mqttClient.loop();
}
```

### Duration Guidelines

| Alert Level | Default Duration | Purpose |
|-------------|------------------|---------|
| `critical` | 60 seconds | Maximum visibility for emergencies |
| `warning` | 30 seconds | Sufficient attention for important issues |
| `notice` | 20 seconds | Standard operational events |
| `info` | 15 seconds | Brief informational messages |
| `debug` | 10 seconds | Quick diagnostic info |

**Category Adjustments:**
- Security: Duration × 2.0 (double time for security alerts)
- News: Duration × 1.5 (extended for news content)
- Weather: Duration × 1.2 (slightly longer for weather)
- Personal: Duration × 0.7 (shorter for personal reminders)

---

## Testing and Validation

### Test Message Payloads

#### 1. Critical Security Alert
```bash
mosquitto_pub -h alert.d-t.pw -p 42690 \
  --cafile ca.crt --cert client.crt --key client.key \
  -t "ledSign/kitchen/message" \
  -m '{
    "timestamp": 1704045600,
    "level": "critical",
    "category": "security",
    "title": "Intruder Alert",
    "message": "Motion detected at front door",
    "display_config": {
      "mode_code": "c",
      "color_code": "1",
      "charset_code": "6",
      "position_code": "0",
      "speed_code": "\\031",
      "effect_code": "Z",
      "priority": true,
      "duration": 60
    },
    "zone": "kitchen"
  }'
```

#### 2. Weather Warning
```bash
mosquitto_pub -h alert.d-t.pw -p 42690 \
  --cafile ca.crt --cert client.crt --key client.key \
  -t "ledSign/kitchen/message" \
  -m '{
    "timestamp": 1704045600,
    "level": "warning",
    "category": "weather",
    "title": "Snow Warning",
    "message": "Heavy snow expected tonight, 3-5 inches",
    "display_config": {
      "mode_code": "m",
      "color_code": "3",
      "charset_code": "3",
      "position_code": "\"",
      "speed_code": "\\026",
      "effect_code": "2",
      "priority": false,
      "duration": 45
    },
    "zone": "kitchen"
  }'
```

#### 3. Info Message
```bash
mosquitto_pub -h alert.d-t.pw -p 42690 \
  --cafile ca.crt --cert client.crt --key client.key \
  -t "ledSign/kitchen/message" \
  -m '{
    "timestamp": 1704045600,
    "level": "info",
    "category": "automation",
    "title": "Task Complete",
    "message": "Backup completed successfully",
    "display_config": {
      "mode_code": "a",
      "color_code": "2",
      "charset_code": "3",
      "position_code": " ",
      "speed_code": "\\027",
      "effect_code": "0",
      "priority": false,
      "duration": 15
    },
    "zone": "kitchen"
  }'
```

### Serial Monitor Debugging

Add debug output to trace message flow:

```cpp
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.println("=== MQTT MESSAGE RECEIVED ===");
  Serial.print("Topic: ");
  Serial.println(topic);
  Serial.print("Payload length: ");
  Serial.println(length);

  // Print raw payload
  Serial.print("Raw JSON: ");
  for (unsigned int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();

  // Parse and display
  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, payload, length);

  if (error) {
    Serial.print("ERROR: JSON parse failed - ");
    Serial.println(error.c_str());
    return;
  }

  Serial.println("Parsed fields:");
  Serial.print("  Level: ");
  Serial.println(doc["level"].as<const char*>());
  Serial.print("  Category: ");
  Serial.println(doc["category"].as<const char*>());
  Serial.print("  Title: ");
  Serial.println(doc["title"].as<const char*>());
  Serial.print("  Message: ");
  Serial.println(doc["message"].as<const char*>());

  JsonObject config = doc["display_config"];
  Serial.println("Display config:");
  Serial.print("  Mode: ");
  Serial.println(config["mode_code"].as<const char*>());
  Serial.print("  Color: ");
  Serial.println(config["color_code"].as<const char*>());
  Serial.print("  Priority: ");
  Serial.println(config["priority"].as<bool>() ? "YES" : "NO");
  Serial.print("  Duration: ");
  Serial.println(config["duration"].as<int>());

  // ... continue processing ...
}
```

### BetaBrite Command Validation

Verify BetaBrite commands before sending:

```cpp
void debugBetabriteCommand(const String& command) {
  Serial.println("=== BETABRITE COMMAND ===");
  Serial.print("Length: ");
  Serial.println(command.length());

  Serial.print("Hex: ");
  for (unsigned int i = 0; i < command.length(); i++) {
    Serial.print(command[i], HEX);
    Serial.print(" ");
  }
  Serial.println();

  Serial.print("ASCII: ");
  for (unsigned int i = 0; i < command.length(); i++) {
    char c = command[i];
    if (c >= 32 && c <= 126) {
      Serial.print(c);
    } else {
      Serial.print("<");
      Serial.print((int)c);
      Serial.print(">");
    }
  }
  Serial.println();
  Serial.println("========================");
}
```

### Validation Checklist

- [ ] MQTT connection establishes with TLS certificates
- [ ] Subscription to `ledSign/{zone}/message` succeeds
- [ ] JSON parsing handles all message formats
- [ ] Display config codes are extracted correctly
- [ ] BetaBrite command structure is valid (NUL padding, SOH, STX, ETX)
- [ ] Serial output to BetaBrite works at 9600 baud
- [ ] Priority messages interrupt display
- [ ] Duration timers expire correctly
- [ ] Normal rotation resumes after priority timeout
- [ ] Special effects display correctly
- [ ] Color codes produce expected colors
- [ ] Character sets render properly
- [ ] Speed codes affect animation speed
- [ ] Position codes place text correctly

---

## Additional Resources

### Alert Manager Documentation
- **CLIENTNODE.md** - Client integration guide
- **BETABRITE.md** - Complete BetaBrite protocol reference
- **ALERT_PAYLOAD_SPEC.md** - Alert payload specification

### BetaBrite Protocol
- **Alpha Protocol Specification** - Official BetaBrite documentation
- **Command Reference** - Display modes, effects, colors, character sets

### ESP32 Development
- **ESP-IDF Documentation** - https://docs.espressif.com/projects/esp-idf/
- **Arduino Core for ESP32** - https://github.com/espressif/arduino-esp32
- **PubSubClient Library** - https://github.com/knolleary/pubsubclient
- **ArduinoJson Library** - https://arduinojson.org/

---

## Appendix: Quick Reference Tables

### Alert Level to Display Preset

| Level | Mode | Color | Charset | Position | Speed | Effect | Priority |
|-------|------|-------|---------|----------|-------|--------|----------|
| critical | flash (c) | red (1) | 10high (6) | fill (0) | 5 | bomb (Z) | true |
| warning | scroll (m) | amber (3) | 7high (3) | topline (") | 4 | trumpet (B) | false |
| notice | rotate (a) | yellow (8) | 7high (3) | midline ( ) | 3 | sparkle (1) | false |
| info | rotate (a) | green (2) | 7high (3) | midline ( ) | 2 | twinkle (0) | false |
| debug | hold (b) | dimgreen (5) | 5high (1) | botline (&) | 1 | none | false |

### Category to Effect Theme

| Category | Effect | Color | Mode | Character Set |
|----------|--------|-------|------|---------------|
| security | starburst (7) | red (1) | flash (c) | 10high (6) |
| system | interlock (3) | amber (3) | compressedrotate (t) | 7high (3) |
| network | slide (5) | yellow (8) | scroll (m) | 7high (3) |
| weather | snow (2) | autocolor (C) | scroll (m) | 7high (3) |
| automation | welcome (8) | green (2) | wipein (r) | 5high (1) |
| personal | twinkle (0) | rainbow1 (9) | rollin (p) | 7highfancy (5) |
| news | newsflash (A) | yellow (8) | special (n) | 7high (3) |
| application | none | green (2) | hold (b) | 5high (1) |

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-17
**Maintained By**: Alert Manager Project
