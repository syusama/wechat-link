import httpx

from wechat_link.cdn import (
    build_cdn_download_url,
    build_cdn_upload_url,
    download_and_decrypt_buffer,
    upload_buffer_to_cdn,
)
from wechat_link.crypto import encrypt_aes_ecb


def test_build_cdn_urls_match_upstream_shape() -> None:
    assert (
        build_cdn_download_url(
            encrypted_query_param="download-param",
            cdn_base_url="https://novac2c.cdn.weixin.qq.com/c2c",
        )
        == "https://novac2c.cdn.weixin.qq.com/c2c/download?encrypted_query_param=download-param"
    )
    assert (
        build_cdn_upload_url(
            upload_param="upload-param",
            filekey="file-1",
            cdn_base_url="https://novac2c.cdn.weixin.qq.com/c2c",
        )
        == "https://novac2c.cdn.weixin.qq.com/c2c/upload?encrypted_query_param=upload-param&filekey=file-1"
    )


def test_upload_buffer_to_cdn_encrypts_payload_and_returns_download_param() -> None:
    plaintext = b"wechat-link-image"
    aes_key = b"0123456789abcdef"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/c2c/upload"
        assert request.url.params["encrypted_query_param"] == "upload-param"
        assert request.url.params["filekey"] == "file-1"
        assert request.headers["Content-Type"] == "application/octet-stream"
        assert request.content == encrypt_aes_ecb(plaintext, aes_key)
        return httpx.Response(200, headers={"x-encrypted-param": "download-param"})

    result = upload_buffer_to_cdn(
        buffer=plaintext,
        upload_param="upload-param",
        filekey="file-1",
        cdn_base_url="https://novac2c.cdn.weixin.qq.com/c2c",
        aes_key=aes_key,
        transport=httpx.MockTransport(handler),
    )

    assert result == "download-param"


def test_download_and_decrypt_buffer_restores_plaintext() -> None:
    plaintext = b"wechat-link-file"
    aes_key = b"0123456789abcdef"
    encrypted = encrypt_aes_ecb(plaintext, aes_key)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/c2c/download"
        assert request.url.params["encrypted_query_param"] == "download-param"
        return httpx.Response(200, content=encrypted)

    result = download_and_decrypt_buffer(
        encrypted_query_param="download-param",
        aes_key_base64="MDEyMzQ1Njc4OWFiY2RlZg==",
        cdn_base_url="https://novac2c.cdn.weixin.qq.com/c2c",
        transport=httpx.MockTransport(handler),
    )

    assert result == plaintext
