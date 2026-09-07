from pydantic import BaseModel, Field


class CardOCRResponse(BaseModel):
    payer_name: str = Field(..., examples=["Delta Dental"])
    payer_id: str = Field(..., examples=["DEL_12345"])
    member_id: str = Field(..., examples=["MEM-99887766"])
    group_number: str = Field(..., examples=["GRP-443322"])
    subscriber_name: str = Field(..., examples=["John Doe"])
    confidence_score: float = Field(..., examples=[0.98], ge=0.0, le=1.0)
