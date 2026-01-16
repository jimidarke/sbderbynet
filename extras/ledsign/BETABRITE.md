# BetaBrite LED Sign Display Capabilities

This document provides a comprehensive reference for the BetaBrite LED sign display capabilities available through the custom BETABRITE library in this project.

## Overview

The BetaBrite library supports the Alpha Protocol for LED sign communication, providing extensive control over text display, colors, animations, and special effects. This enables rich, dynamic alert presentations that can be customized based on alert type, severity, and content.

## Display Modes

### Basic Display Modes
| Mode | Code | Description | Use Case |
|------|------|-------------|----------|
| Rotate | `a` | Cycles through text files | Default continuous display |
| Hold | `b` | Static display without movement | Important messages that need to stay visible |
| Flash | `c` | Text blinks on/off | Critical alerts requiring immediate attention |
| Scroll | `m` | Text scrolls horizontally | Long messages or continuous information |
| Auto Mode | `o` | Sign determines best display method | General purpose display |

### Motion Display Modes
| Mode | Code | Description | Visual Effect |
|------|------|-------------|---------------|
| Roll Up | `e` | Text rolls up from bottom | Smooth vertical transition |
| Roll Down | `f` | Text rolls down from top | Smooth vertical transition |
| Roll Left | `g` | Text rolls in from right | Horizontal sliding motion |
| Roll Right | `h` | Text rolls in from left | Horizontal sliding motion |
| Roll In | `p` | Text rolls in from edges | Converging motion effect |
| Roll Out | `q` | Text rolls out to edges | Diverging motion effect |

### Wipe Display Modes
| Mode | Code | Description | Visual Effect |
|------|------|-------------|---------------|
| Wipe Up | `i` | Text wipes upward | Clean vertical reveal |
| Wipe Down | `j` | Text wipes downward | Clean vertical reveal |
| Wipe Left | `k` | Text wipes leftward | Clean horizontal reveal |
| Wipe Right | `l` | Text wipes rightward | Clean horizontal reveal |
| Wipe In | `r` | Text wipes in from edges | Converging reveal |
| Wipe Out | `s` | Text wipes out to edges | Diverging reveal |

### Advanced Display Modes
| Mode | Code | Description | Best For |
|------|------|-------------|----------|
| Compressed Rotate | `t` | Compact rotation display | Space-efficient cycling |
| Explode | `u` | Text explodes outward | High-impact announcements |
| Clock | `v` | Time/date display mode | Timestamp information |
| Special | `n` | Enables special effects | Enhanced visual presentations |

## Special Effects (Used with Special Display Mode)

### Atmospheric Effects
| Effect | Code | Description | Mood/Theme |
|--------|------|-------------|------------|
| Twinkle | `0` | Stars twinkling effect | Gentle, pleasant |
| Sparkle | `1` | Sparkling lights effect | Celebratory, bright |
| Snow | `2` | Falling snow effect | Weather, winter theme |
| Spray | `6` | Water spray effect | Dynamic, energetic |
| Starburst | `7` | Explosive star effect | Dramatic, attention-grabbing |
| Fireworks | `X` | Fireworks explosion | Celebration, major events |

### Movement Effects
| Effect | Code | Description | Motion Type |
|--------|------|-------------|-------------|
| Interlock | `3` | Interlocking pattern | Mechanical, systematic |
| Switch | `4` | Switching pattern | Toggle, alternating |
| Slide | `5` | Sliding motion | Smooth, directional |
| Slots | `9` | Slot machine effect | Random, gaming |
| Turballoon | `Y` | Turbulent balloon | Floating, dynamic |

### Themed Effects
| Effect | Code | Description | Theme |
|--------|------|-------------|-------|
| Welcome | `8` | Welcome message effect | Greeting, hospitality |
| News Flash | `A` | Breaking news style | Urgent news, updates |
| Trumpet | `B` | Trumpet fanfare | Announcement, fanfare |
| Thank You | `S` | Thank you message | Gratitude, completion |
| No Smoking | `U` | No smoking symbol | Warning, prohibition |
| Don't Drink & Drive | `V` | Safety message | Safety, warning |
| Fishimal | `W` | Fish animation | Playful, aquatic |
| Bomb | `Z` | Explosion effect | Extreme urgency |

