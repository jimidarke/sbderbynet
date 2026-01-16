# SoapboxDerbyNet SaaS API

Secure, multi-tenant API middleware for soapbox derby race management.

## Quick Start

### Development

```bash
# Copy environment variables
cp .env.example .env
# Edit .env with your configuration

# Start services
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Production

```bash
# Configure production secrets in .env
docker compose up -d
```

## Architecture

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+ with Row-Level Security
- **Cache**: Redis for race data and rate limiting
- **Auth**: Firebase Authentication (Google OAuth)
- **Logging**: Alert Manager integration

## API Overview

Base URL: `https://api.soapboxderbynet.com/v1`

| Module | Prefix | Purpose |
|--------|--------|---------|
| Auth | `/auth` | Firebase token exchange, refresh |
| Organizations | `/orgs` | Multi-tenant management |
| Events | `/orgs/{orgId}/events` | Race events |
| Races | `/orgs/{orgId}/events/{eventId}/races` | Heats, results |
| Racers | `/orgs/{orgId}/events/{eventId}/racers` | Participants |
| Favorites | `/me` | User preferences, notifications |
| Audience | `/orgs/{orgId}/events/{eventId}/audience` | Predictions, cheers, polls |
| Donations | `/donations` | Stripe integration |
| Devices | `/orgs/{orgId}/devices` | DerbyPi management |
| Admin | `/admin` | System administration |

## Authentication

### User Auth (Firebase)

1. Client authenticates with Firebase (Google Sign-In)
2. Client exchanges Firebase ID token for API JWT
3. API JWT used for subsequent requests

```bash
# Exchange Firebase token
curl -X POST https://api.soapboxderbynet.com/v1/auth/firebase/verify \
  -H "Content-Type: application/json" \
  -d '{"id_token": "eyJ..."}'
```

### Device Auth (RSA Signatures)

DerbyPi devices authenticate using RSA-2048 key pairs:

1. Device generates keypair on first boot
2. Admin registers public key in dashboard
3. Device signs each request with private key

## Multi-Tenancy

- PostgreSQL Row-Level Security (RLS) isolates tenant data
- `org_id` column on all tenant-scoped tables
- Automatic context setting via middleware

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Type checking
mypy app/

# Linting
ruff check .
```

## Environment Variables

See `.env.example` for all configuration options.

## Project Structure

```
api/
├── app/
│   ├── main.py          # FastAPI entry point
│   ├── config.py        # Settings from environment
│   ├── database.py      # PostgreSQL with async SQLAlchemy
│   ├── redis_client.py  # Redis for caching
│   └── dependencies.py  # FastAPI dependencies
├── modules/
│   ├── auth/            # Authentication
│   ├── orgs/            # Organizations
│   ├── events/          # Events
│   ├── races/           # Races
│   ├── racers/          # Racers
│   ├── favorites/       # User favorites
│   ├── audience/        # Predictions, cheers, polls
│   ├── donations/       # Stripe donations
│   ├── devices/         # Device management
│   └── admin/           # System admin
├── middleware/
│   ├── tenant.py        # Multi-tenant context
│   └── logging.py       # Alert Manager integration
├── models/              # SQLAlchemy models
├── schemas/             # Pydantic schemas
├── migrations/          # Alembic migrations
└── tests/               # Test suite
```

## License

Proprietary - SoapboxDerbyNet
