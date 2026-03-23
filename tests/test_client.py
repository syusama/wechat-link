import json
from io import BytesIO

import httpx
import pytest
from PIL import Image

from wechat_link.client import Client


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

    client = Client(
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

    client = Client(
        bot_token="bot-token",
        transport=httpx.MockTransport(handler),
        channel_version="0.1.0",
    )

    result = client.get_updates(cursor="cursor-1")

    assert result.next_cursor == "cursor-2"
    assert result.messages[0].from_user_id == "user@im.wechat"
    assert result.messages[0].text() == "你好"


def test_send_text_requires_context_token() -> None:
    client = Client()

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

    client = Client(
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

    client = Client(
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

    client = Client(
        bot_token="bot-token",
        transport=httpx.MockTransport(handler),
        channel_version="0.1.0",
    )

    result = client.send_typing(
        ilink_user_id="user@im.wechat",
        typing_ticket="typing-1",
    )

    assert result.ret == 0


def test_default_timeout_allows_long_polling_endpoints() -> None:
    client = Client()

    assert client._client.timeout.read == 45.0
    assert client._client.timeout.connect == 15.0
    assert client._client.timeout.write == 15.0
    assert client._client.timeout.pool == 15.0

    client.close()


def test_save_qrcode_image_downloads_from_url(tmp_path) -> None:
    image_bytes = b"\x89PNG\r\n\x1a\nfake"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://liteapp.weixin.qq.com/q/demo"
        return httpx.Response(
            200,
            content=image_bytes,
            headers={"Content-Type": "image/png"},
        )

    client = Client(transport=httpx.MockTransport(handler))
    output_path = tmp_path / "login-qrcode.png"

    result = client.save_qrcode_image(
        "https://liteapp.weixin.qq.com/q/demo",
        output_path=output_path,
    )

    assert result == output_path
    assert output_path.read_bytes() == image_bytes
    client.close()


def test_render_qrcode_terminal_from_url() -> None:
    image = Image.new("1", (2, 2), 1)
    image.putpixel((0, 0), 0)
    image.putpixel((1, 0), 1)
    image.putpixel((0, 1), 1)
    image.putpixel((1, 1), 0)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://liteapp.weixin.qq.com/q/demo"
        return httpx.Response(
            200,
            content=image_bytes,
            headers={"Content-Type": "image/png"},
        )

    client = Client(transport=httpx.MockTransport(handler))

    rendered = client.render_qrcode_terminal(
        "https://liteapp.weixin.qq.com/q/demo",
        padding=0,
    )

    assert rendered.splitlines() == ["██  ", "  ██"]
    client.close()


def test_save_qrcode_image_generates_png_when_url_returns_html(tmp_path) -> None:
    html_bytes = b"<!doctype html><html><body>qr page</body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://liteapp.weixin.qq.com/q/demo"
        return httpx.Response(
            200,
            content=html_bytes,
            headers={"Content-Type": "text/html; charset=utf-8"},
        )

    client = Client(transport=httpx.MockTransport(handler))
    output_path = tmp_path / "login-qrcode.png"

    result = client.save_qrcode_image(
        "https://liteapp.weixin.qq.com/q/demo",
        output_path=output_path,
    )

    opened = Image.open(output_path)

    assert result == output_path
    assert opened.size[0] > 0
    assert opened.size[1] > 0
    client.close()


def test_render_qrcode_terminal_generates_from_url_when_response_is_html() -> None:
    html_bytes = b"<!doctype html><html><body>qr page</body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://liteapp.weixin.qq.com/q/demo"
        return httpx.Response(
            200,
            content=html_bytes,
            headers={"Content-Type": "text/html; charset=utf-8"},
        )

    client = Client(transport=httpx.MockTransport(handler))

    rendered = client.render_qrcode_terminal(
        "https://liteapp.weixin.qq.com/q/demo",
        padding=0,
    )

    assert "██" in rendered
    assert len(rendered.splitlines()) > 10
    client.close()
