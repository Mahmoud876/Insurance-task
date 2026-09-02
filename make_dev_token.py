import uuid
from datetime import UTC, datetime, timedelta

import jwt

JWT_SECRET_KEY = "insecure_dev_secret_key_change_in_production"
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "dental-claims-engine"
JWT_AUDIENCE = "dental-claims-api"

TENANT_ID = "e4006cf1-135c-4107-9532-36efcdc53e39"
USER_ID = str(uuid.uuid4())

now = datetime.now(UTC)

payload = {
    "sub": USER_ID,
    "tenant_id": TENANT_ID,
    "roles": ["admin"],
    "iss": JWT_ISSUER,
    "aud": JWT_AUDIENCE,
    "iat": now,
    "exp": now + timedelta(days=7),
}

token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

print("\nDEV JWT (copy everything between the lines):\n")
print("-" * 60)
print(token)
print("-" * 60)
