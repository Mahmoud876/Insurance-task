# Decision log — Track 3 security hardening

Captured: 2026-09-14. Scope: every implementation choice made during Track 3 (security hardening), with the reasoning behind it, the trade-off it accepted, and where to review the code. Written so that a reviewer who did not watch the work happen can either approve it or reverse any item.

General: nothing in this log is irreversible. Each item names the file(s) to inspect if you want to change it.

---

## Cross-cutting decisions

| # | Decision | Why | Review location |
|---|----------|-----|-----------------|
| 1 | Backend stays synchronous (sync SQLAlchemy, sync endpoints) | Async was possible but buys little here and risks churn across the whole app | `backend/app/` |
| 2 | Tests run in a clean mode: `ENVIRONMENT=test` + `RATE_LIMIT_ENABLED=false` set at the top of `conftest.py` before app imports | Keeps tests deterministic and unthrottled | `backend/tests/conftest.py` |
| 3 | Middleware order (outermost to innermost): CORS → RateLimit → SecurityHeaders → RequestLogging → Authentication → TenantIsolation | Order is load-bearing: rate limiting sees every request, auth runs late, tenant isolation runs last so unauthenticated requests die early | `backend/app/main.py` |

## A — Rate limiting (T3a)

- **Chosen:** Redis-backed fixed-window limiter with automatic in-memory fallback when Redis is unavailable. Limits: 60/min on `/auth/`, `/api/v1/insurance-cards/`, `/api/v1/claims/`; 300/min elsewhere; `/health`, `/metrics`, `/openapi.json`, `/docs`, `/redoc`, `/favicon.ico` exempt. Rejects with `429` + `Retry-After`, plus `X-RateLimit-Limit/Remaining` headers.
- **Why:** Redis already exists in the stack; login and claim/card endpoints are the brute-force and data-snooping targets; monitoring endpoints must never be throttled or the system looks down.
- **Trade-off accepted:** fixed-window allows short bursts at minute boundaries (a sliding-window limiter is fairer but more complex). The in-memory fallback resets on restart — acceptable for a degradation path, not a hard requirement to be persistent.
- **Review:** `backend/app/middleware/rate_limit.py`, `backend/app/main.py`, `backend/tests/test_rate_limit.py`.

## B — Security headers (T3b)

- **Chosen:** Content-Security-Policy without `unsafe-inline`, `X-Content-Type-Options: nosniff`, `Cross-Origin-Opener-Policy: same-origin`, removed `Server` banner. HSTS deliberately **not** set over plain HTTP because it would poison browser sessions on localhost; it belongs at the TLS/proxy layer in production.
- **Why:** defensible browser defaults, minimal surface, and the frontend is a separate origin so strict CSP cannot break it.
- **Trade-off accepted:** if the frontend ever inlines scripts, strict CSP will need loosening.
- **Review:** `backend/app/middleware/security_headers.py`, `backend/tests/test_security_headers.py`.

## C — Upload hardening (T3c)

- **Chosen:** allowlist of `image/jpeg`, `image/png`, `image/webp`, `application/pdf`; verification of the file's real byte signature (magic bytes), not the claimed name; 10 MB size cap. Wrong type → `415`, too large → `413`.
- **Why:** allowlists beat blocklists; byte-level checks beat trust-in-filename.
- **Trade-off accepted:** no malware scanning (out of scope) and unusual scan formats are rejected.
- **Review:** `backend/app/core/uploads.py`, `backend/tests/test_upload_hardening.py`.

## D — Attachment storage (T3d)

