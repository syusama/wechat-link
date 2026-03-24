from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = REPO_ROOT / ".state"
SESSION_PATH = STATE_DIR / "wechat-link-session.json"
LAST_CONTEXT_PATH = STATE_DIR / "last-message-context.json"


def ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_session() -> dict[str, str]:
    if not SESSION_PATH.exists():
        raise SystemExit(
            f"session not found: {SESSION_PATH.resolve()}\n"
            "Run: python examples/login_session.py",
        )

    session = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
    bot_token = session.get("bot_token")
    if not bot_token:
        raise SystemExit(
            f"bot_token missing in session file: {SESSION_PATH.resolve()}",
        )
    return session


def save_session(session: dict[str, str]) -> Path:
    ensure_state_dir()
    SESSION_PATH.write_text(
        json.dumps(session, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return SESSION_PATH


def save_last_context(
    *,
    from_user_id: str,
    context_token: str,
    text: str,
) -> Path:
    ensure_state_dir()
    payload = {
        "from_user_id": from_user_id,
        "context_token": context_token,
        "text": text,
    }
    LAST_CONTEXT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return LAST_CONTEXT_PATH


def load_last_context() -> dict[str, str]:
    if not LAST_CONTEXT_PATH.exists():
        raise SystemExit(
            f"context not found: {LAST_CONTEXT_PATH.resolve()}\n"
            "Run: python examples/receive_once.py",
        )

    payload = json.loads(LAST_CONTEXT_PATH.read_text(encoding="utf-8"))
    from_user_id = payload.get("from_user_id")
    context_token = payload.get("context_token")
    if not from_user_id or not context_token:
        raise SystemExit(
            f"context file is incomplete: {LAST_CONTEXT_PATH.resolve()}",
        )
    return {
        "from_user_id": str(from_user_id),
        "context_token": str(context_token),
        "text": str(payload.get("text", "")),
    }
