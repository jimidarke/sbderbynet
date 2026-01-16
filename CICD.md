# CI/CD Strategy

A three-tier deployment strategy optimized for sole developer workflow: **Local → Staging → Production**.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     LOCAL DEVELOPMENT                            │
│  Docker with bind mounts for instant hot-reload                 │
│  Edit code → refresh browser → see changes                      │
│                                                                  │
│  No git commits needed for testing iterations                   │
└─────────────────────────────────────────────────────────────────┘
                             │
                      git push develop
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GITHUB ACTIONS                               │
│                                                                  │
│  On push to develop:                                            │
│    → Build Docker images                                        │
│    → Push to ghcr.io (GitHub Container Registry)                │
│    → SSH deploy to staging                                      │
│                                                                  │
│  On merge to main:                                              │
│    → Build Docker images                                        │
│    → Push to ghcr.io                                            │
│    → SSH deploy to production                                   │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        SERVER                                    │
│                                                                  │
│  ┌─────────────────────┐    ┌─────────────────────┐            │
│  │  STAGING            │    │  PRODUCTION         │            │
│  │  dev.soapbox...     │    │  soapboxderbynet... │            │
│  │                     │    │                     │            │
│  │  Image tag: develop │    │  Image tag: main    │            │
│  │  Volumes: *_staging │    │  Volumes: *_prod    │            │
│  └─────────────────────┘    └─────────────────────┘            │
│                                                                  │
│  nginx-proxy (shared reverse proxy with Let's Encrypt)          │
└─────────────────────────────────────────────────────────────────┘
```

## Workflow Summary

| Scenario | Action | Result |
|----------|--------|--------|
| Quick testing | Edit locally | Instant hot-reload, no commits |
| Ready for review | `git push origin develop` | Auto-deploys to dev.soapboxderbynet.com |
| Ready for production | Merge develop → main | Auto-deploys to soapboxderbynet.com |
| Emergency hotfix | Push directly to main | Auto-deploys (use sparingly) |

## Local Development

```bash
# Start local stack
cd installer/docker-local
docker compose up -d

# Access at http://localhost:8080/derbynet/
# Edit PHP/Python files - changes reflect immediately
```

**How it works**: Bind mounts overlay your local `website/` directory into the container, so file changes are instant without rebuilding.

## Deployment Pipeline

### Staging (develop branch)

1. Push to `develop` branch
2. GitHub Actions builds images, tags as `develop`
3. Pushes to `ghcr.io/your-org/soapboxderbynet-web:develop`
4. SSHs to server, runs `docker compose pull && docker compose up -d`
5. Live at `dev.soapboxderbynet.com`

### Production (main branch)

1. Create PR from `develop` → `main`
2. Merge PR
3. GitHub Actions builds images, tags as `main`
4. Pushes to `ghcr.io/your-org/soapboxderbynet-web:main`
5. SSHs to server, deploys to production
6. Live at `soapboxderbynet.com`

## Server Directory Structure

```
/opt/derbynet/
├── staging/
│   ├── docker-compose.yml
│   └── .env                  # VIRTUAL_HOST=dev.soapboxderbynet.com
│
├── production/
│   ├── docker-compose.yml
│   └── .env                  # VIRTUAL_HOST=soapboxderbynet.com
│
└── shared/
    └── nginx-proxy/          # Let's Encrypt + reverse proxy
```

## Docker Images

| Image | Purpose | Registry |
|-------|---------|----------|
| `soapboxderbynet-web` | PHP/Nginx web application | ghcr.io |
| `soapboxderbynet-server` | Python race server | ghcr.io |
| `eclipse-mosquitto:2` | MQTT broker | Docker Hub (official) |

## GitHub Secrets Required

| Secret | Purpose |
|--------|---------|
| `SERVER_HOST` | Server IP or hostname |
| `SERVER_USER` | SSH username (e.g., `deploy`) |
| `SERVER_SSH_KEY` | Private SSH key for deployment |

## Permission Strategy

**Production**: Docker-managed named volumes - no permission conflicts since containers run isolated.

**Local Development**: Containers run as root, bind mounts work because:
- Alpine containers don't enforce strict user separation
- Data dirs are 777 inside container
- Host files remain owned by your user

If permission issues occur locally:
```bash
chmod -R 777 website/  # Nuclear option for local dev only
```

## Rollback

```bash
# On server, rollback to previous image
cd /opt/derbynet/production
docker compose pull ghcr.io/your-org/soapboxderbynet-web:previous-sha
docker compose up -d

# Or via git
git revert HEAD
git push origin main  # Triggers new deploy with reverted code
```

## Key Files

| File | Purpose |
|------|---------|
| `installer/docker-local/docker-compose.yml` | Local dev with hot-reload |
| `installer/docker-cloud/docker-compose.staging.yml` | Staging server config |
| `installer/docker-cloud/docker-compose.production.yml` | Production server config |
| `.github/workflows/deploy.yml` | CI/CD pipeline |

## Benefits Over SFTP

1. **No permission conflicts** - Docker manages volumes
2. **Full audit trail** - Every change in git history
3. **Easy rollback** - Revert commit or pull old image
4. **Reproducible** - Same image everywhere
5. **No sync drift** - Code baked into immutable images
6. **Fast iteration** - Local bind mounts = instant feedback

## Future Enhancements

- [ ] Add automated tests to CI pipeline
- [ ] Database migration automation
- [ ] Blue-green deployments for zero-downtime
- [ ] Slack/Discord deploy notifications
- [ ] Automated version bumping on release