- **Chosen:** files stored under tenant- and claim-scoped prefixes (`tenants/{tenant}/claims/{claim}/attachments/...`); downloads happen via pre-signed S3 URLs that expire in 300 seconds; the API never proxies file bytes.
- **Why:** files never flow through the app (no bandwidth/leak bottleneck), and a 5-minute expiry bounds any leaked link.
- **Trade-off accepted:** the API cannot log individual presigned-link downloads (that is S3's job). Live tests used a local S3 mock because MinIO is archived upstream and its Docker pulls were denied in this environment.
- **Review:** `backend/app/core/storage.py`, `backend/app/modules/claims/api/attachments.py`, `backend/tests/test_attachments.py`.

## E — Field encryption (T3e)

- **Chosen:** Fernet (AES-128-CBC + HMAC) for `member_id`; stored as `member_id_enc` plus readable `member_id_last4`; migration `4867fb7c0ede` adds the columns; the app refuses to run with the default dev encryption key outside `ENVIRONMENT=test`.
- **Why:** Fernet is the dependable symmetric standard already shipped by the project's `cryptography` dependency; keeping last4 preserves masked display and lookup behavior.
- **Trade-off accepted:** encrypts the one high-value PII field rather than the whole database (no TDE); the default-key guard is bypassable in the test environment by design.
- **Review:** insurance policy model, the settings validator (`backend/app/config.py`), `backend/alembic/versions/4867fb7c0ede_*.py`, `backend/tests/test_field_encryption.py`.

## F — CI audits (T3f)

- **Chosen:** a new `security-audit` job in `.github/workflows/ci.yaml` running pip-audit (Python deps), npm audit at `--audit-level=high` (frontend), and gitleaks (secret scan) with `.gitleaks.toml` allowlisting only the dev-default encryption key (a placeholder, never a real secret).
- **Why:** dependencies are the largest attack surface; gating on high-severity npm findings keeps false-positive noise down. Audit runs result: pip-audit 0, npm 0 after upgrading `fast-uri`/`js-yaml`, gitleaks clean (remaining findings were `.venv` noise).
- **Trade-off accepted:** moderate-severity npm findings do not fail the pipeline.
- **Review:** `.github/workflows/ci.yaml`, `.gitleaks.toml`, README "Security hardening" section.

## G — Baseline scan (T3g) — RESULT: verified clean

- **Chosen:** run an independent scanner against the live app, then triage and record findings regardless of outcome.
- **What actually happened (all evidence-verified against the app's own request log):**
  - ZAP attempted three ways. The ZAP Core build's `-cmd -quickurl` path produced empty scans; running ZAP as a daemon and driving it through its REST API worked. **ZAP spider + active scan completed: 427 requests hit the app (DB-backed routes live), attacker-style probes across `/`, config-file paths, metadata endpoints, and injection strings. Result: 0 High / 0 Medium / 0 Low / 0 Informational on the application** (the single "alert" was ZAP flagging its own version as outdated).
  - **nuclei** (backup scanner): misconfiguration + exposures + curated templates against the same live app over a verified egress path. Result: exit 0, 0 findings.
  - Ground-truth: the app's structured request log (`backend`, request-logging middleware) grew from 2 to 571 lines during these scans, proving both tools genuinely reached and exercised the app (this matters because an earlier "clean" report was a false clean — Postgres was down, so almost every request hung; that taught us to always verify scanner egress).
- **Record:** `docs/zap-baseline-report.html` (ZAP official HTML report).
- **Outcome:** T3g closed with no action items; residual risk recorded below.
- **Residual risks accepted (not fixed):** ZAP is flagged by Windows Defender on this machine (unblocked manually to run); the sandbox blocks some scanner↔uvicorn dials (mitigated via a local stdlib forward proxy); neither scanner authenticates, so unauthenticated surface only.

---

## Historical note (found during T3g, worth keeping)

- A local Postgres serving `127.0.0.1:5433` (app's `DATABASE_URL`) can be down without notice; the app's behavior then is silent request hangs. Verify DB availability before any live scan (`/health` alone is not enough — `/health` does not touch the DB).
- `loadtest.make_token` signs with the same settings the server loads only if run from `backend/` (and any PowerShell `Invoke-WebRequest` 401s against `/api/v1/claims/` were a client-side header artifact — Python `urllib` with the same token returns 200; re-verify with a real client before suspecting auth).

## How to reverse any item

Change the named file, re-run the gates the same way Track 3 was verified (`ruff`, `mypy`, `pytest` — full suite at 313 passing as of this log), and update this document.