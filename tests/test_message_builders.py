import base64

import pytest

from wechat_link.models import UploadedMedia


def _uploaded_media(**overrides) -> UploadedMedia:
    payload = {
        "filekey": "file-1",
        "download_encrypted_query_param": "download-param",
        "aes_key_hex": "0123456789abcdef0123456789abcdef",
        "file_size": 18,
        "file_size_ciphertext": 32,
        "raw_md5": None,
        "thumb_download_encrypted_query_param": None,
        "thumb_file_size": None,
        "thumb_file_size_ciphertext": None,
        "thumb_width": None,
        "thumb_height": None,
    }
    payload.update(overrides)
    return UploadedMedia(**payload)


def test_build_outbound_payload_for_text_message() -> None:
    from wechat_link.message_builders import build_text_payload

    client_id, payload = build_text_payload(
        channel_version="0.1.0",
        to_user_id="user@im.wechat",
        text="hello",
        context_token="ctx-1",
        client_id="client-1",
    )

    assert client_id == "client-1"
    assert payload == {
        "msg": {
            "from_user_id": "",
            "to_user_id": "user@im.wechat",
            "client_id": "client-1",
            "message_type": 2,
            "message_state": 2,
            "context_token": "ctx-1",
            "item_list": [{"type": 1, "text_item": {"text": "hello"}}],
        },
        "base_info": {"channel_version": "0.1.0"},
    }


def test_build_outbound_payload_generates_client_id_when_missing() -> None:
    from wechat_link.message_builders import build_text_payload

    client_id, payload = build_text_payload(
        channel_version="0.1.0",
        to_user_id="user@im.wechat",
        text="hello",
        context_token="ctx-1",
    )

    assert client_id.startswith("wechat-link-")
    assert payload["msg"]["client_id"] == client_id


def test_build_outbound_payload_rejects_missing_context_token() -> None:
    from wechat_link.message_builders import build_text_payload

    with pytest.raises(ValueError, match="context_token"):
        build_text_payload(
            channel_version="0.1.0",
            to_user_id="user@im.wechat",
            text="hello",
            context_token="",
        )


def test_build_outbound_payload_for_image_message() -> None:
    from wechat_link.message_builders import build_image_payload

    client_id, payload = build_image_payload(
        channel_version="0.1.0",
        to_user_id="user@im.wechat",
        uploaded=_uploaded_media(),
        context_token="ctx-1",
        client_id="client-2",
    )

    assert client_id == "client-2"
    assert payload["msg"]["item_list"] == [
        {
            "type": 2,
            "image_item": {
                "media": {
                    "encrypt_query_param": "download-param",
                    "aes_key": base64.b64encode(
                        b"0123456789abcdef0123456789abcdef"
                    ).decode("utf-8"),
                    "encrypt_type": 1,
                },
                "mid_size": 32,
            },
        }
    ]


def test_build_outbound_payload_for_video_with_thumb() -> None:
    from wechat_link.message_builders import build_video_payload

    client_id, payload = build_video_payload(
        channel_version="0.1.0",
        to_user_id="user@im.wechat",
        uploaded=_uploaded_media(
            raw_md5="abc123",
            thumb_download_encrypted_query_param="thumb-download-param",
            thumb_file_size=12,
            thumb_file_size_ciphertext=16,
            thumb_width=120,
            thumb_height=80,
        ),
        context_token="ctx-1",
        client_id="client-3",
    )

    assert client_id == "client-3"
    assert payload["msg"]["item_list"] == [
        {
            "type": 5,
            "video_item": {
                "media": {
                    "encrypt_query_param": "download-param",
                    "aes_key": "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
                    "encrypt_type": 1,
                },
                "video_size": 32,
                "video_md5": "abc123",
                "thumb_media": {
                    "encrypt_query_param": "thumb-download-param",
                    "aes_key": "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
                    "encrypt_type": 1,
                },
                "thumb_size": 16,
                "thumb_height": 80,
                "thumb_width": 120,
            },
        }
    ]


def test_build_outbound_payload_for_voice_message() -> None:
    from wechat_link.message_builders import build_voice_payload

    client_id, payload = build_voice_payload(
        channel_version="0.1.0",
        to_user_id="user@im.wechat",
        uploaded=_uploaded_media(),
        context_token="ctx-1",
        client_id="client-4",
        encode_type=6,
        sample_rate=16000,
        playtime=1200,
        text="hello",
    )

    assert client_id == "client-4"
    assert payload["msg"]["item_list"] == [
        {
            "type": 3,
            "voice_item": {
                "media": {
                    "encrypt_query_param": "download-param",
                    "aes_key": "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
                    "encrypt_type": 1,
                },
                "encode_type": 6,
                "sample_rate": 16000,
                "playtime": 1200,
                "text": "hello",
            },
        }
    ]
