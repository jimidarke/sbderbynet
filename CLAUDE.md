# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a comprehensive soapbox derby race management system built by extensively modifying the DerbyNet software. DerbyNet was originally created for Pinewood Derby racing events (small wooden cars racing down a gravity track), but has been extensively modified to support children's Soapbox Derby events (larger gravity-powered cars with children riding in them).

**Current Version: 1.0.0**

## Complete Documentation

For comprehensive documentation including:
- Pull request summary and technical contributions
- System architecture and requirements
- Installation and setup instructions
- Feature documentation and usage guides
- Hardware integration details
- Testing and quality assurance information

**Please refer to the main [README.md](README.md) file which contains all consolidated documentation for this project.**

## Quick Technical Reference

### Key System Components

1. **DerbyNet PHP Core** (`/website/`): Web-based race management system
2. **Race Server** (`/extras/soapbox/infra/server/`): Central coordination server with MQTT messaging
3. **Finish Timer** (`/extras/soapbox/infra/finishtimer/`): Hardware-based finish line detection
4. **Start Timer** (`/extras/soapbox/infra/starttimer/`): ESP32-based race start detection
5. **Derby Display** (`/extras/soapbox/infra/derbydisplay/`): Display screens for race information
6. **HLS Feed** (`/extras/soapbox/hlsfeed/`): Camera streaming service for race viewing

### Major Enhancements Made

- **~40 new files** in complete hardware infrastructure
- **Critical scheduling engine fixes** resolving parameter interpretation bugs
- **JSON-based elimination tournament system** with 3 new database tables
- **Professional kiosk displays** with modern UI/UX
- **MQTT messaging architecture** for hardware coordination
- **Broadcast messaging system** for real-time announcements
- **Complete backward compatibility** with existing DerbyNet functionality

### Memory Guidance

- All names of racing rounds must start with a number to allow proper sequencing
- The database file is a cached copy of production - changes will be discarded when refreshed
- Tournament configurations use JSON files in `/inc/elimination-configs/`
- Heat generation uses weighted parameters: avoid_consecutive=5000, group_weighted_cars=100, avoid_same_lane=200, heat_counts=10

### Production Data Access

For troubleshooting, the live database can be accessed via SFTP. See [SECURE/SFTP_ACCESS.md](SECURE/SFTP_ACCESS.md) for connection details and usage instructions.

Quick reference:
```bash
# Setup (once): copy key to Linux filesystem for proper permissions
mkdir -p ~/.ssh/derbynet && cp SECURE/keys/derby/id_rsa ~/.ssh/derbynet/ && chmod 600 ~/.ssh/derbynet/id_rsa

# Download current database
sftp -i ~/.ssh/derbynet/id_rsa -P 22 derbynet@192.168.100.10:/var/lib/derbynet/2025/test1/derbynet.sqlite3 /tmp/derbynet/
```

### Critical Bug Fixes Applied

**Heat Generation Parameter Fix (2025-06-12)**:
- Fixed `n_times_per_lane` parameter interpretation in scheduling engine
- JSON `races_per_racer: 3` → `n_times_per_lane = 1` (3 total races: 1 per lane)
- JSON `races_per_racer: 1` → Custom sequential scheduling function
- Removed conflicting legacy triple elimination logic

**Key Files Modified**:
- `website/ajax/action.schedule.generate.inc` - Fixed elimination tournament detection
- `website/inc/schedule_one_round.inc` - Added custom single-race scheduling
- `website/inc/elimination-config.inc` - Tournament configuration management
- `website/sql/sqlite/elimination-tables.inc` - New database schema

## Development Notes

- This system maintains full backward compatibility with original DerbyNet
- The `extras/soapbox/` directory contains completely new infrastructure
- Core scheduling engine fixes benefit all DerbyNet users
- Elimination tournament system is designed as reusable framework
- Professional display enhancements work with any derby type

For detailed technical information, architecture diagrams, installation guides, and complete feature documentation, see the main [README.md](README.md).