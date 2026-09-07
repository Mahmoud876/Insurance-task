from typing import Any

from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    ruleset_id: str | None = Field(None, examples=["rs_draft_102"])
    candidate_rules: list[dict[str, Any]] | None = Field(
        None, description="Optional inline rule definitions for instant evaluation"
    )
    corpus_tag: str | None = Field(
        "golden_v1", description="Tag of target claim corpus to evaluate against"
    )
    claim_ids: list[str] | None = Field(
        None, description="Specific list of claim IDs to run simulation on"
    )
    max_claims: int = Field(1000, ge=1, le=10000)


class FindingDrift(BaseModel):
    rule_id: str
    rule_name: str
    baseline_occurrences: int
    simulated_occurrences: int
    delta: int
    percentage_change: float


class ClaimSimulationDiff(BaseModel):
    claim_id: str
    baseline_status: str
    simulated_status: str
    status_changed: bool
    added_finding_ids: list[str]
    removed_finding_ids: list[str]


class SimulationResponse(BaseModel):
    total_claims_evaluated: int
    claims_with_drift: int
    drift_percentage: float
    finding_drifts: list[FindingDrift]
    sample_claim_diffs: list[ClaimSimulationDiff]
