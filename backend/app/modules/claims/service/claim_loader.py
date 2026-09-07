from typing import Any

from app.modules.rules.pipeline_types import ClaimSnapshot, ReferenceData


def load_claim_snapshot(*args: Any, **kwargs: Any) -> ClaimSnapshot:
    raise NotImplementedError("Claim snapshot loading is not configured")


def load_reference_data(*args: Any, **kwargs: Any) -> ReferenceData:
    return ReferenceData()
