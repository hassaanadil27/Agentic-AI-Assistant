"""Internal JSONL audit log for analytical query planning and validation."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUERY_LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "query_analysis.jsonl"


def log_query(payload: dict[str, Any]) -> None:
    QUERY_LOG_PATH.parent.mkdir(exist_ok=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **payload}
    with QUERY_LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
