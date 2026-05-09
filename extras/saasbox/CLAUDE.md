# SaaSBox Cloud Backend

## Purpose

Premium cloud features for SBDerbyNet — subscription management, push notifications, and cloud-hosted race data. Runs in a private cloud VPC as a Docker-containerized service.

## How It Fits

Optional cloud layer that sits alongside the on-premise DerbyNet system. The DerbyPi (`extras/derbypi/`) syncs data to SaaSBox for remote access. The Flutter app will connect to this API for mobile features.

## Key Files

- `api/` — FastAPI backend (Dockerfile, docker-compose.yml, requirements.txt)
- `api/.env.example` — Environment variable configuration template
- `FCM_NOTIFICATION_PLAN.md` — Firebase Cloud Messaging integration plan

## Tech Stack

- Python (FastAPI), Docker, docker-compose
- pytest for testing

## Dependencies

- Docker and Docker Compose
- See `api/requirements.txt` for Python dependencies

## Common Tasks

- **Run locally**: `cd api && docker-compose up`
- **Test**: `cd api && pytest`
- **Configure**: Copy `api/.env.example` to `api/.env` and edit

## Gotchas

- **Early stage**: Limited documentation and features — this is pre-launch
- **Deployment**: Docker-only, no bare-metal setup documented

## Related Docs

- [api/README.md](api/README.md) — API layer documentation
- [FCM_NOTIFICATION_PLAN.md](FCM_NOTIFICATION_PLAN.md) — Push notification architecture
- [docs/business/COMMERCIALIZATION.md](../../docs/business/COMMERCIALIZATION.md) — Business model and pricing
