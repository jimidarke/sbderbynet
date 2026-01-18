# Alert Manager Client Integration Reference

**Version:** 1.4.0
**Last Updated:** 2025-12-30

Technical reference for sending alerts to the Alert Manager system. Audience: Senior developers and LLM code assistants.

---

## Connection Matrix

| Protocol | Host | Port | Auth | TLS | Use Case |
|----------|------|------|------|-----|----------|
| **HTTPS** | `alert.d-t.pw` | `443` | Basic Auth / Bearer | TLS 1.2+ | Web services, scripts **(PRIMARY)** |
| **HTTP** | `alert.d-t.pw` | `8080` | Basic Auth / Bearer | None | Internal/legacy |
| **MQTT** | `alert.d-t.pw` | `42690` | Username/password | TLS 1.2 | **ESP32 LED devices only** |
| **SNMPv3** | `alert.d-t.pw` | `162/UDP` | USM | N/A | Network devices |

---

## Encryption Standards

### TLS Configuration

| Protocol | Version | Cipher Suites | Certificates |
|----------|---------|---------------|--------------|
| HTTPS | TLS 1.2+ | System default | None required (Basic Auth) |
| MQTT | TLS 1.2 | ESP32-compatible | CA cert required for verification |

### SNMPv3 Security Levels

| Level | Authentication | Encryption | Compatibility |
|-------|----------------|------------|---------------|
| `noAuthNoPriv` | Username only | None | Maximum vendor compatibility |
| `authNoPriv` | SHA/MD5 | None | Moderate security |
| `authPriv` | SHA | AES-128/256 | High security |

---

## HTTP Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/alert` | Required | Send alert payload |
| `POST` | `/test` | Required | Send test alert |
| `GET` | `/health` | None | Health check |
| `GET` | `/logs` | Required | Log viewer web interface |
| `GET` | `/api/logs/list` | Required | List available log files (JSON) |
| `GET` | `/api/logs/tail` | Required | Tail log file for streaming |
| `GET` | `/docs` | Required | Serve documentation |

---

## MQTT Topics

| Topic | Direction | Description |
|-------|-----------|-------------|
| `alerts/input` | Publish | Submit alerts (internal only) |
| `alerts/service/status` | Subscribe | Service health (every 60s) |
| `ledSign/{zone}/message` | Subscribe | LED sign messages per zone |
| `ledSign/{zone}/rssi` | Publish | Device signal strength |
| `ledSign/{zone}/ip` | Publish | Device IP address |
| `ledSign/{zone}/uptime` | Publish | Device uptime |
| `ledSign/{zone}/memory` | Publish | Device free memory |

> **MQTT External Access Scope**: Port 42690 is exclusively for ESP32 BetaBrite LED sign devices. All other clients (scripts, services, integrations) should use the HTTP gateway at port 8080/443. See `ESP32_BETABRITE_IMPLEMENTATION.md` for LED device setup.

---

## Authentication & Access Control

| User Type | Rate Limit | Can Send | Log Access | Expires |
|-----------|------------|----------|------------|---------|
| `admin` | 1000/hr | Yes (all clients) | All logs (ops/, file/) | Never |
| `node` | 1000/hr | Yes (auto-inherit clientname) | file/{clientname}*.log | 5 years |
| `client` | 100/hr | No | file/{clientname}*.log | 2 years |

**Client Name Inheritance**: For `node` users, if `client` field is empty/missing, the user's configured `clientname` is automatically applied.

---

## Alert Payload Schema

### Required Fields

| Field | Type | Constraints |
|-------|------|-------------|
| `timestamp` | integer | Unix epoch seconds (no decimals, not ISO 8601) |
| `level` | string | `critical`, `warning`, `notice`, `info`, `debug` |
| `category` | string | `security`, `system`, `weather`, `automation`, `personal`, `network`, `application`, `news` |
| `title` | string | Short alert title |
| `message` | string | Detailed message (multiline supported, see sanitization note below) |
| `source` | string | Source identifier (must be string, not object) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `client` | string | Client identifier for log routing |
| `metadata` | object | Arbitrary key-value data |
| `display_config` | object | LED sign display settings |
| `routing` | object | Override routing rules |

### Level Aliases

| Canonical | Aliases |
|-----------|---------|
| `critical` | `error`, `err`, `crit` |
| `warning` | `warn` |
| `info` | `inf` |
| `debug` | `dbg` |

### String Normalization

All string fields (`level`, `category`, `client`) are automatically whitespace-trimmed, lowercased, and alias-resolved.

### Message Sanitization (File Pathway Only)

**As of v1.4.0**, messages are automatically sanitized in file logs to maintain single-line format:

