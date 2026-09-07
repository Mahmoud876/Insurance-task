import hashlib
import json

from app.modules.rules.pipeline_types import ClaimSnapshot, ReferenceData
from app.modules.rules.resolver import ResolvedRuleSet


def compute_input_hash(
    snapshot: ClaimSnapshot,
    ruleset: ResolvedRuleSet,
    reference: ReferenceData,
) -> str:
    payload = {
        "snapshot": snapshot.model_dump(mode="json"),
        "ruleset_versions": sorted(ruleset.pinned_version_ids),
        "reference": reference.model_dump(mode="json"),
    }
    canonical_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()
