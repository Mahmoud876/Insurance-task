"""Mint a bearer JWT for load-testing the scrub endpoint.

Usage:
    uv run python -m loadtest.make_token <tenant_id>
"""

import sys
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from app.config import settings


def make_token(
    tenant_id: str,
    *,
    roles: list[str] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(uuid4()),
        "tenant_id": tenant_id,
        "roles": roles or ["admin"],
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token.decode("utf-8") if isinstance(token, bytes) else token


if __name__ == "__main__":
    if len(sys.argv) == 2:
        tenant_id = sys.argv[1]
    else:
        import json
        from pathlib import Path

        state_file = Path(__file__).parent / ".seed-state.json"
        tenant_id = json.loads(state_file.read_text(encoding="utf-8")).get("tenant_id", "")
    if not tenant_id:
        print("Usage: python -m loadtest.make_token <tenant_id>", file=sys.stderr)
        raise SystemExit(2)
    print(make_token(tenant_id))
