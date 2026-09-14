import json
import os
from pathlib import Path


def _load_seed_state() -> dict[str, str]:
    state_file = Path(__file__).parent / ".seed-state.json"
    if not state_file.exists():
        return {}
    return json.loads(state_file.read_text(encoding="utf-8"))


def _save_seed_state(state: dict[str, str]) -> None:
    state_file = Path(__file__).parent / ".seed-state.json"
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")


def run() -> dict[str, str]:
    """Seed load-test data quietly and cache IDs for the token script."""
    from loadtest.seed import seed

    state = seed()
    _save_seed_state(state)
    print(f"Seeded tenant_id={state['tenant_id']} claim_id={state['claim_id']}")
    return state


def get_claim_id() -> str:
    return os.getenv("CLAIM_ID") or _load_seed_state().get("claim_id", "")


def get_tenant_id() -> str:
    return os.getenv("TENANT_ID") or _load_seed_state().get("tenant_id", "")


if __name__ == "__main__":
    run()
