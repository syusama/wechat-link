import base64
import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from wechat_link.client import Client
from wechat_link.models import UploadedMedia


def test_get_upload_url_posts_expected_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/ilink/bot/getuploadurl"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload == {
            "filekey": "file-1",
            "media_type": 1,
            "to_user_id": "user@im.wechat",
            "rawsize": 10,
            "rawfilemd5": "abc",
            "filesize": 16,
            "thumb_rawsize": None,
            "thumb_rawfilemd5": None,
            "thumb_filesize": None,
            "no_need_thumb": True,
            "aeskey": "0123456789abcdef0123456789abcdef",
            "base_info": {"channel_version": "0.1.0"},
        }
        return httpx.Response(200, json={"upload_param": "upload-param", "thumb_upload_param": ""})

    client = Client(
        bot_token="bot-token",
        transport=httpx.MockTransport(handler),
        channel_version="0.1.0",
    )

    result = client.get_upload_url(
        filekey="file-1",
        media_type=1,
        to_user_id="user@im.wechat",
        rawsize=10,
        rawfilemd5="abc",
        filesize=16,
        no_need_thumb=True,
        aeskey="0123456789abcdef0123456789abcdef",
    )

    assert result.upload_param == "upload-param"


def test_upload_image_calls_get_upload_url_and_cdn(tmp_path: Path) -> None:
    image_path = tmp_path / "demo.jpg"
    image_path.write_bytes(b"wechat-link-image")

    def api_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/ilink/bot/getuploadurl"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["media_type"] == 1
        assert payload["to_user_id"] == "user@im.wechat"
        assert payload["no_need_thumb"] is True
        return httpx.Response(200, json={"upload_param": "upload-param"})

    def cdn_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/c2c/upload"
        assert request.url.params["encrypted_query_param"] == "upload-param"
        return httpx.Response(200, headers={"x-encrypted-param": "download-param"})

    client = Client(
        bot_token="bot-token",
        transport=httpx.MockTransport(api_handler),
        cdn_transport=httpx.MockTransport(cdn_handler),
        channel_version="0.1.0",
    )

    uploaded = client.upload_image(
        file_path=image_path,
        to_user_id="user@im.wechat",
    )

    assert uploaded.download_encrypted_query_param == "download-param"
    assert uploaded.file_size == len(b"wechat-link-image")
    assert uploaded.file_size_ciphertext == 32
    assert len(uploaded.aes_key_hex) == 32


def test_send_image_posts_expected_message_shape() -> None:
    uploaded = UploadedMedia(
        filekey="file-1",
        download_encrypted_query_param="download-param",
        aes_key_hex="0123456789abcdef0123456789abcdef",
        file_size=18,
        file_size_ciphertext=32,
    )

    def handler(request: httpx.Request) -> httpx.Response:
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
                "item_list": [
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
                ],
            },
            "base_info": {"channel_version": "0.1.0"},
        }
        return httpx.Response(200, json={"ret": 0})

    client = Client(
        bot_token="bot-token",
        transport=httpx.MockTransport(handler),
        channel_version="0.1.0",
    )

    result = client.send_image(
        to_user_id="user@im.wechat",
        uploaded=uploaded,
        context_token="ctx-1",
        client_id="client-1",
    )

    assert result == "client-1"


def test_send_file_posts_expected_message_shape() -> None:
    uploaded = UploadedMedia(
        filekey="file-1",
        download_encrypted_query_param="download-param",
        aes_key_hex="0123456789abcdef0123456789abcdef",
        file_size=18,
        file_size_ciphertext=32,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/ilink/bot/sendmessage"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["msg"]["item_list"] == [
            {
                "type": 4,
                "file_item": {
                    "media": {
                        "encrypt_query_param": "download-param",
                        "aes_key": "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
                        "encrypt_type": 1,
                    },
                    "file_name": "report.txt",
                    "len": "18",
                },
            }
        ]
        return httpx.Response(200, json={"ret": 0})

    client = Client(
        bot_token="bot-token",
        transport=httpx.MockTransport(handler),
        channel_version="0.1.0",
    )

    result = client.send_file(
        to_user_id="user@im.wechat",
        file_name="report.txt",
        uploaded=uploaded,
        context_token="ctx-1",
        client_id="client-2",
    )

    assert result == "client-2"


def test_send_image_requires_context_token() -> None:
    client = Client()

    with pytest.raises(ValueError, match="context_token"):
        client.send_image(
            to_user_id="user@im.wechat",
            uploaded=UploadedMedia(
                filekey="file-1",
                download_encrypted_query_param="download-param",
                aes_key_hex="0123456789abcdef0123456789abcdef",
                file_size=18,
                file_size_ciphertext=32,
            ),
            context_token="",
        )


def test_upload_video_calls_get_upload_url_with_video_media_type(tmp_path: Path) -> None:
    video_path = tmp_path / "demo.mp4"
    video_path.write_bytes(b"wechat-link-video")

    def api_handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["media_type"] == 2
        return httpx.Response(200, json={"upload_param": "upload-param"})

    def cdn_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"x-encrypted-param": "download-param"})

    client = Client(
        bot_token="bot-token",
        transport=httpx.MockTransport(api_handler),
        cdn_transport=httpx.MockTransport(cdn_handler),
        channel_version="0.1.0",
    )

    uploaded = client.upload_video(
        file_path=video_path,
        to_user_id="user@im.wechat",
    )

    assert uploaded.download_encrypted_query_param == "download-param"


