"""Creates a secondary claim + uploads a fake EOB for the COB scrub demo.

The fake EOB is rendered to a PNG so EasyOCR can read it at upload time,
which then seeds patient procedure history (source=EOB_IMPORT) so the
frequency rule (P4_FREQ_LIMITATION) can also fire.

"""

import io
import os
import sys

import requests

API = "http://127.0.0.1:8000"
KC = "http://localhost:8080"


def get_token():
    r = requests.post(
        f"{KC}/realms/insurance/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "insurance-frontend",
            "username": "ola",
            "password": "password123",
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def pick_existing_patient_and_provider(token):
    r = requests.get(f"{API}/api/v1/claims", headers=headers(token), timeout=10)
    r.raise_for_status()
    items = r.json()["items"]
    if items:
        c = items[0]
        print(
            f"  Using claim {c['claim_number']} as source "
            f"(patient={c['patient_id']}, provider={c['provider_id']})"
        )
        return c["patient_id"], c["provider_id"], c.get("payer_id")
    sys.exit(
        "No claims found. Seed the dev database first:\n"
        "  cd backend && .venv/Scripts/python.exe -m app.modules.reference.seed_dev_data"
    )


def create_claim(token, patient_id, provider_id, payer_id=None):
    payload = {
        "patient_id": patient_id,
        "provider_id": provider_id,
        "total_amount": "250.00",
        "is_secondary_claim": True,
        "service_date_from": "2026-09-01",
        "service_date_to": "2026-09-01",
    }
    if payer_id:
        payload["payer_id"] = payer_id
    r = requests.post(
        f"{API}/api/v1/claims", headers=headers(token), json=payload, timeout=10
    )
    r.raise_for_status()
    claim = r.json()
    print(f"  Created claim {claim['claim_number']}  id={claim['id']}")
    print(f"    is_secondary_claim={claim['is_secondary_claim']}")
    return claim["id"]


def add_lines(token, claim_id):
    lines = [
        {
            "procedure_code": "D2140",
            "tooth_number": "14",
            "surface": "MO",
            "charge_amount": "125.00",
        },
        {
            "procedure_code": "D1110",
            "tooth_number": None,
            "surface": None,
            "charge_amount": "85.00",
        },
        {
            "procedure_code": "D1110",
            "tooth_number": None,
            "surface": None,
            "charge_amount": "40.00",
        },
    ]
    r = requests.put(
        f"{API}/api/v1/claims/{claim_id}/lines",
        headers=headers(token),
        json=lines,
        timeout=10,
    )
    r.raise_for_status()
    print(f"  Added {len(lines)} line items")


def scrub(token, claim_id):
    r = requests.post(
        f"{API}/api/v1/claims/{claim_id}/scrub", headers=headers(token), timeout=10
    )
    r.raise_for_status()
    result = r.json()
    print(f"  Status: {result['status']}  Readiness: {result['readiness_score']}")
    for f in result.get("findings_summary", []):
        print(
            f"    [{f['severity']}] {f.get('rule_id') or f.get('code')}: "
            f"{f.get('summary', '')[:80]}"
        )
    return result


def render_eob_png():
    """Renders a clean, high-contrast EOB image that EasyOCR can read.

    Each CDT code is isolated on its own line and rendered larger than the
    surrounding text, which makes the trailing-zero digit unambiguous to the
    OCR model."
    """
    from PIL import Image, ImageDraw, ImageFont

    rows = [
        (60, "Delta Dental Assurance"),
        (60, "Member ID: 88421-DA-01"),
        (60, "Date of Service: 08/01/2026"),
        (60, "Procedure"),
        (90, "D1110"),
        (60, "Prophylaxis - Adult"),
        (60, "Allowed Amount: 85.00"),
        (60, "Date of Service: 08/15/2026"),
        (60, "Procedure"),
        (90, "D1110"),
        (60, "Prophylaxis - Adult"),
        (60, "Allowed Amount: 85.00"),
        (60, "Total Allowed Amount: 170.00"),
    ]

    font_cache = {}

    mono = None
    for candidate in (
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cour.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    ):
        if os.path.exists(candidate):
            mono = candidate
            break

    def font(size):
        if size not in font_cache:
            if mono is not None:
                font_cache[size] = ImageFont.truetype(mono, size)
            else:
                font_cache[size] = ImageFont.load_default()
        return font_cache[size]

    width = max(font(90).getbbox(row[1])[2] for row in rows) + 240
    spacing = 118
    height = sum(spacing for _ in rows) + 200
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    y = 80
    for size, text in rows:
        draw.text((120, y), text, fill="black", font=font(size))
        y += spacing

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def upload_eob(token, claim_id):
    png_bytes = render_eob_png()
    r = requests.post(
        f"{API}/api/v1/claims/{claim_id}/attachments",
        headers=headers(token),
        files={"file": ("eob_primary.png", png_bytes, "image/png")},
        data={"doc_type": "Primary EOB"},
        timeout=30,
    )
    r.raise_for_status()
    att = r.json()
    print(f"  Uploaded EOB attachment id={att['id']}  doc_type={att['doc_type']}")
    if att.get("ocr_text"):
        print(f"    OCR text preview: {att['ocr_text'][:140]}...")
    else:
        print("    WARNING: no OCR text was extracted (EasyOCR may be unavailable).")
        print(
            "    The COB rule will still clear (doc_type is enough); P4_FREQ_LIMITATION"
        )
        print("    requires OCR to read the procedure code.")
    return att


def main():
    print("Authenticating...")
    token = get_token()

    print("\nFinding patient/provider...")
    patient_id, provider_id, payer_id = pick_existing_patient_and_provider(token)

    print("\nCreating secondary claim with 2 line items...")
    claim_id = create_claim(token, patient_id, provider_id, payer_id)

    print("\nAdding procedure lines...")
    add_lines(token, claim_id)

    print("\n--- SCRUB 1: expect P4_COB_ORDER warning ---")
    scrub(token, claim_id)

    print("\nUploading fake primary EOB (D2140 + date) as a rendered PNG...")
    upload_eob(token, claim_id)

    print("\n--- SCRUB 2: P4_COB_ORDER should be gone ---")
    scrub(token, claim_id)

    print("\n" + "=" * 60)
    print("Open the claim editor in your browser:")
    print(f"  http://localhost:5173/claims/{claim_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()