| Behavior | Description |
|----------|-------------|
| **Newlines** | `\n`, `\r`, `\r\n` replaced with ` ↵ ` (visible indicator) |
| **Tabs** | `\t` replaced with single space |
| **Truncation** | Messages >500 chars truncated with `...` suffix |
| **Scope** | File pathway only - email/database retain full multiline content |

**Why**: Prevents log corruption when messages contain SQL statements, stack traces, or formatted output.

**Example Input**:
```json
{"message": "SQL Error:\nColumn 'date' cannot be null\nRetrying..."}
```

**File Log Output**:
```
1735577400 [critical] [application] source: Title - SQL Error: ↵ Column 'date' cannot be null ↵ Retrying...
```

**Email Output**: Full message with newlines preserved.

**Configuration**: Sanitization enabled by default. Admins can adjust `max_message_length` (default: 500) or disable with `"sanitize_messages": false` in pathway config.

---

## Payload Examples

### Minimal

```json
{"timestamp":1732982400,"level":"info","category":"application","title":"Status","message":"OK","source":"my-service"}
```

### With Routing Override

```json
{
  "timestamp": 1732982400,
  "level": "critical",
  "category": "security",
  "title": "Security Alert",
  "message": "Unauthorized access detected",
  "source": "security-monitor",
  "client": "prod-security",
  "routing": {"override": true, "pathways": ["email_critical", "led_sign"]}
}
```

---

## LED Display Config

| Field | Values |
|-------|--------|
| `mode` | `rotate`, `hold`, `flash`, `scroll`, `rollup`, `rolldown`, `rollright`, `rollleft`, `explode`, `newsflash`, `welcome`, `compressed` |
| `color` | `red`, `green`, `amber`, `rainbow1`, `rainbow2`, `autocolor`, `color_mix` |
| `special_effect` | `twinkle`, `sparkle`, `snow`, `starburst`, `bomb`, `welcome`, `cyclecolors` |
| `character_set` | `5high`, `7high`, `10high`, `7shadow`, `7highfancy`, `7widestroke` |
| `speed` | 1-5 (slowest to fastest) |
| `priority` | boolean |
| `duration` | seconds |

Zone targeting via `metadata.led_zones` array.

---

## Quick Start

### cURL

```bash
curl -X POST https://alert.d-t.pw/alert \
  -u username:password \
  -H "Content-Type: application/json" \
  -d '{"timestamp":'$(date +%s)',"level":"warning","category":"system","title":"Alert","message":"Test","source":"curl"}'
```

### Python

```python
import requests, time

requests.post(
    "https://alert.d-t.pw/alert",
    auth=("username", "password"),
    json={
        "timestamp": int(time.time()),
        "level": "info",
        "category": "application",
        "title": "Status",
        "message": "Task completed",
        "source": "my-app"
    }
)
```

---

## Validation Rules

| Input | Result |
|-------|--------|
| `"level": "ERROR"` | `"critical"` (alias + lowercase) |
| `"level": " warn "` | `"warning"` (trim + alias) |
| `"timestamp": 1732982400` | Valid |
| `"timestamp": "2024-01-15T10:30:00Z"` | **Invalid** - must be integer |
| `"timestamp": 1732982400.123` | **Invalid** - no decimals |
| `"source": {"name": "x"}` | **Invalid** - must be string |

---

## Output Pathways

| Pathway | Description |
|---------|-------------|
| `file` | Date-rotated logs: `/data/logs/file/{client}/{date}.log` |
| `email` | O365 Graph API with MSAL, HTML templates |
| `led_sign` | BetaBrite via MQTT, multi-zone |
| `console` | stdout |
| `database` | PostgreSQL, weekly partitions |

Routing: first-match semantics. Override via `routing.override` + `routing.pathways`.

---

## Management Tools

| Tool | Purpose |
|------|---------|
| `tools/http-auth-manager.sh` | HTTP user CRUD, set-clientname |
| `tools/mqtt-auth-manager.sh` | MQTT user management |
| `tools/snmp-auth-manager.sh` | SNMPv3 user management |
| `tools/cert-manager.sh` | TLS certificate management |

---

## Service Health

**MQTT Topic**: `alerts/service/status` (published every 60s)

```json
{"status":"running","timestamp":"2024-01-15T10:30:00Z","stats":{"alerts_processed":42,"alerts_routed":38,"errors":0,"uptime_seconds":3600}}
```

---

## Documentation Index

| Document | Content |
|----------|---------|
| `CLAUDE.md` | Technical reference (authoritative) |
| `HTTP_GATEWAY.md` | HTTP API details |
| `MQTT_AUTH.md` | MQTT authentication |
| `SNMP_INTEGRATION.md` | SNMP device setup |
| `DATABASE_INTEGRATION.md` | PostgreSQL backend |
| `ANALYTICS.md` | Analytics engine |
| `BETABRITE.md` | LED sign protocol |
