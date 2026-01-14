# Deployment - Coolify on Icculus

Open Valley is deployed via [Coolify](https://coolify.io/) on the `icculus` server, accessible via Tailscale.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Coolify on Icculus                       │
│                murmuration.starlingstrategy.com             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────────────────────┐    │
│  │ openvalley-db│      │ openvalley-app (planned)     │    │
│  │ PostgreSQL 16│◄────►│ FastAPI + Next.js            │    │
│  │ + pgvector   │      │                              │    │
│  │ + PostGIS    │      │ openvalley.maconphillips.com │    │
│  │              │      └──────────────────────────────┘    │
│  │ Port: 5433   │                                          │
│  └──────────────┘                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Current Status

| Service | Status | Domain |
|---------|--------|--------|
| **openvalley-db** | Running | Internal (Tailscale) |
| **openvalley-app** | Planned | openvalley.maconphillips.com |

## Database Connection

### Via Tailscale (internal)

```bash
# Connection string
postgresql://openvalley:<password>@icculus:5433/openvalley

# Or via IP
postgresql://openvalley:<password>@100.75.27.44:5433/openvalley
```

### Environment Variables

Set in Coolify for `openvalley-db`:
- `POSTGRES_USER=openvalley`
- `POSTGRES_PASSWORD=<see Coolify>`
- `POSTGRES_DB=openvalley`

### Dockerfile (Database)

```dockerfile
FROM pgvector/pgvector:pg16
RUN apt-get update && apt-get install -y postgresql-16-postgis-3 && rm -rf /var/lib/apt/lists/*
```

Custom Docker options: `--network-alias=openvalley-db -v openvalley_pgdata:/var/lib/postgresql/data`

## Coolify API Access

Base URL: `https://murmuration.starlingstrategy.com/api/v1`

```bash
# List all resources
curl -H "Authorization: Bearer <token>" \
  "https://murmuration.starlingstrategy.com/api/v1/resources"

# Get database environment variables
curl -H "Authorization: Bearer <token>" \
  "https://murmuration.starlingstrategy.com/api/v1/applications/m44kg8ww4k0wsgcg4gosgco8/envs"
```

API token stored separately (not in repo).

## Migration Plan

### Phase 1: Database (Complete)
- [x] Create PostgreSQL container with pgvector + PostGIS
- [x] Configure persistent storage (`openvalley_pgdata`)
- [x] Import data from local database
- [x] Verify data integrity (1,823 parcels, 618 STR listings, etc.)

### Phase 2: Application (TODO)
- [ ] Create `openvalley-app` service in Coolify
- [ ] Configure build from GitHub repo
- [ ] Set environment variables:
  - `DATABASE_URL=postgresql://openvalley:<password>@openvalley-db:5432/openvalley`
  - `ADMIN_TOKEN=<secure token>`
  - `NODE_ENV=production`
- [ ] Configure domain: `openvalley.maconphillips.com`
- [ ] Set up SSL via Coolify/Traefik

### Phase 3: DNS & Go-Live
- [ ] Point `openvalley.maconphillips.com` to Coolify
- [ ] Verify frontend loads
- [ ] Test API endpoints
- [ ] Deprecate local Docker setup

## Local Development

For local development, continue using `docker-compose.yml`:

```bash
docker compose up -d
# Database at localhost:5432
# API at localhost:8999
# Frontend at localhost:3000
```

To connect to production database locally (for debugging):

```bash
PGPASSWORD='<password>' psql -h icculus -p 5433 -U openvalley -d openvalley
```

## Data Sync

Currently data is imported via scripts run locally, then the database was copied to Coolify. Future options:

1. **Run import scripts against Coolify DB directly** (preferred)
   ```bash
   DATABASE_URL=postgresql://openvalley:<password>@icculus:5433/openvalley \
     uv run python scripts/import_parcels.py --import
   ```

2. **pg_dump/pg_restore** for full refreshes
   ```bash
   # Export from local
   pg_dump -h localhost -U openvalley openvalley > backup.sql

   # Import to Coolify
   PGPASSWORD='<password>' psql -h icculus -p 5433 -U openvalley -d openvalley < backup.sql
   ```

## Troubleshooting

### Can't connect to database
1. Check Tailscale is connected: `tailscale status | grep icculus`
2. Verify port is open: `nc -zv 100.75.27.44 5433`
3. Check container is running via Coolify UI or API

### Database container not starting
Check logs in Coolify UI → openvalley-db → Logs

### Need to rebuild database
```bash
# Via Coolify API
curl -X POST -H "Authorization: Bearer <token>" \
  "https://murmuration.starlingstrategy.com/api/v1/applications/m44kg8ww4k0wsgcg4gosgco8/restart"
```
