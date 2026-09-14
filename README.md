# Dental Claim Scrubber

A rule-based system for validating dental insurance claims before submission to reduce claim denials, improve claim quality, and provide reproducible validation results.

> 🚧 **Project Status:** This project is currently under development.

---

## Overview

Dental Claim Scrubber validates dental insurance claims before they are submitted to an insurance provider. It helps identify common errors early, reducing claim denials and improving the accuracy and consistency of submitted claims.

---

## Features

- Rule-based claim validation
- Reproducible scrub runs
- React frontend for reviewing claim validation results
- Python backend API
- Audit trail for validation results
- Docker-based development environment

---

## Technology Stack

### Frontend

- React 18
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui

### Backend

- Python
- PostgreSQL 16
- Redis 7
- MinIO

### Development Tools

- Docker Compose
- GitHub Actions
- ESLint
- Prettier
- Ruff
- MyPy
- Pytest

---

## Project Structure

```text
.
├── frontend/
├── backend/
├── docs/
├── .github/
├── docker-compose.yml
├── CONTRIBUTING.md
├── Makefile
└── README.md
```

---

## Prerequisites

Before running the project, make sure you have installed:

- Git
- Node.js
- Python 3.12+
- Docker Desktop (or Docker Engine with Docker Compose)

---

## Installation

Repository setup instructions will be added once the project structure is finalized.

```bash
git clone <repository-url>
cd <repository-name>
```

---

## Running the Project

Follow these steps in order to get the system running.

### 1. Infrastructure (Docker)
The easiest way to run the supporting services (Database, Cache, Storage, and Identity Provider) is using Docker Compose.

```bash
docker compose up -d
```

#### Keycloak Configuration
Once Keycloak is running at `http://localhost:8080`, you must configure the authentication:

1. **Admin Login**: Go to `http://localhost:8080` and log in with `admin` / `admin`.
2. **Create Realm**: Create a new realm named `insurance`.
3. **Create Client**:
   - **Client ID**: `insurance-frontend`
   - **Client Protocol**: `openid-connect`
   - **Client authentication**: **Off** (This makes it a Public Client)
   - **Authorization**: **Off**
   - **Valid Redirect URIs**: `http://localhost:5173/*`
   - **Web Origins**: `http://localhost:5173`

### 2. Backend API
The backend provides the logic and connects the frontend to the identity provider.

```bash
# Navigate to backend folder
cd backend

# Install dependencies (using uv)
uv sync

# Run the API
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend UI
The user interface allows you to manage claims and review findings.

```bash
# Open a new terminal tab
cd frontend

# Install dependencies (do this once)
npm install

# Start the development server
npm run dev
```

Once the frontend is running, open `http://localhost:5173` in your browser.


---

## Development

Common development commands:

```bash
make dev
make build
make test
make lint
```

### Backend load testing (k6)

The scrub endpoint (`POST /api/v1/claims/{claim_id}/scrub`) has a k6 load-test
scenario that runs 50 concurrent virtual users against a 20-line claim and
fails if `p(95) > 300ms` or the error rate exceeds 1%.

Prerequisites: local Postgres running (via `docker compose up -d`) at the
`DATABASE_URL` in `backend/.env`/`app/config.py`, migrations applied
(`make migrate`), an installed `k6` binary, and the backend running
(e.g. `uvicorn app.main:app` from `backend/`).

```bash
cd backend
make load-test-seed    # seeds tenant/patient/provider/policy/20-line claim, caches IDs
make load-test-token   # prints a bearer JWT for the seeded tenant
export TOKEN="$(make load-test-token)"
export CLAIM_ID="$(cat loadtest/.seed-state.json | python -c "import json,sys; print(json.load(sys.stdin)['claim_id'])")"
k6 run loadtest/scrub.js
```

`loadtest/scrub.js` reads `BASE_URL` (default `http://127.0.0.1:8000`),
`TOKEN`, and `CLAIM_ID` from env. Seed/token utilities live in
`backend/loadtest/` (`python -m loadtest` and `python -m loadtest.make_token`).

The scenario spreads concurrent users across the seeded claim pool (50 claims
by default via `CLAIM_COUNT`), keeping the pool single-claim `CLAIM_ID` for a
pure stress test.

#### Measured results (dev box: 16 cores, Docker/WSL2 Postgres, k6 2.2.0)

| Workers | p95       | Throughput | Errors/checks          |
|---------|-----------|------------|------------------------|
| 1       | 3.28s     | ~29 rps    | 0 errors, 100% checks |
| 4       | 685ms     | 87 rps     | 0 errors, 100% checks |
| 8       | 633ms     | 92 rps     | 0 errors, 100% checks |