def test_upload_voice_calls_get_upload_url_with_voice_media_type(tmp_path: Path) -> None:
    voice_path = tmp_path / "demo.silk"
    voice_path.write_bytes(b"wechat-link-voice")

    def api_handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["media_type"] == 4
        return httpx.Response(200, json={"upload_param": "upload-param"})

    def cdn_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"x-encrypted-param": "download-param"})

    client = Client(
        bot_token="bot-token",
        transport=httpx.MockTransport(api_handler),
        cdn_transport=httpx.MockTransport(cdn_handler),
        channel_version="0.1.0",
    )

    uploaded = client.upload_voice(
        file_path=voice_path,
        to_user_id="user@im.wechat",
    )

    assert uploaded.download_encrypted_query_param == "download-param"


def test_send_video_posts_expected_message_shape() -> None:
    uploaded = UploadedMedia(
        filekey="file-1",
        download_encrypted_query_param="download-param",
        aes_key_hex="0123456789abcdef0123456789abcdef",
        file_size=18,
        file_size_ciphertext=32,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
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
                },
            }
        ]
        return httpx.Response(200, json={"ret": 0})

    client = Client(
        bot_token="bot-token",
        transport=httpx.MockTransport(handler),
        channel_version="0.1.0",
    )

    result = client.send_video(
        to_user_id="user@im.wechat",
        uploaded=uploaded,
        context_token="ctx-1",
        client_id="client-3",
    )

    assert result == "client-3"


def test_send_voice_posts_expected_message_shape() -> None:
    uploaded = UploadedMedia(
        filekey="file-1",
        download_encrypted_query_param="download-param",
        aes_key_hex="0123456789abcdef0123456789abcdef",
        file_size=18,
        file_size_ciphertext=32,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
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
        return httpx.Response(200, json={"ret": 0})

    client = Client(
        bot_token="bot-token",
        transport=httpx.MockTransport(handler),
        channel_version="0.1.0",
    )

    result = client.send_voice(
        to_user_id="user@im.wechat",
        uploaded=uploaded,
        context_token="ctx-1",
        client_id="client-4",
        encode_type=6,
        sample_rate=16000,
        playtime=1200,
        text="hello",
    )

    assert result == "client-4"


def test_upload_video_with_thumb_posts_thumb_metadata_and_uploads_twice(tmp_path: Path) -> None:
    video_path = tmp_path / "demo.mp4"
    thumb_path = tmp_path / "thumb.jpg"
    video_path.write_bytes(b"wechat-link-video")
    Image.new("RGB", (120, 80), color="red").save(thumb_path, format="JPEG")
    seen_upload_paths: list[str] = []

    def api_handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["media_type"] == 2
        assert payload["no_need_thumb"] is False
        assert payload["thumb_rawsize"] > 0
        assert payload["thumb_rawfilemd5"]
        assert payload["thumb_filesize"] >= payload["thumb_rawsize"]
        return httpx.Response(
            200,
            json={"upload_param": "upload-param", "thumb_upload_param": "thumb-upload-param"},
        )

    def cdn_handler(request: httpx.Request) -> httpx.Response:
        seen_upload_paths.append(request.url.params["encrypted_query_param"])
        return httpx.Response(
            200,
            headers={"x-encrypted-param": f"download-{request.url.params['encrypted_query_param']}"},
        )

    client = Client(
        bot_token="bot-token",
        transport=httpx.MockTransport(api_handler),
        cdn_transport=httpx.MockTransport(cdn_handler),
        channel_version="0.1.0",
    )

    uploaded = client.upload_video(
        file_path=video_path,
        to_user_id="user@im.wechat",
        thumb_path=thumb_path,
    )

    assert seen_upload_paths == ["upload-param", "thumb-upload-param"]
    assert uploaded.thumb_download_encrypted_query_param == "download-thumb-upload-param"
    assert uploaded.thumb_width == 120
    assert uploaded.thumb_height == 80
    assert uploaded.thumb_file_size and uploaded.thumb_file_size > 0
    assert uploaded.thumb_file_size_ciphertext and uploaded.thumb_file_size_ciphertext >= uploaded.thumb_file_size


def test_send_video_includes_thumb_media_when_present() -> None:
    uploaded = UploadedMedia(
        filekey="file-1",
        download_encrypted_query_param="download-param",
        aes_key_hex="0123456789abcdef0123456789abcdef",
        file_size=18,
        file_size_ciphertext=32,
        thumb_download_encrypted_query_param="thumb-download-param",
        thumb_file_size=12,
        thumb_file_size_ciphertext=16,
        thumb_width=120,
        thumb_height=80,
        raw_md5="abc123",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
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
        return httpx.Response(200, json={"ret": 0})

    client = Client(
        bot_token="bot-token",
        transport=httpx.MockTransport(handler),
        channel_version="0.1.0",
    )

    result = client.send_video(
        to_user_id="user@im.wechat",
        uploaded=uploaded,
        context_token="ctx-1",
        client_id="client-5",
    )

    assert result == "client-5"
