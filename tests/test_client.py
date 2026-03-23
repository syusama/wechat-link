import json

import httpx
import pytest

from wechat_link.client import WeChatLinkClient


def test_get_bot_qrcode_uses_expected_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/ilink/bot/get_bot_qrcode"
        assert request.url.params["bot_type"] == "3"
        return httpx.Response(
            200,
            json={
                "ret": 0,
                "qrcode": "abc123",
                "qrcode_img_content": "https://liteapp.weixin.qq.com/q/demo",
            },
        )

    client = WeChatLinkClient(
        transport=httpx.MockTransport(handler),
        channel_version="0.1.0",
    )

    result = client.get_bot_qrcode()

    assert result.qrcode == "abc123"
    assert result.qrcode_img_content == "https://liteapp.weixin.qq.com/q/demo"


def test_get_updates_posts_cursor_and_base_info() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/ilink/bot/getupdates"
        assert request.headers["Authorization"] == "Bearer bot-token"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload == {
            "get_updates_buf": "cursor-1",
            "base_info": {"channel_version": "0.1.0"},
        }
        return httpx.Response(
            200,
            json={
                "ret": 0,
                "msgs": [
                    {
                        "from_user_id": "user@im.wechat",
                        "to_user_id": "bot@im.bot",
                        "context_token": "ctx-1",
                        "item_list": [{"type": 1, "text_item": {"text": "你好"}}],
                    }
                ],
                "get_updates_buf": "cursor-2",
                "longpolling_timeout_ms": 35000,
            },
        )

    client = WeChatLinkClient(
        bot_token="bot-token",
        transport=httpx.MockTransport(handler),
        channel_version="0.1.0",
    )

    result = client.get_updates(cursor="cursor-1")

    assert result.next_cursor == "cursor-2"
    assert result.messages[0].from_user_id == "user@im.wechat"
    assert result.messages[0].text() == "你好"


def test_send_text_requires_context_token() -> None:
    client = WeChatLinkClient()

    with pytest.raises(ValueError, match="context_token"):
        client.send_text(to_user_id="user@im.wechat", text="hi", context_token="")


def test_send_text_posts_expected_message_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/ilink/bot/sendmessage"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload == {
            "msg": {
                "from_user_id": "",
                "to_user_id": "user@im.wechat",
                "client_id": "client-1",
                "message_type": 2,
                "message_state": 2,
                "context_token": "ctx-1",
                "item_list": [{"type": 1, "text_item": {"text": "pong"}}],
            },
            "base_info": {"channel_version": "0.1.0"},
        }
        return httpx.Response(200, json={"ret": 0})

    client = WeChatLinkClient(
        bot_token="bot-token",
        transport=httpx.MockTransport(handler),
        channel_version="0.1.0",
    )

    result = client.send_text(
        to_user_id="user@im.wechat",
        text="pong",
        context_token="ctx-1",
        client_id="client-1",
    )

    assert result == "client-1"


def test_get_config_posts_expected_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/ilink/bot/getconfig"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload == {
            "ilink_user_id": "user@im.wechat",
            "context_token": "ctx-1",
            "base_info": {"channel_version": "0.1.0"},
        }
        return httpx.Response(
            200,
            json={"ret": 0, "typing_ticket": "typing-1", "errmsg": ""},
        )

    client = WeChatLinkClient(
        bot_token="bot-token",
        transport=httpx.MockTransport(handler),
        channel_version="0.1.0",
    )

    result = client.get_config(ilink_user_id="user@im.wechat", context_token="ctx-1")

    assert result.ret == 0
    assert result.typing_ticket == "typing-1"


def test_send_typing_posts_expected_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/ilink/bot/sendtyping"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload == {
            "ilink_user_id": "user@im.wechat",
            "typing_ticket": "typing-1",
            "status": 1,
            "base_info": {"channel_version": "0.1.0"},
        }
        return httpx.Response(200, json={"ret": 0, "errmsg": ""})

    client = WeChatLinkClient(
        bot_token="bot-token",
        transport=httpx.MockTransport(handler),
        channel_version="0.1.0",
    )

    result = client.send_typing(
        ilink_user_id="user@im.wechat",
        typing_ticket="typing-1",
    )

    assert result.ret == 0