### Color Effects
| Effect | Code | Description | Usage |
|--------|------|-------------|-------|
| Cycle Colors | `C` | Rotates through colors | Dynamic, eye-catching |

## Colors

### Standard Colors
| Color | Code | Description | Best For |
|-------|------|-------------|----------|
| Red | `1` | Bright red | Critical alerts, emergencies |
| Green | `2` | Bright green | Success, normal status |
| Amber | `3` | Amber/orange | Warnings, caution |
| Yellow | `8` | Bright yellow | Attention, information |
| Orange | `7` | Orange | Moderate warnings |

### Dimmed Colors
| Color | Code | Description | Usage |
|-------|------|-------------|-------|
| Dim Red | `4` | Darker red | Subdued alerts |
| Dim Green | `5` | Darker green | Background status |
| Brown | `6` | Brown/dark amber | Neutral information |

### Dynamic Colors
| Color | Code | Description | Effect |
|-------|------|-------------|--------|
| Rainbow 1 | `9` | First rainbow pattern | Multi-color cycling |
| Rainbow 2 | `A` | Second rainbow pattern | Alternative rainbow |
| Color Mix | `B` | Mixed color pattern | Varied color display |
| Auto Color | `C` | Sign determines color | Automatic selection |

## Display Positions

| Position | Code | Description | Usage |
|----------|------|-------------|-------|
| Top Line | `"` | Upper portion of display | Headers, titles |
| Middle Line | ` ` | Center of display | Main content |
| Bottom Line | `&` | Lower portion of display | Status, footers |
| Fill | `0` | Full display area | Maximum visibility |
| Left | `1` | Left-aligned | Standard text alignment |
| Right | `2` | Right-aligned | Numbers, timestamps |

## Character Sets

### Standard Character Sets
| Set | Code | Description | Height | Style |
|-----|------|-------------|--------|-------|
| 5 High | `1` | Basic 5-pixel height | Small | Simple |
| 5 Stroke | `2` | 5-pixel stroke font | Small | Outlined |
| 7 High | `3` | Standard 7-pixel height | Medium | Clean |
| 7 Stroke | `4` | 7-pixel stroke font | Medium | Outlined |
| 7 High Fancy | `5` | Decorative 7-pixel | Medium | Stylized |
| 10 High | `6` | Large 10-pixel height | Large | Bold |

### Enhanced Character Sets
| Set | Code | Description | Style |
|-----|------|-------------|-------|
| 7 Shadow | `7` | Shadow effect | Dimensional |
| Full High Fancy | `8` | Full height decorative | Elegant |
| Full High | `9` | Full height standard | Maximum size |
| 7 Shadow Fancy | `:` | Shadow with decoration | Ornate |

### Wide Character Sets
| Set | Code | Description | Width |
|-----|------|-------------|-------|
| 5 Wide | `;` | 5-pixel wide | Compact wide |
| 7 Wide | `<` | 7-pixel wide | Standard wide |
| 7 Wide Fancy | `=` | Decorative wide | Stylized wide |
| 5 Wide Stroke | `>` | 5-pixel wide outline | Outlined wide |

## Text Formatting Controls

### Character Attributes
| Attribute | Code | Description | Effect |
|-----------|------|-------------|--------|
| Wide | `0` | Wide characters | Expanded width |
| Double Wide | `1` | Double width | Very wide text |
| Double High | `2` | Double height | Very tall text |
| True Descenders | `3` | Proper descenders | Better typography |
| Fixed Width | `4` | Monospace font | Aligned columns |
| Fancy | `5` | Decorative style | Ornate appearance |
| Shadow | `7` | Shadow effect | Dimensional look |

### Speed Controls
| Speed | Code | Description | Rate |
|-------|------|-------------|------|
| Speed 1 | `\025` | Slowest | Deliberate, readable |
| Speed 2 | `\026` | Slow | Comfortable reading |
| Speed 3 | `\027` | Medium | Standard pace |
| Speed 4 | `\030` | Fast | Quick updates |
| Speed 5 | `\031` | Fastest | Rapid attention |

### Special Formatting
| Control | Code | Description | Usage |
|---------|------|-------------|-------|
| New Line | `\015` | Line break | Multi-line messages |
| New Page | `\014` | Page break | Separate content |
| Character Flash | `\007` | Flashing text | Emphasis |
| No Hold Speed | `\011` | Continuous motion | Smooth animation |

