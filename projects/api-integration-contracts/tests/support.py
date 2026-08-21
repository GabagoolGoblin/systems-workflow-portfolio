from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "fixtures" / "synthetic_contract.json"
RUN_PATH = ROOT / "fixtures" / "synthetic_run.json"


def fixtures() -> tuple[dict[str, Any], dict[str, Any]]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    run = json.loads(RUN_PATH.read_text(encoding="utf-8"))
    return deepcopy(contract), deepcopy(run)


def rate_limited_attempt(number: int, correlation: str, retry_after: str = "2") -> dict[str, Any]:
    return {
        "attempt": number,
        "status": 429,
        "headers": {"retry-after": retry_after, "x-correlation-id": correlation},
        "body": {
            "error": {
                "code": "synthetic_rate_limited",
                "message": "Synthetic bounded retry fixture.",
            }
        },
    }

