# SaaSBox Premium Cloud Service - Commercialization Plan

## Executive Summary

Transform DerbyNet's on-premise racing system into a freemium SaaS model with **SaaSBox** as the cloud premium brand. The on-premise system (DerbyPi) remains free and fully functional offline. SaaSBox adds cloud-connected premium features for audience engagement, mobile access, and event enhancements.

**Target:** MVP ready for June 2026 race season (~5 months)

---

## Current State

### Already Built
- **Landing page** live at `soapboxderbynet.com` (nginx + Let's Encrypt)
- **Docker infrastructure** on Ubuntu host with nginx-proxy network
- **Flutter mobile app** in development (Android read-only POC working)
- **On-premise system** (DerbyPi) production-ready with 386 tests passing
- **Log sync service** (`logsync.py`) ready for cloud ingestion

### Directory Structure (Existing)
```
extras/saasbox/
├── README.md                    # Placeholder
└── landing/
    ├── docker-compose.yml       # Landing page container (LIVE)
    └── html/
        └── index.html           # "Coming Soon" page (LIVE)
```

---

## 1. Business Model & Pricing Strategy

### Recommended Model: Annual License + Participant Tier

Based on industry analysis (race timing: $2-3/participant, event SaaS: $299-499/year), propose a **hybrid model** optimized for once-per-year events:

| Tier | Annual Price | Includes | Target |
|------|-------------|----------|--------|
| **Free (DerbyPi)** | $0 | Full on-premise system, hardware integration, offline operation | DIY organizers |
| **Hardware Kit** | $800-1500 one-time | Pre-configured Raspberry Pi, finish timers, start timer, displays | Time-constrained organizers |
| **SaaSBox Starter** | $299/year | Cloud sync, public standings, 1 admin | Small events (≤100 racers) |
| **SaaSBox Pro** | $499/year | + Mobile app, push notifications, voting, 3 admins | Medium events (101-300 racers) |
| **SaaSBox Enterprise** | $799/year | + Custom branding, API access, analytics, unlimited admins | Large events (300+) |

### Add-on Pricing

| Feature | Price | Description |
|---------|-------|-------------|
| HLS Streaming | +$99/year | Live video feeds to mobile app |
| SMS Notifications | +$0.02/msg | Beyond included quota (1000 msgs) |
| Custom Domain | +$49/year | yourderby.soapboxderbynet.com |
| Priority Support | +$199/year | Dedicated support channel |

### Non-Profit Discount: 25% off all tiers

### Payment: Stripe (self-service checkout + subscription management)

---

## 2. Feature Matrix

### Free Tier (DerbyPi - On-Premise)
- Full race management (scheduling, results, awards)
- Hardware integration (finish timer, start timer, displays)
- Elimination tournament system
- Kiosk displays (standings, on-deck, results)
- MQTT messaging architecture
- Broadcast messaging (local only)
- SQLite database (offline operation)
- **Works completely offline**

### SaaSBox Starter ($299/year)
All Free features plus:
- Cloud sync (race data, results - PII stripped)
- Public standings webpage (pinny + class + times only)
- Basic analytics dashboard
- Log sync for support

### SaaSBox Pro ($499/year)
All Starter features plus:
- **Mobile App Access** (iOS/Android PWA)
- **Push Notifications** ("Pinny #1234 races in 5 minutes")
- **Favourite-a-Racer** (by pinny number, not name)
- **Audience Voting** (best car design, sportsmanship)
- **Predictions Game** (pick heat winners)
- Parent portal (race schedule, standings, notifications)
- 3 cloud admin accounts
- 1000 SMS/push notifications included

### SaaSBox Enterprise ($799/year)
All Pro features plus:
- **White-label branding** (logo, colors, fonts)
- **Custom subdomain** (yourderby.soapboxderbynet.com)
- **API access** (for custom integrations)
- **Advanced analytics** (year-over-year comparison)
- **Sponsor showcase** (rotating sponsor displays)
- **Ad slots** (configurable advertisement placements)
- Unlimited admin accounts
- Priority support
- Custom elimination configurations

---

## 3. Technical Architecture

### System Topology (Your Existing Infrastructure)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SAASBOX CLOUD (Your Ubuntu VPS)                          │
│                                                                              │
│  ┌────────────────┐     ┌────────────────────────────────────────────────┐  │
│  │  nginx-proxy   │     │              Docker Network                    │  │
│  │  (existing)    │────►│  ┌─────────────┐  ┌─────────────┐             │  │
│  │  + letsencrypt │     │  │ saasbox-api │  │  postgres   │             │  │
│  └────────────────┘     │  │  (FastAPI)  │  │  (data)     │             │  │
│         │               │  └──────┬──────┘  └──────┬──────┘             │  │
│         ▼               │         └─────────┬──────┘                    │  │
│  soapboxderbynet.com    │                   │                           │  │
│  ├─ / (landing)         │  ┌────────────────┴───────────────┐           │  │
│  ├─ /api (FastAPI)      │  │ redis (cache + sessions)       │           │  │
│  └─ /app (Flutter web)  │  └────────────────────────────────┘           │  │
│                         └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ Sync (HTTPS, one-way)
                                     │ POST /api/v1/sync/ingest
                                     │ PII-stripped data only
                                     │
┌────────────────────────────────────┼──────────────────────────────────────────┐
│                           ON-PREMISE (DerbyPi)                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   DerbyNet   │  │  Race Server │  │   MQTT       │  │   Finish     │     │
│  │   PHP        │  │  + SyncClient│  │   Broker     │  │   Timer      │     │
│  │              │  │   (Python)   │  │ (Mosquitto)  │  │   (RPi)      │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         └──────────────────┴─────────────────┴─────────────────┘             │
│                                    │                                          │
│                          ┌─────────┴─────────┐                               │
│                          │   SQLite          │  ← SOURCE OF TRUTH            │
│                          │   (Local DB)      │    (works offline)            │
│                          └───────────────────┘                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Data Sync Protocol

**Direction:** One-way only (On-Premise → Cloud)
**On-premise is ALWAYS source of truth**

**Data Synced (PII-Stripped):**
```json
{
  "event_id": "uuid",
  "timestamp": "2026-06-15T14:30:00Z",
  "racers": [
    {"pinny": 1234, "class": "Junior", "age_group": "8-10"}
  ],
  "results": [
    {"pinny": 1234, "round": 1, "heat": 3, "lane": 2, "time": 12.345, "place": 1}
  ],
  "schedule": [
    {"round": 1, "heat": 4, "lanes": [1234, 5678, 9012]}
  ],
  "standings": [
    {"pinny": 1234, "class": "Junior", "rank": 1, "status": "advancing"}
  ]
}
```

**Data NEVER Synced (PII Protected):**
- Racer names (first, last)
- Parent contact info
- Photos (unless explicit opt-in)
- Home addresses
- Registration details

### API Gateway Structure

```
https://api.soapboxderbynet.com/v1/
├── /auth/
│   ├── POST /login          # OAuth2/JWT authentication
│   ├── POST /refresh        # Token refresh
│   └── GET  /me             # Current user profile
│
├── /events/{event_id}/
│   ├── GET  /standings      # Public standings (PII-stripped)
│   ├── GET  /schedule       # Current/upcoming heats
│   ├── GET  /results        # Completed heat results
│   └── GET  /live           # WebSocket upgrade for real-time
│
├── /notifications/
│   ├── POST /subscribe      # Subscribe to racer (by pinny)
│   ├── DELETE /unsubscribe  # Remove subscription
│   └── GET  /preferences    # Notification settings
│
├── /voting/
│   ├── GET  /ballots        # Available votes
│   ├── POST /cast           # Submit vote
│   └── GET  /results        # Vote tallies (when closed)
│
├── /sync/                   # Internal (on-premise → cloud)
│   ├── POST /ingest         # Race data sync
│   └── POST /logs           # Log sync (existing logsync.py)
│
└── /admin/                  # Tenant management
    ├── GET  /tenants        # List tenants
    ├── POST /tenants        # Create tenant
    └── GET  /usage          # Usage metrics
```

---

## 4. Implementation Phases (MVP for June 2026)

### Sprint 1: API Foundation (Weeks 1-3)
**Goal:** Backend API for Flutter app

**Deliverables:**
1. `extras/saasbox/api/` - FastAPI backend
   - JWT authentication (for Flutter app)
   - Public endpoints (no auth for standings)
   - OpenAPI auto-documentation

2. Database schema (PostgreSQL container)
   - `events`, `racers`, `results`, `standings` tables
   - `subscriptions` (favourite-a-racer)
   - `device_tokens` (push notifications)

3. Docker Compose integration
   - Add to existing nginx-proxy network
   - `api.soapboxderbynet.com` subdomain

**Key Files:**
```
extras/saasbox/
├── api/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings from env vars
│   ├── auth.py              # JWT tokens
│   ├── db.py                # SQLAlchemy models
│   ├── routes/
│   │   ├── public.py        # /standings, /schedule (no auth)
│   │   ├── user.py          # /subscribe, /favorites (JWT)
│   │   └── sync.py          # /ingest (API key auth)
│   └── schemas.py           # Pydantic models
├── docker-compose.yml       # API + Postgres + Redis
├── Dockerfile
└── requirements.txt
```

### Sprint 2: On-Premise Sync (Weeks 4-5)
**Goal:** DerbyPi pushes data to cloud

**Deliverables:**
1. Extend `logsync.py` → `racesync.py`
   - Sync race results after each heat
   - Sync standings after round completion
   - PII filter (strip names, keep pinny/class)

2. Environment config on DerbyPi
   - `SAASBOX_API_KEY` - per-event auth token
   - `SAASBOX_EVENT_ID` - UUID for this event
   - `SAASBOX_ENABLED=true/false`

3. Sync trigger hooks
   - After `action.result.write` completes
   - After round advancement

**Key Files:**
```
extras/soapbox/infra/server/
├── racesync.py              # NEW: Race data sync client
└── pii_filter.py            # NEW: Strip PII from sync payload
```

### Sprint 3: Flutter Integration (Weeks 6-8)
**Goal:** Connect Flutter app to API

**Deliverables (coordinate with Flutter dev):**
1. API client in Flutter
   - GET `/api/v1/events/{id}/standings`
   - GET `/api/v1/events/{id}/schedule`
   - POST `/api/v1/subscribe` (favourite racer)

2. Push notifications
   - Firebase Cloud Messaging setup
   - POST device token to `/api/v1/devices`
   - "Your racer is up next" trigger

3. WebSocket for live updates
   - `/api/v1/events/{id}/live` endpoint
   - Real-time standings refresh

### Sprint 4: Engagement Features (Weeks 9-12)
**Goal:** Premium tier features

**Deliverables:**
1. Voting system
   - Ballot creation via admin
   - Vote submission endpoint
   - Results display (when closed)

2. Predictions game
   - Heat winner picks
   - Points leaderboard
   - End-of-event prizes display

3. Sponsor showcase
   - Configurable ad slots
   - Rotation logic
   - Click tracking

### Sprint 5: Payments & Polish (Weeks 13-16)
**Goal:** Monetization + production hardening

**Deliverables:**
1. Stripe integration
   - Checkout session creation
   - Webhook for subscription status
   - Customer portal link

2. Admin dashboard (simple)
   - Event creation/management
   - View sync status
   - Usage metrics

3. Production hardening
   - Rate limiting
   - Error monitoring (Sentry)
   - Backup strategy

---

## 5. Critical Files to Create/Modify

### New Cloud Components (extras/saasbox/)

| File | Purpose |
|------|---------|
| `api/main.py` | FastAPI app with CORS, middleware |
| `api/config.py` | Pydantic settings from env vars |
| `api/auth.py` | JWT token creation/validation |
| `api/db.py` | SQLAlchemy models + engine |
| `api/schemas.py` | Pydantic request/response models |
| `api/routes/public.py` | `/standings`, `/schedule` (no auth) |
| `api/routes/user.py` | `/subscribe`, `/favorites` (JWT) |
| `api/routes/sync.py` | `/ingest` (API key for DerbyPi) |
| `api/routes/admin.py` | `/events`, `/usage` (admin JWT) |
| `docker-compose.yml` | API + Postgres + Redis containers |
| `Dockerfile` | Python 3.11 + uvicorn |

### On-Premise Modifications (extras/soapbox/)

| File | Change |
|------|--------|
| `infra/server/racesync.py` | NEW: Sync client extending logsync.py pattern |
| `infra/server/pii_filter.py` | NEW: Strip names/photos before sync |
| `infra/server/derbyRace.py` | Add sync hook after race completion |

### Flutter App Integration (coordinate externally)

| Endpoint | Flutter Screen |
|----------|----------------|
| `GET /events/{id}/standings` | Standings list view |
| `GET /events/{id}/schedule` | Upcoming heats view |
| `POST /subscribe` | Favourite-a-racer button |
| `WS /events/{id}/live` | Real-time refresh |
| `POST /devices` | Register for push notifications |

---

## 6. Verification Plan

### Testing Strategy

1. **Unit Tests** - pytest for all FastAPI routes
2. **Integration Tests** - Docker Compose end-to-end
3. **PII Audit** - Verify no names in cloud database
4. **Load Tests** - Simulate 500+ concurrent users on standings page

### Acceptance Criteria (MVP)

| Feature | Test Method | Pass Criteria |
|---------|-------------|---------------|
| Cloud sync | Inspect cloud DB after sync | No names, only pinny + class + times |
| Public standings | Browser without login | See standings without auth |
| Push notifications | Trigger heat assignment | Alert received within 30s |
| Favourite racer | Subscribe to pinny | Receive notification when racing |
| Stripe checkout | Complete test purchase | Subscription active in DB |

### End-to-End Test Flow
```
1. DerbyPi records heat result
2. racesync.py sends to cloud (PII stripped)
3. Flutter app polls /standings
4. User sees updated results
5. Subscribed user gets push notification
```

---

## 7. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| PII leak to cloud | Strict `pii_filter.py`, audit logs, unit tests |
| Cloud outage affects races | On-premise is primary, cloud is enhancement only |
| Stripe integration complexity | Use Stripe Checkout (hosted), not custom forms |
| June deadline tight | Focus on MVP (standings + notifications), defer voting |
| Flutter/API mismatch | OpenAPI spec shared, generate Flutter client |

---

## 8. MVP Scope for June 2026

### Must Have (MVP)
- Public standings API (no auth)
- DerbyPi → Cloud sync (PII stripped)
- Flutter app connected to API
- Push notifications (FCM)
- Favourite-a-racer by pinny

### Nice to Have (if time permits)
- Voting system
- Predictions game
- Stripe payments (can invoice manually initially)

### Defer to v2 (post-June)
- White-label branding
- Analytics dashboard
- Multi-event management
- Enterprise features

---

## Summary

**5-month roadmap** to MVP for June 2026 race season:

| Sprint | Weeks | Deliverable |
|--------|-------|-------------|
| 1 | 1-3 | FastAPI backend + Postgres on your VPS |
| 2 | 4-5 | DerbyPi sync client with PII filtering |
| 3 | 6-8 | Flutter app connected + push notifications |
| 4 | 9-12 | Voting, predictions (stretch goal) |
| 5 | 13-16 | Stripe + polish |

**Start with:** Sprint 1 (API foundation) - this unlocks Flutter integration and validates the architecture.

**First file to create:** `extras/saasbox/api/main.py` (FastAPI entry point)
