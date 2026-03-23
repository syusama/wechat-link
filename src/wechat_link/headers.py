from __future__ import annotations

import base64
import secrets


def build_wechat_uin() -> str:
    value = secrets.randbits(32)
    return base64.b64encode(str(value).encode("utf-8")).decode("utf-8")


def build_wechat_headers(*, body: bytes, bot_token: str | None) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        "AuthorizationType": "ilink_bot_token",
        "X-WECHAT-UIN": build_wechat_uin(),
    }
    if bot_token:
        headers["Authorization"] = f"Bearer {bot_token}"
    return headers