The `p(95) < 300ms` gate does **not** pass on this dev box. Profiling shows the
bottleneck is infrastructure, not application code:

- The rule pipeline itself runs in ~1.3ms per claim; a scrub takes **9 SQL
  queries** (N+1 fixed, regression-guarded at `<=15`).
- 1 -> 4 workers cuts p95 by ~5x (GIL-bound sync middleware is the first wall).
- 4 -> 8 workers plateaus at ~630ms / ~92 rps — the shared Docker/WSL2
  Postgres saturates. On production hardware (8+ uvicorn workers against a
  dedicated Postgres) the target is expected to be reachable.

connection pool sizing is tunable via `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` (env),
and the claim-status metric refresh is throttled (see `refresh_claim_gauges`).

---

### Security hardening

Track 3 of the production plan. All implemented surfaces below are covered by
automated tests and were verified against a live server (`uvicorn`, Redis via
docker-compose) unless noted.

#### Rate limiting (T3a)

`RateLimitMiddleware` (app/core/rate_limit.py): Redis-backed fixed-window
(60 req/min on `/auth/`, `/api/v1/insurance-cards/`, `/api/v1/claims/`;
300 req/min elsewhere) with automatic in-memory fallback when Redis is
unreachable. `GET /health` and `/metrics` are exempt. 429s carry
`Retry-After`. Exempt paths and `RATE_LIMIT_ENABLED=false` keep k6/health
scans from tripping it.

- Verified live: 60 allowed requests then 429 with `Retry-After: 60`.

#### Security headers / CSP (T3b)

`SecurityHeadersMiddleware` (app/core/security_headers.py) sets CSP
(`script-src 'self'`, no `unsafe-inline`, `frame-ancestors 'none'`),
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`, and
HSTS on HTTPS only.

- Verified live on `/health` + asserted in tests.

#### Upload MIME sniffing + size caps (T3c)

`app/core/uploads.py` validates magic bytes against a JPEG/PNG/WebP/PDF
allowlist (415 on mismatch / disallowed) and enforces
`MAX_UPLOAD_SIZE_BYTES` (10 MB default, 413 otherwise). OCR and the new
attachment endpoint both share these helpers.

- Verified live: PNG upload accepted (201), JPEG-bytes-declared-as-PNG → 415.

#### Randomized S3 keys + 5-minute pre-signed URLs (T3d)

`POST /api/v1/claims/{claim_id}/attachments` (requires `CLAIM_WRITE`) stores
under `tenants/{tenant}/claims/{claim}/attachments/{uuid}.{ext}` via
`S3ObjectStorage`; `GET .../attachments/{id}/url` (requires `CLAIM_READ`)
returns a 5-minute pre-signed URL (`S3_PRESIGN_EXPIRY_SECONDS=300`), tenant
and claim scoped (403/404 on mismatch).

- Verified live: upload → 201, presign `expires_in: 300`, download bytes
  from the pre-signed URL matched exactly. (S3 smoke used a local
  S3-compatible mock; `minio/minio` images are no longer pullable on Docker
  Hub and the MinIO OSS binary distribution was archived 2025.)

#### Field-level member-ID encryption (T3e)

`InsurancePolicy.member_id` encrypts to `member_id_enc` (Fernet,
`app/core/field_encryption.py`) plus a `member_id_last4` search column;
raw member IDs never stored in plaintext. Staging/production `Settings`
validation rejects the dev-default Fernet key and `minioadmin` S3 creds.

- Verified live: ciphertext != plaintext, `member_id_last4` correct,
  decrypt round-trip; staging startup with the default key fails with
  `FIELD_ENCRYPTION_KEY must be rotated...`.
- Migration `4867fb7c0ede` adds the two columns (applied to dev DB).

#### Dependency audits + secret scan (T3f)

- backend: `pip-audit --local` → **0 known vulnerabilities**.
- frontend: `npm audit` had 2 high + 4 moderate (`fast-uri`, `js-yaml`, ...);
  resolved via `npm audit fix` (→ **0 vulnerabilities**), build verified.
- gitleaks (8.30.1 + custom config in `.gitleaks.toml`): only findings were a
  documented dev-only default key (now allowlisted) + `.venv` third-party
  noise excluded by git-tracked scan.
- All three are CI gates in `.github/workflows/ci.yaml` (`security-audit` job).

---

## Contributing

Please read **CONTRIBUTING.md** before creating branches or submitting Pull Requests.


