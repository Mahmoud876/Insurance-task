import sys
from datetime import date
from uuid import uuid4

sys.path.insert(0, "")

import app.db.models as _  # noqa: F401  (register mappers before first query)
import requests
from app.core.database_session import SessionLocal
from app.modules.claims.models.patient import Patient
from app.modules.claims.models.provider import Provider

from scripts.test_eob_loop import (
    API,
    add_lines,
    create_claim,
    get_token,
    headers,
    render_eob_png,
)


def fresh_patient_and_provider():
    """Creates a brand-new patient + provider via the DB (no API endpoint exists)."""
    db = SessionLocal()
    try:
        from app.modules.claims.models.claim import Claim

        tenant_id = db.query(Claim).first().tenant_id
        patient = Patient(
            tenant_id=tenant_id,
            first_name="Demo",
            last_name=f"EOB{uuid4().hex[:6]}",
            dob=date(2003, 6, 10),
        )
        provider = Provider(
            tenant_id=tenant_id,
            npi=f"9{uuid4().hex[:8]}"[:10],
            first_name="Dr",
            last_name="Cobra",
        )
        db.add_all([patient, provider])
        db.commit()
        db.refresh(patient)
        db.refresh(provider)
        return str(patient.id), str(provider.id)
    finally:
        db.close()


def main():
    token = get_token()
    patient_id, provider_id = fresh_patient_and_provider()
    print(f"  Fresh patient={patient_id}  provider={provider_id}")

    claim_id = create_claim(token, patient_id, provider_id, None)
    add_lines(token, claim_id)

    with open("scripts/demo_eob_primary.png", "wb") as fh:
        fh.write(render_eob_png())
    print(
        "  Saved scripts/demo_eob_primary.png (upload this via the UI as 'EOB (primary payer)')"
    )

    r = requests.post(
        f"{API}/api/v1/claims/{claim_id}/scrub", headers=headers(token), timeout=10
    )
    r.raise_for_status()
    result = r.json()
    print(f"  Pre-upload scrub: readiness={result['readiness_score']}")
    for f in result.get("findings_summary", []):
        print(f"    [{f['severity']}] {f.get('rule_id') or f.get('code')}")

    print("\n" + "=" * 64)
    print("Open this claim and do the upload yourself:")
    print(f"  http://localhost:5173/claims/{claim_id}")
    print("=" * 64)


if __name__ == "__main__":
    main()
