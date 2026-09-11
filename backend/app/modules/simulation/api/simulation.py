from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security.auth import AuthContext
from app.deps import get_current_auth_context, get_db
from app.modules.simulation.schemas import SimulationRequest, SimulationResponse
from app.modules.simulation.service import SimulationService

router = APIRouter(prefix="/v1/rulesets", tags=["Ruleset Simulation"])


@router.post(
    "/simulate",
    response_model=SimulationResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate a candidate ruleset against historical claims",
)
def simulate_ruleset(
    request: SimulationRequest,
    db: Session = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_auth_context),
) -> SimulationResponse:
    """Runs candidate rules in dry-run mode against target claims to quantify finding drift."""
    service = SimulationService(db, auth_ctx.tenant_id)
    try:
        return service.run_simulation(request)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        ) from err
