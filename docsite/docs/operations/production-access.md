# Production Access

How to reach the live DerbyNet database on the race-day Raspberry Pi over SFTP.

!!! warning "Keys are out-of-band"
    The SSH key for `derbynet@192.168.100.10` is **not** stored in this repo. Keys are provisioned per-deployer through the secret-management process — ask whoever set up your dev box. The historical `SECURE/keys/derby/id_rsa` path is no longer canonical.

---

## Connection

| Parameter | Value |
|---|---|
| Host | `192.168.100.10` |
| Port | `22` |
| Username | `derbynet` |
| Private key | wherever your provisioning put it (e.g. `~/.ssh/derbynet/id_rsa`) |
| Remote path | `/var/lib/derbynet` |

You'll be on the race subnet to do this — either physically at the venue, or through a venue-side jumphost.

---

## Usage

### Download the current database

```bash
mkdir -p /tmp/derbynet
sftp -i ~/.ssh/derbynet/id_rsa -P 22 \
     derbynet@192.168.100.10:/var/lib/derbynet/2025/test1/derbynet.sqlite3 \
     /tmp/derbynet/
```

### Interactive session

```bash
sftp -i ~/.ssh/derbynet/id_rsa derbynet@192.168.100.10
> cd /var/lib/derbynet
> ls -la
```

### Query the downloaded copy

```bash
sqlite3 /tmp/derbynet/derbynet.sqlite3 ".tables"
sqlite3 /tmp/derbynet/derbynet.sqlite3 "SELECT * FROM Roster LIMIT 5;"
```

---

## Server data layout

```
/var/lib/derbynet/
├── {year}/{event}/
│   ├── derbynet.sqlite3   ← Main database (SQLite, WAL mode)
│   ├── cars/              ← Car photos
│   ├── racers/            ← Racer photos
│   ├── imagery/           ← General images
│   ├── logs/              ← Application logs
│   ├── slides/            ← Slideshow content
│   └── videos/            ← Race videos
├── imagery/
├── queue/
└── slides/
```

### Database tables (28 total)

- **Core**: `Roster`, `Classes`, `Ranks`, `Rounds`, `RaceChart`, `RaceInfo`
- **Elimination**: `EliminationTournaments`, `EliminationAdvancement`, `EliminationRoundState`
- **Other**: `Awards`, `Kiosks`, `Scenes`, `DeviceStatus`, `TimerStatus`, etc.

---

## Cloud sync — why we don't usually need this

The Pi pushes a snapshot of the live SQLite to the cloud twin via the `cloud-sync.sh` cron job. For most browsing/inspection, hit the cloud twin instead — it's auth-friendly, doesn't require being on the race subnet, and is what the [Dress Rehearsal](dress-rehearsal.md) Part B verification step relies on. SFTP into the Pi is for the small set of cases where you need the file directly: forensic post-mortems, backup pulls, or cloud-sync itself broken.

---

## Important notes

- The database file is a live SQLite3 in WAL mode. Downloads are point-in-time snapshots; changes do not sync back.
- Don't write to the live DB over SFTP. If you need to apply a change, do it through the PHP application or via a deliberate `scp` of a vetted file *while the race server is stopped*.