## Alert Level Mapping Recommendations

### Critical Alerts
```
Mode: flash (c) or newsflash (A)
Special Effect: starburst (7) or bomb (Z)
Color: red (1)
Speed: 5 (fastest)
Character Set: 10 High (6) or 7 High (3)
Position: fill (0)
```

### Warning Alerts  
```
Mode: scroll (m) or special (n)
Special Effect: sparkle (1) or trumpet (B) 
Color: amber (3) or orange (7)
Speed: 3 (medium)
Character Set: 7 High (3)
Position: top line (")
```

### Info Alerts
```
Mode: rotate (a) or scroll (m)
Special Effect: twinkle (0) or welcome (8)
Color: green (2) or auto color (C)
Speed: 2 (slow)
Character Set: 7 High (3) or 5 High (1)
Position: middle line ( )
```

### Debug Alerts
```
Mode: hold (b)
Special Effect: none
Color: dim green (5)
Speed: 1 (slowest)
Character Set: 5 High (1)
Position: bottom line (&)
```

## Category-Specific Recommendations

### Security Alerts
- **Effects**: starburst, newsflash, bomb
- **Colors**: red, amber for severity
- **Mode**: flash, explode for urgency

### Weather Alerts  
- **Effects**: snow, spray, twinkle
- **Colors**: context-appropriate (blue/white for snow, etc.)
- **Mode**: scroll for continuous updates

### System Status
- **Effects**: sparkle, cycle colors
- **Colors**: green (good), amber (warning), red (error)
- **Mode**: rotate, hold for status

### Personal Reminders
- **Effects**: welcome, thank you
- **Colors**: auto color, rainbow
- **Mode**: gentle transitions (wipe, roll)

## Enhanced Message Format Examples

### Priority Alert (Full Featured)
```
[red,flash,starburst,10high,5,fill]SECURITY ALERT: Motion detected at front door
```

### Weather Update (Atmospheric)
```
[amber,scroll,snow,7high,2,topline]WEATHER: Snow expected tonight, 3-5 inches
```

### System Status (Informational)
```
[green,rotate,twinkle,7high,2,midline]SYSTEM: All services operating normally
```

### Emergency Alert (Maximum Impact)
```
[red,explode,bomb,10high,5,fill]EMERGENCY: Evacuate building immediately
```

## Programming Interface

### Basic Usage
```cpp
// Simple text with color and effect
sign.WriteTextFile('A', "[red,flash]Alert Message", BB_COL_RED, BB_DP_TOPLINE, BB_DM_FLASH, BB_SDM_STARBURST);

// Priority message (overrides normal rotation)
sign.WritePriorityTextFile("URGENT: Emergency Alert", BB_COL_RED, BB_DP_FILL, BB_DM_FLASH, BB_SDM_BOMB);
```

### Advanced Configuration
```cpp
// Configure memory for multiple text files
sign.SetMemoryConfiguration('A', 5, 256);  // Files A-E, 256 bytes each

// Multiple messages in sequence
sign.WriteTextFile('A', "[red,flash,starburst]Critical Alert");
sign.WriteTextFile('B', "[amber,scroll,sparkle]Warning Message"); 
sign.WriteTextFile('C', "[green,rotate,twinkle]Status Update");
```

## Integration with Alert Router System

The BetaBrite library integrates seamlessly with the centralized Alert Router Service, enabling rich, contextually appropriate displays based on alert metadata. The alert router maps incoming alert messages to specific BetaBrite display configurations using the complete range of available animations and effects.

### Alert Router to BetaBrite Mapping

#### Standardized JSON Alert Message Format

**Basic Alert with LED Configuration**:
```json
{
  "timestamp": 1704045600,
  "level": "critical",
  "category": "security",
  "title": "Motion Detected",
  "message": "Front door motion sensor triggered",
  "source": {
    "id": "security-system-01",
    "type": "security_service",
    "metadata": {
      "location": "front_door",
      "device_id": "motion_01"
    }
  },
  "pathway_config": {
    "led_security": {
      "zones": {
        "main": {
          "display_config": {
            "mode": "explode",
            "special_effect": "bomb",
            "color": "red",
            "character_set": "10high",
            "speed": 5,
            "priority": true,
            "duration": 30
          }
        }
      }
    }
  }
}
```

