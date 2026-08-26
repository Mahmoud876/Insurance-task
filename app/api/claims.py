from fastapi import APIRouter

from app.schemas.claim import ClaimCreate

router = APIRouter(
    prefix="/v1/claims",
    tags=["claims"],
)


@router.post("")
def create_claim(data: ClaimCreate):
    return data


