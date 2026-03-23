from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from wechat_link.models import (
    ConfigResponse,
    LoginQRCode,
    QRCodeStatus,
    TypingResponse,
    UpdatesResponse,
    WeixinMessage,
)
from wechat_link.store import FileCursorStore
from wechat_link.relay import create_relay_app


class FakeSDKClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def get_bot_qrcode(self, *, bot_type: int = 3) -> LoginQRCode:
        self.calls.append(("get_bot_qrcode", bot_type))
        return LoginQRCode(
            ret=0,
            qrcode="qr-1",
            qrcode_img_content="https://liteapp.weixin.qq.com/q/qr-1",
        )

    def get_qrcode_status(self, qrcode: str) -> QRCodeStatus:
        self.calls.append(("get_qrcode_status", qrcode))
        return QRCodeStatus(
            status="confirmed",
            bot_token="bot-token",
            baseurl="https://ilinkai.weixin.qq.com",
            ilink_bot_id="bot@im.bot",
            ilink_user_id="user@im.wechat",
        )

    def get_config(self, *, ilink_user_id: str, context_token: str | None = None) -> ConfigResponse:
        self.calls.append(("get_config", {"ilink_user_id": ilink_user_id, "context_token": context_token}))
        return ConfigResponse(ret=0, typing_ticket="typing-1", errmsg="")

    def send_typing(self, *, ilink_user_id: str, typing_ticket: str, status: int = 1) -> TypingResponse:
        self.calls.append(
            (
                "send_typing",
                {
                    "ilink_user_id": ilink_user_id,
                    "typing_ticket": typing_ticket,
                    "status": status,
                },
            )
        )
        return TypingResponse(ret=0, errmsg="")

    def get_updates(self, *, cursor: str = "") -> UpdatesResponse:
        self.calls.append(("get_updates", cursor))
        return UpdatesResponse(
            ret=0,
            next_cursor="cursor-2",
            longpolling_timeout_ms=35000,
            messages=[
                WeixinMessage(
                    from_user_id="user@im.wechat",
                    to_user_id="bot@im.bot",
                    context_token="ctx-1",
                    item_list=[{"type": 1, "text_item": {"text": "你好"}}],
                )
            ],
        )

    def send_text(
        self,
        *,
        to_user_id: str,
        text: str,
        context_token: str,
        client_id: str | None = None,
    ) -> str:
        self.calls.append(
            (
                "send_text",
                {
                    "to_user_id": to_user_id,
                    "text": text,
                    "context_token": context_token,
                    "client_id": client_id,
                },
            )
        )
        return client_id or "generated-client-id"


def test_relay_health_endpoint_returns_ok() -> None:
    app = create_relay_app(client=FakeSDKClient())

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_relay_login_and_config_endpoints_forward_to_client() -> None:
    fake_client = FakeSDKClient()
    app = create_relay_app(client=fake_client)
    http_client = TestClient(app)

    qrcode_response = http_client.get("/login/qrcode")
    status_response = http_client.get("/login/status", params={"qrcode": "qr-1"})
    config_response = http_client.post(
        "/config",
        json={"ilink_user_id": "user@im.wechat", "context_token": "ctx-1"},
    )

    assert qrcode_response.status_code == 200
    assert qrcode_response.json()["qrcode"] == "qr-1"
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "confirmed"
    assert config_response.status_code == 200
    assert config_response.json()["typing_ticket"] == "typing-1"
    assert fake_client.calls[:3] == [
        ("get_bot_qrcode", 3),
        ("get_qrcode_status", "qr-1"),
        ("get_config", {"ilink_user_id": "user@im.wechat", "context_token": "ctx-1"}),
    ]


def test_relay_poll_endpoint_reads_and_persists_cursor(tmp_path: Path) -> None:
    fake_client = FakeSDKClient()
    store = FileCursorStore(tmp_path / "cursor.json")
    store.save("cursor-1")

    app = create_relay_app(client=fake_client, cursor_store=store)
    response = TestClient(app).post("/updates/poll", json={})

    assert response.status_code == 200
    assert response.json()["next_cursor"] == "cursor-2"
    assert response.json()["messages"][0]["context_token"] == "ctx-1"
    assert fake_client.calls == [("get_updates", "cursor-1")]
    assert store.load() == "cursor-2"


def test_relay_typing_and_text_endpoints_forward_payloads() -> None:
    fake_client = FakeSDKClient()
    app = create_relay_app(client=fake_client)
    http_client = TestClient(app)

    typing_response = http_client.post(
        "/typing",
        json={
            "ilink_user_id": "user@im.wechat",
            "typing_ticket": "typing-1",
            "status": 1,
        },
    )
    message_response = http_client.post(
        "/messages/text",
        json={
            "to_user_id": "user@im.wechat",
            "text": "pong",
            "context_token": "ctx-1",
            "client_id": "client-1",
        },
    )

    assert typing_response.status_code == 200
    assert typing_response.json() == {"ret": 0, "errmsg": ""}
    assert message_response.status_code == 200
    assert message_response.json() == {"client_id": "client-1"}
    assert fake_client.calls == [
        (
            "send_typing",
            {
                "ilink_user_id": "user@im.wechat",
                "typing_ticket": "typing-1",
                "status": 1,
            },
        ),
        (
            "send_text",
            {
                "to_user_id": "user@im.wechat",
                "text": "pong",
                "context_token": "ctx-1",
                "client_id": "client-1",
            },
        ),
    ]
