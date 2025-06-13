# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This is a comprehensive soapbox derby race management system built by extensively modifying the DerbyNet software. DerbyNet was originally created for Pinewood Derby racing events (small wooden cars racing down a gravity track), but has been extensively modified to support children's Soapbox Derby events (larger gravity-powered cars with children riding in them).

**Current Version: 0.5.0**

## System Overview

This project is a comprehensive soapbox derby race management system built by extensively modifying the DerbyNet software. DerbyNet was originally created for Pinewood Derby racing events (small wooden cars racing down a gravity track), but has been extensively modified to support children's Soapbox Derby events (larger gravity-powered cars with children riding in them).

The system consists of several integrated components:

1. **DerbyNet PHP Core** (`/website/`): A PHP-based web application that handles race management, timing, results tracking, and award management
2. **Race Server** (`/extras/soapbox/infra/server/`): Central coordination server that manages race state and communicates with hardware components
3. **Finish Timer** (`/extras/soapbox/infra/finishtimer/`): Hardware-based finish line detection system using toggle switches on Raspberry Pi
4. **Start Timer** (`/extras/soapbox/infra/starttimer/`): ESP32-based device that detects race start signals 
5. **Derby Display** (`/extras/soapbox/infra/derbydisplay/`): Display screens showing race status and results
6. **HLS Feed** (`/extras/soapbox/hlsfeed/`): Camera streaming service for race viewing and replay

[... rest of the existing content ...]

## Memory Guidance

- All names of racing rounds must start with a number to allow proper sequencing
- The database file is a cached copy of production you can read from it but any changes will be discarded and any commands to the server will not be evident after the file was refreshed

## Critical Heat Generation Fix (2025-06-12)

**IMPORTANT**: The elimination tournament heat generation was completely fixed after discovering the root cause of incorrect scheduling.

### Problem:
- **Preliminary rounds** were generating 3 races per lane (9 total per racer) instead of 3 races per racer (1 per lane)
- **Quarter finals** were generating 27 heats (81 entries) instead of 9 heats (27 entries)
- Legacy triple elimination logic was conflicting with JSON hardcoded configurations

### Root Cause:
DerbyNet's scheduling system has a parameter `n_times_per_lane` that was being misinterpreted:
- `n_times_per_lane = 3` means racer appears 3 times in EACH lane (9 total races on 3-lane track)
- `n_times_per_lane = 1` means racer appears 1 time in EACH lane (3 total races on 3-lane track)

### Solution:
1. **Fixed Parameter Logic** (`ajax/action.schedule.generate.inc`):
   - JSON `races_per_racer: 3` → `n_times_per_lane = 1` (once per lane = 3 total)
   - JSON `races_per_racer: 1` → Custom sequential scheduling

2. **Added Custom Single-Race Scheduling** (`inc/schedule_one_round.inc`):
   - New function `schedule_elimination_single_race()` 
   - Creates sequential heat assignment for rounds with 1 race per racer
   - Bypasses problematic `max_runs_per_car` rotation logic

3. **Removed All Legacy Logic**:
   - Eliminated conflicting triple elimination detection
   - Cleaned up legacy database column references

### Key Files Modified:
- `website/ajax/action.schedule.generate.inc` - Fixed elimination tournament detection and parameter setting
- `website/inc/schedule_one_round.inc` - Added custom single-race scheduling function
- Multiple files - Removed legacy triple elimination logic conflicts

**Result**: Elimination tournaments now generate correct heat counts as specified in JSON configuration.
```