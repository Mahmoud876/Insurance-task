from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.claims.models.insurance_policy import InsurancePolicy
from app.modules.claims.models.patient import Patient
from app.modules.ocr.engine import OcrEngine, OcrLine, image_from_bytes
from app.modules.ocr.parser import CardOCRResult, parse_insurance_card
from app.modules.payers.payer import Payer
from app.modules.payers.payer_plan import PayerPlan

logger = logging.getLogger(__name__)


def ocr_lines_from_bytes(
    data: bytes,
    media_type: str,
    engine: OcrEngine,
) -> list[OcrLine]:
    image = image_from_bytes(data, media_type)
    return engine.text_lines(image)


def ocr_card_from_bytes(
    data: bytes,
    media_type: str,
    engine: OcrEngine,
) -> CardOCRResult:
    image = image_from_bytes(data, media_type)
    lines = engine.text_lines(image)
    return parse_insurance_card(lines)


def _resolve_or_create_payer(
    db: Session,
    tenant_id: UUID,
    extract: CardOCRResult,
) -> Payer:
    code = extract.payer_id or "UNKNOWN"
    name = extract.payer_name or "Unknown Payer"

    if extract.payer_id:
        payer = db.scalar(
            select(Payer).where(Payer.tenant_id == tenant_id, Payer.payer_code == extract.payer_id)
        )
        if payer is not None:
            return payer

    payer = db.scalar(select(Payer).where(Payer.tenant_id == tenant_id, Payer.name == name))
    if payer is not None:
        return payer

    payer = Payer(tenant_id=tenant_id, name=name, payer_code=code)
    db.add(payer)
    db.flush()
    return payer


def _resolve_or_create_plan(
    db: Session,
    tenant_id: UUID,
    payer: Payer,
    payer_plan_id: UUID | None,
) -> PayerPlan:
    if payer_plan_id is not None:
        plan = db.get(PayerPlan, payer_plan_id)
        if plan is not None and plan.tenant_id == tenant_id and plan.payer_id == payer.id:
            return plan

    plan = db.scalar(select(PayerPlan).where(PayerPlan.payer_id == payer.id).limit(1))
    if plan is None:
        plan = PayerPlan(tenant_id=tenant_id, payer_id=payer.id, plan_name=f"{payer.name} Plan")
        db.add(plan)
        db.flush()
    return plan


def _upsert_policy(
    db: Session,
    tenant_id: UUID,
    patient: Patient,
    plan: PayerPlan,
    extract: CardOCRResult,
) -> InsurancePolicy:
    if extract.member_id:
        for policy in db.scalars(
            select(InsurancePolicy).where(
                InsurancePolicy.tenant_id == tenant_id,
                InsurancePolicy.patient_id == patient.id,
                InsurancePolicy.payer_plan_id == plan.id,
            )
        ):
            if policy.member_id == extract.member_id:
                policy.group_number = extract.group_number or policy.group_number
                policy.source = "ocr"
                policy.verified_at = datetime.now(UTC)
                return policy

    policy = InsurancePolicy(
        tenant_id=tenant_id,
        patient_id=patient.id,
        payer_plan_id=plan.id,
        policy_number=extract.member_id or f"OCR-{uuid.uuid4().hex[:12].upper()}",
        group_number=extract.group_number or None,
        member_id=extract.member_id or None,
        effective_date=datetime.now(UTC).date(),
        source="ocr",
        verified_at=datetime.now(UTC),
    )
    db.add(policy)
    db.flush()
    return policy


def upsert_policy_from_ocr(
    db: Session,
    tenant_id: UUID,
    extract: CardOCRResult,
    *,
    patient_id: UUID | None,
    payer_plan_id: UUID | None = None,
) -> InsurancePolicy | None:
    if patient_id is None:
        return None

    try:
        patient = db.get(Patient, patient_id)
        if patient is None or patient.tenant_id != tenant_id:
            return None

        payer = _resolve_or_create_payer(db, tenant_id, extract)
        plan = _resolve_or_create_plan(db, tenant_id, payer, payer_plan_id)
        policy = _upsert_policy(db, tenant_id, patient, plan, extract)
        db.commit()
        db.refresh(policy)
        return policy
    except Exception:
        logger.exception("Failed to persist insurance policy from OCR result")
        db.rollback()
        return None
