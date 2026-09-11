from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.modules.claims.models.claim import Claim
from app.modules.rules.models import RulesetVersion
from app.modules.rules.operators import generic as _generic_operators  # noqa: F401
from app.modules.rules.pipeline import post_process_findings
from app.modules.rules.pipeline_types import (
    ClaimLineSnapshot,
    ClaimSnapshot,
    Finding,
    FindingSeverity,
    ScrubResult,
)
from app.modules.rules.registry import OperatorRegistry
from app.modules.simulation.schemas import (
    ClaimSimulationDiff,
    FindingDrift,
    SimulationRequest,
    SimulationResponse,
)


class SimulationService:
    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def run_simulation(self, request: SimulationRequest) -> SimulationResponse:
        """Executes candidate rules against specified claims in dry run mode and calculates drift metrics"""
        candidate_rules = request.candidate_rules
        if not candidate_rules and request.ruleset_id:
            candidate_rules = self._load_ruleset_rules(request.ruleset_id)
        if not candidate_rules:
            raise ValueError("candidate_rules or ruleset_id is required")

        target_claims = self._fetch_target_claims(
            claim_ids=request.claim_ids,
            corpus_tag=request.corpus_tag,
            limit=request.max_claims,
        )

        total_evaluated = len(target_claims)
        if total_evaluated == 0:
            return SimulationResponse(
                total_claims_evaluated=0,
                claims_with_drift=0,
                drift_percentage=0.0,
                finding_drifts=[],
                sample_claim_diffs=[],
            )

        claims_with_drift_count = 0
        diffs: list[ClaimSimulationDiff] = []
        rule_counts_baseline: dict[str, int] = {}
        rule_counts_simulated: dict[str, int] = {}

        for claim in target_claims:
            claim_id = claim["id"]

            baseline_findings = claim.get("existing_findings", [])
            baseline_rule_ids = {f["rule_id"] for f in baseline_findings}

            simulated_result = self._evaluate_dry_run(
                claim_payload=claim,
                candidate_rules=candidate_rules,
            )
            simulated_rule_ids = {finding.rule_id for finding in simulated_result.findings}

            # Track global frequency per rule
            for rid in baseline_rule_ids:
                rule_counts_baseline[rid] = rule_counts_baseline.get(rid, 0) + 1
            for rid in simulated_rule_ids:
                rule_counts_simulated[rid] = rule_counts_simulated.get(rid, 0) + 1

            # Compute diffs
            added = list(simulated_rule_ids - baseline_rule_ids)
            removed = list(baseline_rule_ids - simulated_rule_ids)
            has_drift = len(added) > 0 or len(removed) > 0

            if has_drift:
                claims_with_drift_count += 1

            diffs.append(
                ClaimSimulationDiff(
                    claim_id=claim_id,
                    baseline_status=claim.get("status", "pending"),
                    simulated_status=simulated_result.status,
                    status_changed=has_drift,
                    added_finding_ids=added,
                    removed_finding_ids=removed,
                )
            )

        # Compute aggregate drift metrics
        all_rule_ids = set(rule_counts_baseline.keys()) | set(rule_counts_simulated.keys())
        finding_drifts: list[FindingDrift] = []

        for rid in all_rule_ids:
            base_cnt = rule_counts_baseline.get(rid, 0)
            sim_cnt = rule_counts_simulated.get(rid, 0)
            delta = sim_cnt - base_cnt
            pct_change = (
                ((delta / base_cnt) * 100.0) if base_cnt > 0 else (100.0 if sim_cnt > 0 else 0.0)
            )

            finding_drifts.append(
                FindingDrift(
                    rule_id=rid,
                    rule_name=f"Rule {rid}",
                    baseline_occurrences=base_cnt,
                    simulated_occurrences=sim_cnt,
                    delta=delta,
                    percentage_change=round(pct_change, 2),
                )
            )

        drift_percentage = round((claims_with_drift_count / total_evaluated) * 100.0, 2)

        finding_drifts.sort(key=lambda item: (-abs(item.delta), item.rule_id))
        return SimulationResponse(
            total_claims_evaluated=total_evaluated,
            claims_with_drift=claims_with_drift_count,
            drift_percentage=drift_percentage,
            finding_drifts=finding_drifts,
            sample_claim_diffs=diffs[:50],  # Truncate sample diffs payload
        )

    def _fetch_target_claims(
        self, claim_ids: list[str] | None, corpus_tag: str | None, limit: int
    ) -> list[dict[str, Any]]:
        """Fetch tenant-scoped claims and serialize them for the pure rule pipeline"""
        statement = (
            select(Claim)
            .options(joinedload(Claim.patient), joinedload(Claim.lines))
            .where(Claim.tenant_id == self.tenant_id)
            .order_by(Claim.created_at)
            .limit(limit)
        )
        if claim_ids:
            parsed_ids = [UUID(value) for value in claim_ids]
            statement = statement.where(Claim.id.in_(parsed_ids))

        claims = self.db.scalars(statement).unique().all()
        return [
            {
                "id": str(claim.id),
                "snapshot": ClaimSnapshot(
                    claim_id=claim.id,
                    tenant_id=claim.tenant_id,
                    claim_number=claim.claim_number,
                    patient_id=claim.patient_id,
                    patient_dob=claim.patient.dob,
                    patient_gender="",
                    service_date_from=claim.service_date_from,
                    service_date_to=claim.service_date_to,
                    lines=[
                        ClaimLineSnapshot(
                            line_number=index,
                            procedure_code=line.procedure_code,
                            tooth_number=line.tooth_number,
                            surface=line.surface,
                            charge_amount=float(line.charge_amount),
                        )
                        for index, line in enumerate(claim.lines, start=1)
                    ],
                ),
                "status": claim.status.value,
                "existing_findings": claim.findings_summary,
            }
            for claim in claims
        ]

    def _evaluate_dry_run(
        self, claim_payload: dict[str, Any], candidate_rules: list[dict[str, Any]] | None
    ) -> ScrubResult:
        """Execute candidate operators without persistence or audit side effects."""
        snapshot: ClaimSnapshot = claim_payload["snapshot"]
        findings: list[Finding] = []
        for raw_rule in candidate_rules or []:
            normalized = dict(raw_rule)
            if "id" in normalized and "rule_id" not in normalized:
                normalized["rule_id"] = normalized.pop("id")
            rule_id = str(normalized.get("rule_id", ""))
            operator_name = normalized.get("operator")
            if not rule_id or not isinstance(operator_name, str):
                raise ValueError("Each candidate rule requires rule_id and operator")
            operator = OperatorRegistry.get(operator_name).fn
            args = [
                self._resolve_argument(argument, snapshot)
                for argument in normalized.get("args", [])
            ]
            try:
                violated = bool(operator(*args))
            except Exception as err:
                raise ValueError(f"Simulation failed for rule '{rule_id}': {err}") from err
            if violated:
                findings.append(
                    Finding(
                        rule_id=rule_id,
                        severity=FindingSeverity(normalized.get("severity", "WARNING")),
                        message_key=str(normalized.get("message_key", "ERR_RULE_VIOLATION")),
                        message=f"Rule {rule_id} failed check.",
                    )
                )

        final_findings, score, status, is_truncated = post_process_findings(findings)
        return ScrubResult(
            claim_id=snapshot.claim_id,
            readiness_score=score,
            status=status,
            findings=final_findings,
            pinned_version_ids=["simulation"],
            is_truncated=is_truncated,
            evaluated_at=datetime.now(UTC),
        )

    def _load_ruleset_rules(self, ruleset_id: str) -> list[dict[str, Any]]:
        record = self.db.scalar(
            select(RulesetVersion).where(
                RulesetVersion.id == ruleset_id,
                RulesetVersion.tenant_id == str(self.tenant_id),
            )
        )
        if record is None:
            raise ValueError(f"Ruleset version '{ruleset_id}' not found")
        rules_payload = record.rules_payload
        if not isinstance(rules_payload, dict) or not isinstance(rules_payload.get("rules"), list):
            raise ValueError(f"Ruleset version '{ruleset_id}' has an invalid payload")
        return cast(list[dict[str, Any]], rules_payload["rules"])

    @staticmethod
    def _resolve_argument(argument: Any, snapshot: ClaimSnapshot) -> Any:
        if argument == "$claim.lines":
            return [
                SimpleNamespace(
                    procedure_code=line.procedure_code,
                    tooth_number=line.tooth_number,
                )
                for line in snapshot.lines
            ]
        if argument == "$claim.service_date_from":
            return snapshot.service_date_from
        if argument == "$claim.service_date_to":
            return snapshot.service_date_to
        if argument == "$claim.claim_id":
            return snapshot.claim_id
        return argument