**Multi-Zone LED Alert Configuration**:
```json
{
  "timestamp": 1704045600,
  "level": "warning",
  "category": "system",
  "title": "Server Status Alert",
  "message": "High CPU usage detected on production server",
  "source": {
    "id": "monitoring-service",
    "type": "monitoring",
    "metadata": {
      "server": "prod-01",
      "cpu_usage": "85%"
    }
  },
  "metadata": {
    "led_zones": ["office", "server_room"]
  },
  "pathway_config": {
    "led_status": {
      "zones": {
        "office": {
          "display_config": {
            "mode": "scroll",
            "color": "amber",
            "character_set": "7high",
            "speed": 3
          }
        },
        "server_room": {
          "display_config": {
            "mode": "flash",
            "special_effect": "starburst",
            "color": "red",
            "character_set": "10high",
            "speed": 4,
            "priority": true
          }
        }
      }
    }
  }
}
```

#### ESP32 Integration Code Example
```cpp
void SignController::processAlertMessage(const String& payload) {
    JsonDocument doc;
    deserializeJson(doc, payload);
    
    String message = doc["message"].as<String>();
    String title = doc["title"].as<String>();
    JsonObject displayConfig = doc["display_config"];
    
    if (displayConfig && !displayConfig.isNull()) {
        // Map JSON config to BetaBrite constants
        char position = mapPosition(displayConfig["position"].as<String>());
        char mode = mapDisplayMode(displayConfig["mode"].as<String>());
        char effect = mapSpecialEffect(displayConfig["special_effect"].as<String>());
        char color = mapColor(displayConfig["color"].as<String>());
        
        String fullMessage = title + ": " + message;
        
        if (displayConfig["priority"].as<bool>()) {
            betabrite.WritePriorityTextFile(fullMessage.c_str(), color, position, mode, effect);
        } else {
            betabrite.WriteTextFile('A', fullMessage.c_str(), color, position, mode, effect);
        }
    } else {
        // Fallback to simple display
        betabrite.WriteTextFile('A', (title + ": " + message).c_str());
    }
}
```

### Alert Level to Animation Presets

#### Critical Alerts - Maximum Impact
- **Mode**: `explode` or `flash` for immediate attention
- **Effect**: `bomb`, `starburst`, or `newsflash` for urgency
- **Color**: `red` for emergency status
- **Character Set**: `10high` or `fhigh` for maximum visibility
- **Position**: `fill` to use entire display
- **Priority**: Always `true` to interrupt normal rotation

```json
{
  "display_config": {
    "position": "fill",
    "mode": "explode",
    "special_effect": "bomb",
    "color": "red",
    "character_set": "10high",
    "speed": 5,
    "priority": true,
    "duration": 60
  }
}
```

#### Warning Alerts - Attention Grabbing
- **Mode**: `newsflash` or `scroll` for visibility
- **Effect**: `trumpet`, `sparkle`, or `starburst` for importance
- **Color**: `amber` or `orange` for caution
- **Character Set**: `7high` for readability
- **Position**: `topline` for prominence

```json
{
  "display_config": {
    "position": "topline",
    "mode": "newsflash",
    "special_effect": "trumpet",
    "color": "amber",
    "character_set": "7high",
    "speed": 3
  }
}
```

#### Info Alerts - Gentle Display
- **Mode**: `scroll` or `rotate` for continuous display
- **Effect**: `twinkle`, `welcome`, or `sparkle` for pleasant viewing
- **Color**: `green` or `autocolor` for positive tone
- **Character Set**: `7high` for standard readability
- **Position**: `midline` for standard placement

```json
{
  "display_config": {
    "position": "midline",
    "mode": "scroll",
    "special_effect": "twinkle",
    "color": "green",
    "character_set": "7high",
    "speed": 2
  }
}
```

### Category-Specific Animation Themes

#### Security Alerts
**High-Impact, Attention-Grabbing Effects**
```json
{
  "security_critical": {
    "mode": "flash",
    "special_effect": "starburst",
    "color": "red",
    "character_set": "10high",
    "position": "fill",
    "priority": true
  },
  "security_warning": {
    "mode": "newsflash",
    "special_effect": "trumpet",
    "color": "amber",
    "character_set": "7high",
    "position": "topline"
  }
}
```

