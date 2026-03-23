from __future__ import annotations

import uuid

from wechat_link.crypto import encode_cdn_aes_key_from_hex
from wechat_link.models import UploadedMedia


def _require_context_token(context_token: str) -> str:
    if not context_token:
        raise ValueError("context_token is required")
    return context_token


def _resolve_client_id(client_id: str | None) -> str:
    return client_id or f"wechat-link-{uuid.uuid4().hex}"


def _base_info(channel_version: str) -> dict[str, dict[str, str]]:
    return {"base_info": {"channel_version": channel_version}}


def _encrypted_media(uploaded: UploadedMedia) -> dict[str, object]:
    return {
        "encrypt_query_param": uploaded.download_encrypted_query_param,
        "aes_key": encode_cdn_aes_key_from_hex(uploaded.aes_key_hex),
        "encrypt_type": 1,
    }


def _thumb_media(uploaded: UploadedMedia) -> dict[str, object]:
    return {
        "encrypt_query_param": uploaded.thumb_download_encrypted_query_param,
        "aes_key": encode_cdn_aes_key_from_hex(uploaded.aes_key_hex),
        "encrypt_type": 1,
    }


def _build_payload(
    *,
    channel_version: str,
    to_user_id: str,
    context_token: str,
    item_list: list[dict[str, object]],
    client_id: str | None = None,
) -> tuple[str, dict[str, object]]:
    outbound_client_id = _resolve_client_id(client_id)
    payload = {
        "msg": {
            "from_user_id": "",
            "to_user_id": to_user_id,
            "client_id": outbound_client_id,
            "message_type": 2,
            "message_state": 2,
            "context_token": _require_context_token(context_token),
            "item_list": item_list,
        },
        **_base_info(channel_version),
    }
    return outbound_client_id, payload


def build_text_payload(
    *,
    channel_version: str,
    to_user_id: str,
    text: str,
    context_token: str,
    client_id: str | None = None,
) -> tuple[str, dict[str, object]]:
    return _build_payload(
        channel_version=channel_version,
        to_user_id=to_user_id,
        context_token=context_token,
        client_id=client_id,
        item_list=[{"type": 1, "text_item": {"text": text}}],
    )


def build_image_payload(
    *,
    channel_version: str,
    to_user_id: str,
    uploaded: UploadedMedia,
    context_token: str,
    client_id: str | None = None,
) -> tuple[str, dict[str, object]]:
    return _build_payload(
        channel_version=channel_version,
        to_user_id=to_user_id,
        context_token=context_token,
        client_id=client_id,
        item_list=[
            {
                "type": 2,
                "image_item": {
                    "media": _encrypted_media(uploaded),
                    "mid_size": uploaded.file_size_ciphertext,
                },
            }
        ],
    )


def build_file_payload(
    *,
    channel_version: str,
    to_user_id: str,
    file_name: str,
    uploaded: UploadedMedia,
    context_token: str,
    client_id: str | None = None,
) -> tuple[str, dict[str, object]]:
    return _build_payload(
        channel_version=channel_version,
        to_user_id=to_user_id,
        context_token=context_token,
        client_id=client_id,
        item_list=[
            {
                "type": 4,
                "file_item": {
                    "media": _encrypted_media(uploaded),
                    "file_name": file_name,
                    "len": str(uploaded.file_size),
                },
            }
        ],
    )


def build_video_payload(
    *,
    channel_version: str,
    to_user_id: str,
    uploaded: UploadedMedia,
    context_token: str,
    client_id: str | None = None,
) -> tuple[str, dict[str, object]]:
    video_item: dict[str, object] = {
        "media": _encrypted_media(uploaded),
        "video_size": uploaded.file_size_ciphertext,
    }
    if uploaded.raw_md5 is not None:
        video_item["video_md5"] = uploaded.raw_md5
    if uploaded.thumb_download_encrypted_query_param:
        video_item["thumb_media"] = _thumb_media(uploaded)
    if uploaded.thumb_file_size_ciphertext is not None:
        video_item["thumb_size"] = uploaded.thumb_file_size_ciphertext
    if uploaded.thumb_height is not None:
        video_item["thumb_height"] = uploaded.thumb_height
    if uploaded.thumb_width is not None:
        video_item["thumb_width"] = uploaded.thumb_width

    return _build_payload(
        channel_version=channel_version,
        to_user_id=to_user_id,
        context_token=context_token,
        client_id=client_id,
        item_list=[{"type": 5, "video_item": video_item}],
    )


def build_voice_payload(
    *,
    channel_version: str,
    to_user_id: str,
    uploaded: UploadedMedia,
    context_token: str,
    client_id: str | None = None,
    encode_type: int | None = None,
    bits_per_sample: int | None = None,
    sample_rate: int | None = None,
    playtime: int | None = None,
    text: str | None = None,
) -> tuple[str, dict[str, object]]:
    voice_item: dict[str, object] = {
        "media": _encrypted_media(uploaded),
    }
    if encode_type is not None:
        voice_item["encode_type"] = encode_type
    if bits_per_sample is not None:
        voice_item["bits_per_sample"] = bits_per_sample
    if sample_rate is not None:
        voice_item["sample_rate"] = sample_rate
    if playtime is not None:
        voice_item["playtime"] = playtime
    if text is not None:
        voice_item["text"] = text

    return _build_payload(
        channel_version=channel_version,
        to_user_id=to_user_id,
        context_token=context_token,
        client_id=client_id,
        item_list=[{"type": 3, "voice_item": voice_item}],
    )
