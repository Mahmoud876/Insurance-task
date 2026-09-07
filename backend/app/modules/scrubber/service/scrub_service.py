from typing import Any

from app.modules.rules.pipeline_types import ScrubResult


def execute_and_persist_scrub(*args: Any, **kwargs: Any) -> ScrubResult:
    raise NotImplementedError("Scrub persistence is not configured")
