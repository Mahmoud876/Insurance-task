from datetime import date
from typing import Any
from uuid import uuid4

from app.main import app
from app.modules.rules.pipeline_types import ClaimLineSnapshot, ClaimSnapshot
from app.modules.simulation.schemas import SimulationRequest
from app.modules.simulation.service import SimulationService


class FixtureSimulationService(SimulationService):
    def __init__(self, claims: list[dict[str, Any]]) -> None:
        super().__init__(db=None, tenant_id=uuid4())  # type: ignore[arg-type]
        self.claims = claims

    def _fetch_target_claims(
        self, claim_ids: list[str] | None, corpus_tag: str | None, limit: int
    ) -> list[dict[str, Any]]:
        return self.claims[:limit]


def make_claim() -> dict[str, Any]:
    snapshot = ClaimSnapshot(
        claim_id=uuid4(),
        tenant_id=uuid4(),
        claim_number="CLM-1",
        patient_id=uuid4(),
        patient_dob=date(1990, 1, 1),
        patient_gender="F",
        service_date_from=date(2026, 9, 7),
        service_date_to=date(2026, 9, 7),
        lines=[
            ClaimLineSnapshot(line_number=1, procedure_code="D2140", tooth_number="11"),
            ClaimLineSnapshot(line_number=2, procedure_code="D2150", tooth_number="11"),
        ],
    )
    return {
        "id": str(snapshot.claim_id),
        "status": "CLEAN",
        "snapshot": snapshot,
        "existing_findings": [],
    }


def test_simulation_reports_candidate_finding_drift() -> None:
    service = FixtureSimulationService([make_claim()])
    result = service.run_simulation(
        SimulationRequest(
            candidate_rules=[
                {
                    "rule_id": "R_SAME_TOOTH_01",
                    "operator": "same_tooth_same_day",
                    "args": ["$claim.lines", "D2140", "D2150"],
                    "message_key": "ERR_SAME_TOOTH_SAME_DAY",
                    "severity": "REJECT",
                }
            ],
            max_claims=10,
        )
    )

    assert result.total_claims_evaluated == 1
    assert result.claims_with_drift == 1
    assert result.drift_percentage == 100.0
    assert result.finding_drifts[0].rule_id == "R_SAME_TOOTH_01"
    assert result.sample_claim_diffs[0].added_finding_ids == ["R_SAME_TOOTH_01"]


def test_simulation_route_is_registered() -> None:
    assert "/api/v1/rulesets/simulate" in app.openapi()["paths"]
