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


class FileContextTokenStore:
    def __init__(self, state_dir: str | Path) -> None:
        self.state_dir = Path(state_dir)

    def load(self, account_id: str, user_id: str) -> str | None:
        tokens = self._load_account_tokens(account_id)
        token = tokens.get(user_id)
        return token if isinstance(token, str) and token else None

    def save(self, account_id: str, user_id: str, context_token: str) -> None:
        if not account_id or not user_id or not context_token:
            raise ValueError("account_id, user_id, and context_token are required")

        tokens = self._load_account_tokens(account_id)
        tokens[user_id] = context_token

        path = self._account_path(account_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(tokens, ensure_ascii=False),
            encoding="utf-8",
        )

    def clear_account(self, account_id: str) -> None:
        path = self._account_path(account_id)
        if path.exists():
            path.unlink()

    def _account_path(self, account_id: str) -> Path:
        return (
            self.state_dir
            / "openclaw-weixin"
            / "accounts"
            / f"{account_id}.context-tokens.json"
        )

    def _load_account_tokens(self, account_id: str) -> dict[str, str]:
        path = self._account_path(account_id)
        if not path.exists():
            return {}

        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}

        return {
            str(user_id): token
            for user_id, token in payload.items()
            if isinstance(token, str) and token
        }
