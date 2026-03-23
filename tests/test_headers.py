import base64

from wechat_link.headers import build_wechat_headers


def test_build_wechat_headers_includes_protocol_fields() -> None:
    body = b'{"hello":"world"}'

    headers = build_wechat_headers(body=body, bot_token="secret-token")

    assert headers["Content-Type"] == "application/json"
    assert headers["Content-Length"] == str(len(body))
    assert headers["AuthorizationType"] == "ilink_bot_token"
    assert headers["Authorization"] == "Bearer secret-token"

    decoded = base64.b64decode(headers["X-WECHAT-UIN"]).decode("utf-8")
    assert decoded.isdigit()


def test_build_wechat_headers_omits_authorization_without_token() -> None:
    headers = build_wechat_headers(body=b"{}", bot_token=None)

    assert "Authorization" not in headers

