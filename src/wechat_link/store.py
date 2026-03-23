from __future__ import annotations

import json
from pathlib import Path


class FileCursorStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> str | None:
        if not self.path.exists():
            return None
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        cursor = payload.get("get_updates_buf")
        return cursor if isinstance(cursor, str) else None

    def save(self, cursor: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"get_updates_buf": cursor}, ensure_ascii=False),
            encoding="utf-8",
        )

