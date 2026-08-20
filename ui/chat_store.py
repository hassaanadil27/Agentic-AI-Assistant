"""Small JSON-backed conversation store."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

STORE_PATH = Path(__file__).resolve().parent.parent / "chat_history.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_chat() -> dict:
    return {"id": uuid4().hex, "title": "New conversation", "created_at": _now(), "messages": [], "charts": []}


def load_chats() -> list[dict]:
    if not STORE_PATH.exists():
        return []
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save_chats(chats: list[dict]) -> None:
    STORE_PATH.write_text(json.dumps(chats, ensure_ascii=False, indent=2), encoding="utf-8")


def title_from_question(question: str, limit: int = 38) -> str:
    clean = " ".join(question.split()).strip()
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"
