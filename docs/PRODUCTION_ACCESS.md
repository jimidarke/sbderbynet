# Production Data Access

Access to the live DerbyNet database on the race-day Raspberry Pi server via SFTP.

## Connection Parameters

| Parameter | Value |
|-----------|-------|
| Host | 192.168.100.10 |
| Port | 22 |
| Username | derbynet |
| Private Key | `~/.ssh/derbynet/id_rsa` |
| Remote Path | /var/lib/derbynet |

## Setup (Required Once)

The SSH key must be on a Linux filesystem for proper permissions. Copy from the repo:

```bash
mkdir -p ~/.ssh/derbynet
cp SECURE/keys/derby/id_rsa ~/.ssh/derbynet/
chmod 600 ~/.ssh/derbynet/id_rsa
```

## Usage

### Download current database
```bash
mkdir -p /tmp/derbynet
sftp -i ~/.ssh/derbynet/id_rsa -P 22 derbynet@192.168.100.10:/var/lib/derbynet/2025/test1/derbynet.sqlite3 /tmp/derbynet/
```

### Interactive session
```bash
sftp -i ~/.ssh/derbynet/id_rsa -P 22 derbynet@192.168.100.10
cd /var/lib/derbynet
ls -la
```

### Query downloaded database
```bash
sqlite3 /tmp/derbynet/derbynet.sqlite3 ".tables"
sqlite3 /tmp/derbynet/derbynet.sqlite3 "SELECT * FROM Roster LIMIT 5;"
```

## Server Data Structure

```
/var/lib/derbynet/
├── {year}/{event}/
│   ├── derbynet.sqlite3  ← Main database (SQLite WAL mode)
│   ├── cars/             ← Car photos
│   ├── racers/           ← Racer photos
│   ├── imagery/          ← General images
│   ├── logs/             ← Application logs
│   ├── slides/           ← Slideshow content
│   └── videos/           ← Race videos
├── imagery/
├── queue/
└── slides/
```

## Database Tables (28 total)

**Core**: `Roster`, `Classes`, `Ranks`, `Rounds`, `RaceChart`, `RaceInfo`

**Elimination**: `EliminationTournaments`, `EliminationAdvancement`, `EliminationRoundState`

**Other**: `Awards`, `Kiosks`, `Scenes`, `DeviceStatus`, `TimerStatus`, etc.

## Important Notes

- The database file is a live SQLite3 database in WAL mode
- Downloaded copies are snapshots — changes will not sync back
- The SSH key is in `SECURE/keys/derby/id_rsa` within this repository