#### Weather Alerts
**Atmospheric, Contextual Effects**
```json
{
  "weather_storm": {
    "mode": "wipedown",
    "special_effect": "spray",
    "color": "amber",
    "character_set": "7high"
  },
  "weather_snow": {
    "mode": "scroll",
    "special_effect": "snow",
    "color": "autocolor",
    "character_set": "7high"
  },
  "weather_wind": {
    "mode": "slide",
    "special_effect": "turballoon",
    "color": "yellow",
    "character_set": "7high"
  }
}
```

#### System Status
**Professional, Informational Display**
```json
{
  "system_error": {
    "mode": "flash",
    "special_effect": "interlock",
    "color": "red",
    "character_set": "7high"
  },
  "system_warning": {
    "mode": "compressed_rotate",
    "special_effect": "sparkle",
    "color": "amber",
    "character_set": "7high"
  },
  "system_ok": {
    "mode": "rotate",
    "special_effect": "twinkle",
    "color": "green",
    "character_set": "7high"
  }
}
```

#### Celebration/Positive News
**Festive, Joyful Effects**
```json
{
  "celebration": {
    "mode": "explode",
    "special_effect": "fireworks",
    "color": "rainbow1",
    "character_set": "10high",
    "position": "fill"
  },
  "achievement": {
    "mode": "rollin",
    "special_effect": "welcome",
    "color": "colormix",
    "character_set": "7highfancy"
  },
  "completion": {
    "mode": "wipein",
    "special_effect": "thankyou",
    "color": "green",
    "character_set": "7shadow"
  }
}
```

### Advanced Integration Features

#### Multi-Zone Display Support
```cpp
// Route different alerts to different sign zones
if (alertLevel == "critical") {
    // Send to all zones
    sendToZone("kitchen", alertMessage, criticalConfig);
    sendToZone("living_room", alertMessage, criticalConfig);
    sendToZone("office", alertMessage, criticalConfig);
} else if (alertCategory == "weather") {
    // Send only to main display zone
    sendToZone("living_room", alertMessage, weatherConfig);
}
```

#### Priority Queue Management
```cpp
// Handle priority messages with duration control
if (displayConfig["priority"].as<bool>()) {
    int duration = displayConfig["duration"].as<int>();
    
    // Set priority message
    betabrite.WritePriorityTextFile(message.c_str(), color, position, mode, effect);
    
    // Schedule return to normal rotation after duration
    scheduler.scheduleTask([this]() {
        betabrite.CancelPriorityTextFile();
    }, duration * 1000);
}
```

#### Dynamic Configuration Updates
```cpp
// Update display based on alert metadata
if (metadata.containsKey("temperature")) {
    float temp = metadata["temperature"].as<float>();
    if (temp > 85) {
        // Use "hot" themed display
        effect = BB_SDM_SPRAY;
        color = BB_COL_RED;
    } else if (temp < 32) {
        // Use "cold" themed display  
        effect = BB_SDM_SNOW;
        color = BB_COL_BLUE;
    }
}
```

### Performance Optimization

#### Efficient Command Generation
```cpp
class BetaBriteCommandBuilder {
public:
    String buildCommand(const JsonObject& config, const String& message) {
        // Pre-build command sequences for common configurations
        String cmd = "";
        cmd += mapToHardwareCode(config["mode"].as<String>());
        cmd += mapToHardwareCode(config["special_effect"].as<String>());
        cmd += mapToHardwareCode(config["color"].as<String>());
        cmd += message;
        return cmd;
    }
    
private:
    char mapToHardwareCode(const String& configValue) {
        // Fast lookup table for configuration mapping
        static const std::map<String, char> mappings = {
            {"explode", BB_DM_EXPLODE},
            {"bomb", BB_SDM_BOMB},
            {"red", BB_COL_RED}
            // ... complete mapping table
        };
        return mappings.at(configValue);
    }
};
```

### Complete Display Capability Matrix

The BetaBrite system supports **23 display modes × 21 special effects × 12 colors × 14 character sets = 84,168 unique display combinations**, enabling highly expressive and contextually appropriate alert presentations that convey not just message content, but also urgency, type, and emotional tone.

This comprehensive integration allows the LED sign controller to serve as a powerful, visually rich output channel in the centralized alerting architecture, providing immediate visual feedback that matches the severity and context of each alert.