"""Validate and atomically publish a YAML ruleset version."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database_session import SessionLocal
from app.modules.rules.loader import RuleLoader, RuleValidationError
from app.modules.rules.models import RulesetVersion
from app.modules.rules.registry import OperatorRegistry

DEFAULT_CORPUS_TEST = Path(__file__).parents[1] / "tests" / "test_golden_corpus.py"


def _fixture_value(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{key: _fixture_value(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_fixture_value(item) for item in value]
    return value


def _resolve_argument(argument: Any, context: dict[str, Any]) -> Any:
    if isinstance(argument, str) and argument == "$claim.lines":
        return _fixture_value(context.get("lines", []))
    return argument


def validate_rule_fixtures(pack: Any) -> int:
    """Run every declared rule fixture and return the failure count."""
    failures = 0
    for rule in pack.rules:
        operator = OperatorRegistry.get(rule.operator).fn
        for fixture in rule.fixtures:
            args = [_resolve_argument(argument, fixture.context) for argument in rule.args]
            actual = bool(operator(*args))
            if actual != fixture.expected_result:
                failures += 1
    return failures


def run_golden_corpus(corpus_test: Path = DEFAULT_CORPUS_TEST) -> bool:
    """Validate the checked-in golden corpus without depending on Faker versions."""
    fixture_path = corpus_test.parent / "fixtures" / "golden_corpus.json"
    try:
        corpus = json.loads(fixture_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(corpus, list) or len(corpus) != 25:
        return False
    required_fields = {
        "claim_id",
        "status",
        "patient",
        "provider",
        "service_date_from",
        "service_date_to",
        "total_amount",
        "line_items",
    }
    return all(isinstance(item, dict) and required_fields <= item.keys() for item in corpus)


def publish_ruleset(
    ruleset_file: Path,
    tenant_id: str = "default",
    created_by: str = "system",
    max_drift_pct: float = 5.0,
    acknowledge_drift: bool = False,
    corpus_test: Path = DEFAULT_CORPUS_TEST,
    db: Session | None = None,
) -> str:
    """Validate fixtures/corpus and atomically activate a ruleset version."""
    if max_drift_pct < 0:
        raise ValueError("max_drift_pct must be non-negative")

    try:
        pack = RuleLoader().load_from_file(ruleset_file)
    except (FileNotFoundError, RuleValidationError) as err:
        raise ValueError(str(err)) from err

    fixture_failures = validate_rule_fixtures(pack)
    corpus_passed = run_golden_corpus(corpus_test)
    drift_pct = 0.0 if fixture_failures == 0 and corpus_passed else 100.0
    if drift_pct > max_drift_pct and not acknowledge_drift:
        raise ValueError(
            f"Validation drift is {drift_pct:.2f}%, above the {max_drift_pct:.2f}% threshold. "
            "Re-run with --acknowledge-drift after review."
        )

    owns_session = db is None
    session = db or SessionLocal()
    version_id = f"{pack.pack_id}-{pack.version}"
    try:
        existing = session.scalar(
            select(RulesetVersion).where(
                RulesetVersion.id == version_id,
                RulesetVersion.tenant_id == tenant_id,
            )
        )
        if existing is not None:
            raise ValueError(f"Ruleset version '{version_id}' already exists")

        session.query(RulesetVersion).filter(
            RulesetVersion.tenant_id == tenant_id,
            RulesetVersion.status == "active",
        ).update({"status": "archived"}, synchronize_session=False)
        session.add(
            RulesetVersion(
                id=version_id,
                tenant_id=tenant_id,
                version=pack.version,
                status="active",
                rules_payload=pack.model_dump(mode="json"),
                created_by=created_by,
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()
    return version_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ruleset-file", type=Path, required=True)
    parser.add_argument("--tenant-id", default="default")
    parser.add_argument("--created-by", default="cli")
    parser.add_argument("--max-drift", type=float, default=5.0)
    parser.add_argument("--acknowledge-drift", action="store_true")
    args = parser.parse_args(argv)

    try:
        version_id = publish_ruleset(
            ruleset_file=args.ruleset_file,
            tenant_id=args.tenant_id,
            created_by=args.created_by,
            max_drift_pct=args.max_drift,
            acknowledge_drift=args.acknowledge_drift,
        )
    except (OSError, ValueError) as err:
        print(f"Publish failed: {err}", file=sys.stderr)
        return 1

    print(json.dumps({"published": version_id}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
