from __future__ import annotations

import httpx

from wechat_link.crypto import decrypt_aes_ecb, encrypt_aes_ecb, parse_cdn_aes_key


def build_cdn_download_url(*, encrypted_query_param: str, cdn_base_url: str) -> str:
    return f"{cdn_base_url}/download?encrypted_query_param={encrypted_query_param}"


def build_cdn_upload_url(*, upload_param: str, filekey: str, cdn_base_url: str) -> str:
    return f"{cdn_base_url}/upload?encrypted_query_param={upload_param}&filekey={filekey}"


def upload_buffer_to_cdn(
    *,
    buffer: bytes,
    upload_param: str,
    filekey: str,
    cdn_base_url: str,
    aes_key: bytes,
    transport: httpx.BaseTransport | None = None,
) -> str:
    ciphertext = encrypt_aes_ecb(buffer, aes_key)
    url = build_cdn_upload_url(
        upload_param=upload_param,
        filekey=filekey,
        cdn_base_url=cdn_base_url,
    )
    with httpx.Client(transport=transport) as client:
        response = client.post(
            url,
            content=ciphertext,
            headers={"Content-Type": "application/octet-stream"},
        )
    response.raise_for_status()
    download_param = response.headers.get("x-encrypted-param")
    if not download_param:
        raise ValueError("CDN upload response missing x-encrypted-param")
    return download_param


def download_and_decrypt_buffer(
    *,
    encrypted_query_param: str,
    aes_key_base64: str,
    cdn_base_url: str,
    transport: httpx.BaseTransport | None = None,
) -> bytes:
    url = build_cdn_download_url(
        encrypted_query_param=encrypted_query_param,
        cdn_base_url=cdn_base_url,
    )
    with httpx.Client(transport=transport) as client:
        response = client.get(url)
    response.raise_for_status()
    key = parse_cdn_aes_key(aes_key_base64)
    return decrypt_aes_ecb(response.content, key)


def download_plain_buffer(
    *,
    encrypted_query_param: str,
    cdn_base_url: str,
    transport: httpx.BaseTransport | None = None,
) -> bytes:
    url = build_cdn_download_url(
        encrypted_query_param=encrypted_query_param,
        cdn_base_url=cdn_base_url,
    )
    with httpx.Client(transport=transport) as client:
        response = client.get(url)
    response.raise_for_status()
    return response.content
