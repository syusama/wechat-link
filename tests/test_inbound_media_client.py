import httpx

from wechat_link.client import Client
from wechat_link.crypto import encrypt_aes_ecb
from wechat_link.models import InboundMediaRef, InboundMessageItem


def test_download_media_uses_decrypt_path_when_aes_key_present() -> None:
    plaintext = b"wechat-link-image"
    encrypted = encrypt_aes_ecb(plaintext, b"0123456789abcdef")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/c2c/download"
        assert request.url.params["encrypted_query_param"] == "download-param"
        return httpx.Response(200, content=encrypted)

    client = Client(cdn_transport=httpx.MockTransport(handler))

    result = client.download_media(
        InboundMediaRef(
            encrypt_query_param="download-param",
            aes_key="MDEyMzQ1Njc4OWFiY2RlZg==",
            encrypt_type=1,
        )
    )

    assert result == plaintext


def test_download_media_uses_plain_download_when_aes_key_missing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/c2c/download"
        assert request.url.params["encrypted_query_param"] == "plain-download-param"
        return httpx.Response(200, content=b"plain-file")

    client = Client(cdn_transport=httpx.MockTransport(handler))

    result = client.download_media(
        InboundMediaRef(
            encrypt_query_param="plain-download-param",
        )
    )

    assert result == b"plain-file"


def test_download_message_item_uses_thumb_media_when_requested() -> None:
    plaintext = b"thumb-image"
    encrypted = encrypt_aes_ecb(plaintext, b"0123456789abcdef")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["encrypted_query_param"] == "thumb-download-param"
        return httpx.Response(200, content=encrypted)

    client = Client(cdn_transport=httpx.MockTransport(handler))
    item = InboundMessageItem(
        kind="video",
        type=5,
        media=InboundMediaRef(encrypt_query_param="video-download-param"),
        thumb_media=InboundMediaRef(
            encrypt_query_param="thumb-download-param",
            aes_key="MDEyMzQ1Njc4OWFiY2RlZg==",
            encrypt_type=1,
        ),
    )

    result = client.download_message_item(item, thumb=True)

    assert result == plaintext


def test_download_media_uses_full_url_when_present() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://cdn.example.com/path/to/file"
        return httpx.Response(200, content=b"plain-file")

    client = Client(cdn_transport=httpx.MockTransport(handler))

    result = client.download_media(
        InboundMediaRef(
            encrypt_query_param="ignored-download-param",
            full_url="https://cdn.example.com/path/to/file",
        )
    )

    assert result == b"plain-file"
