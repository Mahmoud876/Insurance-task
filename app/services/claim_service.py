import base64
from datetime import date, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import String, cast, select
from sqlalchemy.orm import Session

from app.core.auth import AuthContext
from app.core.rbac import ROLE_PERMISSIONS, Permission
from app.db.models.claim import Claim, ClaimStatus
from app.db.models.claim_line import ClaimLine
from app.schemas.claim import (
    ClaimBoardPage,
    ClaimCreate,
    ClaimLineCreate,
    ClaimLineResponse,
    ClaimResponse,
    ClaimUpdate,
)


class ClaimService:
    @staticmethod
    def _verify_permission(auth_ctx: AuthContext, required_permission: Permission | str) -> None:
        roles = getattr(auth_ctx, "roles", []) or []
        user_permissions: set[Permission | str] = set()
        for role in roles:
            for perm in ROLE_PERMISSIONS.get(role, set()):
                user_permissions.add(perm)
                if hasattr(perm, "value"):
                    user_permissions.add(perm.value)

        target_perm = required_permission
        target_val = target_perm.value if isinstance(target_perm, Permission) else str(target_perm)

        if target_perm not in user_permissions and target_val not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{target_val}' required",
            )

    @staticmethod
    def make_etag(claim: Claim | ClaimResponse) -> str:
        return f'"{claim.updated_at.isoformat()}"'

    @staticmethod
    def _get_tenant_claim(db: Session, claim_id: UUID, auth_ctx: AuthContext) -> Claim:
        claim = db.scalar(
            select(Claim).where(Claim.id == claim_id, Claim.tenant_id == auth_ctx.tenant_id)
        )
        if not claim:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
        return claim

    @staticmethod
    def _claim_status_value(claim: Claim) -> str:
        return claim.status.value if isinstance(claim.status, ClaimStatus) else str(claim.status)

    @staticmethod
    def list_claims(
        db: Session,
        auth_ctx: AuthContext,
        *,
        cursor: str | None = None,
        limit: int = 25,
        status_filter: ClaimStatus | None = None,
        patient_id: UUID | None = None,
        patient_search: str | None = None,
        payer_id: UUID | None = None,
        service_date_from: date | None = None,
        service_date_to: date | None = None,
    ) -> ClaimBoardPage:
        ClaimService._verify_permission(auth_ctx, Permission.CLAIM_READ)

        stmt = select(Claim).where(Claim.tenant_id == auth_ctx.tenant_id)

        if status_filter:
            stmt = stmt.where(Claim.status == status_filter)
        if patient_id:
            stmt = stmt.where(Claim.patient_id == patient_id)
        if payer_id:
            stmt = stmt.where(Claim.payer_id == payer_id)
        if service_date_from:
            stmt = stmt.where(Claim.service_date_from >= service_date_from)
        if service_date_to:
            stmt = stmt.where(Claim.service_date_to <= service_date_to)
        if patient_search:
            stmt = stmt.where(cast(Claim.patient_id, String).ilike(f"%{patient_search}%"))

        if cursor:
            try:
                decoded = base64.b64decode(cursor.encode()).decode()
                cursor_dt, cursor_id = decoded.split("::")
                stmt = stmt.where(
                    (Claim.created_at < datetime.fromisoformat(cursor_dt))
                    | (
                        (Claim.created_at == datetime.fromisoformat(cursor_dt))
                        & (Claim.id < UUID(cursor_id))
                    )
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor"
                ) from e

        stmt = stmt.order_by(Claim.created_at.desc(), Claim.id.desc()).limit(limit + 1)
        results = db.scalars(stmt).all()

        has_more = len(results) > limit
        items = results[:limit]

        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            raw_cursor = f"{last_item.created_at.isoformat()}::{last_item.id}"
            next_cursor = base64.b64encode(raw_cursor.encode()).decode()

        return ClaimBoardPage(
            items=[ClaimResponse.model_validate(c) for c in items],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    @staticmethod
    def get_claim(db: Session, claim_id: UUID, auth_ctx: AuthContext) -> ClaimResponse:
        ClaimService._verify_permission(auth_ctx, Permission.CLAIM_READ)
        claim = ClaimService._get_tenant_claim(db, claim_id, auth_ctx)
        return ClaimResponse.model_validate(claim)

    @staticmethod
    def create_claim(db: Session, payload: ClaimCreate, auth_ctx: AuthContext) -> ClaimResponse:
        ClaimService._verify_permission(auth_ctx, Permission.CLAIM_CREATE)

        claim = Claim(
            tenant_id=auth_ctx.tenant_id,
            patient_id=payload.patient_id,
            provider_id=payload.provider_id,
            payer_id=payload.payer_id,
            total_amount=payload.total_amount,
            status=ClaimStatus.DRAFT,
        )
        if payload.service_date is not None:
            claim.service_date_from = payload.service_date
            claim.service_date_to = payload.service_date
        db.add(claim)
        db.commit()
        db.refresh(claim)
        return ClaimResponse.model_validate(claim)

    @staticmethod
    def update_claim(
        db: Session,
        claim_id: UUID,
        payload: ClaimUpdate,
        auth_ctx: AuthContext,
        if_match: str | None = None,
    ) -> ClaimResponse:
        ClaimService._verify_permission(auth_ctx, Permission.CLAIM_UPDATE)
        claim = ClaimService._get_tenant_claim(db, claim_id, auth_ctx)

        if if_match is not None and if_match != ClaimService.make_etag(claim):
            raise HTTPException(
                status_code=status.HTTP_412_PRECONDITION_FAILED,
                detail="Claim has been modified",
            )

        status_val = ClaimService._claim_status_value(claim)
        if status_val == ClaimStatus.SUBMITTED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update a submitted claim",
            )

        update_data = payload.model_dump(exclude_unset=True)
        service_date = update_data.pop("service_date", None)
        if service_date is not None:
            claim.service_date_from = service_date
            claim.service_date_to = service_date
        for field, value in update_data.items():
            setattr(claim, field, value)

        db.commit()
        db.refresh(claim)
        return ClaimResponse.model_validate(claim)

    @staticmethod
    def scrub_claim(db: Session, claim_id: UUID, auth_ctx: AuthContext) -> ClaimResponse:
        ClaimService._verify_permission(auth_ctx, Permission.CLAIM_UPDATE)
        claim = ClaimService._get_tenant_claim(db, claim_id, auth_ctx)

        status_val = ClaimService._claim_status_value(claim)
        if status_val not in (ClaimStatus.DRAFT.value, ClaimStatus.SCRUBBED.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot scrub claim in status '{status_val}'",
            )

        claim.status = ClaimStatus.SCRUBBED
        db.commit()
        db.refresh(claim)
        return ClaimResponse.model_validate(claim)

    @staticmethod
    def submit_claim(db: Session, claim_id: UUID, auth_ctx: AuthContext) -> ClaimResponse:
        ClaimService._verify_permission(auth_ctx, Permission.CLAIM_SUBMIT)
        claim = ClaimService._get_tenant_claim(db, claim_id, auth_ctx)

        status_val = ClaimService._claim_status_value(claim)
        if status_val != ClaimStatus.SCRUBBED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Claim must be in SCRUBBED status prior to submission",
            )

        claim.status = ClaimStatus.SUBMITTED
        db.commit()
        db.refresh(claim)
        return ClaimResponse.model_validate(claim)

    @staticmethod
    def delete_claim(db: Session, claim_id: UUID, auth_ctx: AuthContext) -> None:
        ClaimService._verify_permission(auth_ctx, Permission.CLAIM_DELETE)
        claim = ClaimService._get_tenant_claim(db, claim_id, auth_ctx)

        status_val = ClaimService._claim_status_value(claim)
        if status_val == ClaimStatus.SUBMITTED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a submitted claim",
            )

        db.delete(claim)
        db.commit()

    @staticmethod
    def replace_claim_lines(
        db: Session,
        claim_id: UUID,
        lines: list[ClaimLineCreate],
        auth_ctx: AuthContext,
    ) -> list[ClaimLineResponse]:
        ClaimService._verify_permission(auth_ctx, Permission.CLAIM_UPDATE)
        claim = ClaimService._get_tenant_claim(db, claim_id, auth_ctx)

        status_val = ClaimService._claim_status_value(claim)
        if status_val == ClaimStatus.SUBMITTED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update a submitted claim",
            )

        for existing_line in list(claim.lines):
            db.delete(existing_line)
        db.flush()

        new_lines: list[ClaimLine] = []
        for line_data in lines:
            line = ClaimLine(
                tenant_id=claim.tenant_id,
                claim_id=claim.id,
                procedure_code=line_data.procedure_code,
                tooth_number=line_data.tooth_number,
                surface=line_data.surface,
                charge_amount=line_data.charge_amount,
            )
            db.add(line)
            new_lines.append(line)

        db.commit()
        for line in new_lines:
            db.refresh(line)
        return [ClaimLineResponse.model_validate(line) for line in new_lines]
