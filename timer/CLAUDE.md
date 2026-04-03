# Timer Application (Legacy Java)

## Purpose

Java-based timer interface application for connecting hardware timers to DerbyNet via serial/USB and WebSocket communication. This is the original DerbyNet timer system.

## How It Fits

This is the original timer bridge from the upstream DerbyNet project. For soapbox derby events, the Python-based timers in `extras/soapbox/infra/` (finishtimer, starttimer) are used instead. This Java timer remains available for Pinewood Derby setups or as a fallback.

## Key Files

- `build.xml` — Apache Ant build configuration
- `src/org/derbynet/` — Java source (80+ files)
- `derbynet-timer/` — Built JAR output

## Tech Stack

- Java (Apache Ant build system)
- Serial communication (RXTX/jSSC libraries)
- WebSocket client
- Libraries in `/lib/` (WebSocket, JSON, Serial JARs)

## Common Tasks

- **Build**: `ant timer-jar` (from repo root)
- **Build web timer**: `ant timer-in-browser`
- **Run**: `java -jar derbynet-timer/derbynet-timer.jar`

## Gotchas

- **Legacy component**: Soapbox derby events use Python timers instead
- **Serial drivers**: May need platform-specific serial port drivers
- **Ant required**: `sudo apt-get install ant` for building

## Related Docs

- Original DerbyNet documentation in `docs/legacy/` (`.fodt` files)
