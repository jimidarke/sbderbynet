# Version Schema for Derby Race System

This document defines the standardized versioning approach for all components of the Derby Race System.

## Versioning Format

The system uses semantic versioning in the format:

```
MAJOR.MINOR.PATCH
```

Where:
- **MAJOR**: Incremented for incompatible API or protocol changes
- **MINOR**: Incremented for backward-compatible new functionality
- **PATCH**: Incremented for backward-compatible bug fixes

## Current System Version

The current system version is: **0.5.0**

## Component Versioning

All components must maintain the following versioning standards:

1. **Version Variable**: Each module should define a `VERSION` constant at the top of the main file:
   ```python
   VERSION = "0.5.0"
   ```

2. **Telemetry**: All telemetry data must include the version:
   ```python
   telemetry_data = {
       "version": VERSION,
       # other telemetry data
   }
   ```

3. **Logging**: Version should be included in startup logs:
   ```python
   logger.info(f"Starting {component_name} v{VERSION}")
   ```

## Version History

Version history should be maintained in comments at the top of each file using this format:

```
Version History:
- 0.5.0 - May 19, 2025 - Standardized version schema across all components
- 0.4.0 - May 10, 2025 - Added service discovery via mDNS
- 0.3.0 - April 22, 2025 - Added remote syslogging and improved error handling
- 0.2.0 - April 15, 2025 - Added telemetry and watchdog timers
- 0.1.0 - April 4, 2025 - Added communication protocols
- 0.0.1 - March 31, 2025 - Initial implementation
```

## Component Versions

All components now standardized to version 0.5.0:

- Server (derbyRace.py): 0.5.0
- Finish Timer (derbynetPCBv1.py): 0.5.0
- Start Timer (main.py): 0.5.0
- Derby Display (derbydisplay.py): 0.5.0
- HLS Feed (replay_handler.py): 0.5.0
- LCD Display (derbyLCD.py): 0.5.0

## Version Update Process

When updating versions:

1. Increment the appropriate part of the version number based on changes
2. Update the VERSION constant in the file
3. Add new entry to the version history in file comments
4. Update version number in telemetry data
5. Update VERSION.md with new component version