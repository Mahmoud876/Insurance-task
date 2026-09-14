from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from loadtest.seed import SeedState


def _load_seed_state() -> SeedState:
    state_file = Path(__file__).parent / ".seed-state.json"
    if not state_file.exists():
        return {}
    state: SeedState = json.loads(state_file.read_text(encoding="utf-8"))
    return state


def _save_seed_state(state: SeedState) -> None:
    state_file = Path(__file__).parent / ".seed-state.json"
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _state_str(state: SeedState, key: str) -> str:
    value = state.get(key)
    return value if isinstance(value, str) else ""


def run() -> SeedState:
    """Seed load-test data quietly and cache IDs for the token script."""
    from loadtest.seed import seed

    state = seed()
    _save_seed_state(state)
    print(f"Seeded tenant_id={state['tenant_id']} claim_id={state['claim_id']}")
    return state


def get_claim_id() -> str:
    return os.getenv("CLAIM_ID") or _state_str(_load_seed_state(), "claim_id")


def get_tenant_id() -> str:
    return os.getenv("TENANT_ID") or _state_str(_load_seed_state(), "tenant_id")


if __name__ == "__main__":
    run()
