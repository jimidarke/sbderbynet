# SaaS Backend

Cloud backend planned for premium subscription features (push notifications, multi-event tenancy, paid integrations). **Early stage** — FastAPI + Docker.

Lives at `extras/saasbox/api/`. Python (FastAPI), Docker, pytest harness.

!!! note "Status"
    The standalone SaaS backend is in pre-launch. The race-day cloud twin (`uisp.darketech.ca`) is a separate, working stack — see [VPS Procedures](../operations/vps-procedures.md). Don't confuse the two.

---

## What's here

- FastAPI service skeleton under `api/`
- Docker / `docker-compose` for local development
- Test harness (pytest)
- Authentication uses an RSA keypair generated on the race Pi during DerbyPi bootstrap (see [DerbyPi](derbypi.md)) — devices register their public key with the SaaS dashboard to enable cloud features

---

## Planned features

- **Push notifications** via Firebase Cloud Messaging — design captured in `extras/saasbox/FCM_NOTIFICATION_PLAN.md`. No implementation yet.
- Multi-tenant event hosting (each org gets a sandbox; design lifted from the cloud-twin tenant model — see [Cloud Multi-Tenancy](../architecture/overview.md#) when it's documented separately).
- Subscription billing.

---

## Files

- `extras/saasbox/api/` — FastAPI service
- `extras/saasbox/api/README.md` — getting started for the service itself
- `extras/saasbox/FCM_NOTIFICATION_PLAN.md` — push-notification design intent

(Two files in this folder — `README.md` placeholder and `CLIENTNODE.md` describing an external alert service — are explicitly **not** part of SBDerbyNet docs and are excluded from this site.)
