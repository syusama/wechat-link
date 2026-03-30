from __future__ import annotations

from pathlib import Path
import zipfile

from wechat_link.models import UploadedMedia, WeixinMessage
from wechat_link.openclaw_adapter import OpenClawWeixinAdapter, markdown_to_plain_text
from wechat_link.store import FileContextTokenStore


class FakeOpenClawClient:
    def __init__(self) -> None:
        self.download_calls: list[tuple[str, bool]] = []
        self.send_calls: list[tuple[str, dict[str, object]]] = []

    def download_message_item(self, item, *, thumb: bool = False) -> bytes:
        self.download_calls.append((item.kind, thumb))
        payloads = {
            "image": b"image-bytes",
            "video": b"video-bytes",
            "file": b"file-bytes",
            "voice": b"voice-bytes",
        }
        return payloads[item.kind]

    def send_text(
        self,
        *,
        to_user_id: str,
        text: str,
        context_token: str,
        client_id: str | None = None,
    ) -> str:
        self.send_calls.append(
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
        return client_id or "text-client-id"

    def upload_image(self, *, file_path: str | Path, to_user_id: str) -> UploadedMedia:
        self.send_calls.append(
            (
                "upload_image",
                {
                    "file_path": Path(file_path).name,
                    "to_user_id": to_user_id,
                },
            )
        )
        return UploadedMedia(
            filekey="image-filekey",
            download_encrypted_query_param="image-download-param",
            aes_key_hex="0123456789abcdef0123456789abcdef",
            file_size=11,
            file_size_ciphertext=16,
        )

    def send_image(
        self,
        *,
        to_user_id: str,
        uploaded: UploadedMedia,
        context_token: str,
        client_id: str | None = None,
    ) -> str:
        self.send_calls.append(
            (
                "send_image",
                {
                    "to_user_id": to_user_id,
                    "uploaded": uploaded.filekey,
                    "context_token": context_token,
                    "client_id": client_id,
                },
            )
        )
        return client_id or "image-client-id"

    def upload_video(
        self,
        *,
        file_path: str | Path,
        to_user_id: str,
        thumb_path: str | Path | None = None,
    ) -> UploadedMedia:
        self.send_calls.append(
            (
                "upload_video",
                {
                    "file_path": Path(file_path).name,
                    "to_user_id": to_user_id,
                    "thumb_path": Path(thumb_path).name if thumb_path else None,
                },
            )
        )
        return UploadedMedia(
            filekey="video-filekey",
            download_encrypted_query_param="video-download-param",
            aes_key_hex="0123456789abcdef0123456789abcdef",
            file_size=11,
            file_size_ciphertext=16,
        )

    def send_video(
        self,
        *,
        to_user_id: str,
        uploaded: UploadedMedia,
        context_token: str,
        client_id: str | None = None,
    ) -> str:
        self.send_calls.append(
            (
                "send_video",
                {
                    "to_user_id": to_user_id,
                    "uploaded": uploaded.filekey,
                    "context_token": context_token,
                    "client_id": client_id,
                },
            )
        )
        return client_id or "video-client-id"

    def upload_file(self, *, file_path: str | Path, to_user_id: str) -> UploadedMedia:
        self.send_calls.append(
            (
                "upload_file",
                {
                    "file_path": Path(file_path).name,
                    "to_user_id": to_user_id,
                },
            )
        )
        return UploadedMedia(
            filekey="file-filekey",
            download_encrypted_query_param="file-download-param",
            aes_key_hex="0123456789abcdef0123456789abcdef",
            file_size=11,
            file_size_ciphertext=16,
        )

    def send_file(
        self,
        *,
        to_user_id: str,
        file_name: str,
        uploaded: UploadedMedia,
        context_token: str,
        client_id: str | None = None,
    ) -> str:
        self.send_calls.append(
            (
                "send_file",
                {
                    "to_user_id": to_user_id,
                    "file_name": file_name,
                    "uploaded": uploaded.filekey,
                    "context_token": context_token,
                    "client_id": client_id,
                },
            )
        )
        return client_id or "file-client-id"

    def upload_voice(self, *, file_path: str | Path, to_user_id: str) -> UploadedMedia:
        self.send_calls.append(
            (
                "upload_voice",
                {
                    "file_path": Path(file_path).name,
                    "to_user_id": to_user_id,
                },
            )
        )
        return UploadedMedia(
            filekey="voice-filekey",
            download_encrypted_query_param="voice-download-param",
            aes_key_hex="0123456789abcdef0123456789abcdef",
            file_size=11,
            file_size_ciphertext=16,
        )

    def send_voice(
        self,
        *,
        to_user_id: str,
        uploaded: UploadedMedia,
        context_token: str,
        client_id: str | None = None,
        encode_type: int | None = None,
        bits_per_sample: int | None = None,
        sample_rate: int | None = None,
        playtime: int | None = None,
        text: str | None = None,
    ) -> str:
        self.send_calls.append(
            (
                "send_voice",
                {
                    "to_user_id": to_user_id,
                    "uploaded": uploaded.filekey,
                    "context_token": context_token,
                    "client_id": client_id,
                    "encode_type": encode_type,
                    "bits_per_sample": bits_per_sample,
                    "sample_rate": sample_rate,
                    "playtime": playtime,
                    "text": text,
                },
            )
        )
        return client_id or "voice-client-id"


def test_build_inbound_context_downloads_priority_media_and_persists_context_token(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    store = FileContextTokenStore(state_dir)
    adapter = OpenClawWeixinAdapter(
        FakeOpenClawClient(),
        account_id="wx-account-1",
        state_dir=state_dir,
        context_token_store=store,
    )
    message = WeixinMessage.from_dict(
        {
            "from_user_id": "user@im.wechat",
            "to_user_id": "bot@im.bot",
            "context_token": "ctx-1",
            "create_time_ms": 1710000000000,
            "item_list": [
                {"type": 1, "text_item": {"text": "hello from wechat"}},
                {
                    "type": 4,
                    "file_item": {
                        "media": {
                            "encrypt_query_param": "file-download-param",
                            "aes_key": "MDEyMzQ1Njc4OWFiY2RlZg==",
                            "encrypt_type": 1,
                        },
                        "file_name": "report.md",
                    },
                },
                {
                    "type": 2,
                    "image_item": {
                        "media": {
                            "encrypt_query_param": "image-download-param",
                            "aes_key": "MDEyMzQ1Njc4OWFiY2RlZg==",
                            "encrypt_type": 1,
                        }
                    },
                },
            ],
        }
    )

    context = adapter.build_inbound_context(message)

    assert context.Body == "hello from wechat"
    assert context.From == "user@im.wechat"
    assert context.To == "user@im.wechat"
    assert context.AccountId == "wx-account-1"
    assert context.OriginatingChannel == "openclaw-weixin"
    assert context.OriginatingTo == "user@im.wechat"
    assert context.Provider == "openclaw-weixin"
    assert context.ChatType == "direct"
    assert context.Timestamp == 1710000000000
    assert context.context_token == "ctx-1"
    assert context.MessageSid.startswith("openclaw-weixin-")
    assert context.MediaType == "image/*"
    assert context.MediaPath is not None
    assert Path(context.MediaPath).exists()
    assert Path(context.MediaPath).read_bytes() == b"image-bytes"
    assert store.load("wx-account-1", "user@im.wechat") == "ctx-1"
    assert adapter.client.download_calls == [("image", False)]


def test_build_inbound_context_uses_quoted_media_when_main_message_has_only_text(
    tmp_path: Path,
) -> None:
    adapter = OpenClawWeixinAdapter(
        FakeOpenClawClient(),
        account_id="wx-account-1",
        state_dir=tmp_path / "state",
    )
    message = WeixinMessage.from_dict(
        {
            "from_user_id": "user@im.wechat",
            "context_token": "ctx-1",
            "item_list": [
                {
                    "type": 1,
                    "text_item": {"text": "follow up"},
                    "ref_msg": {
                        "title": "quoted-image",
                        "message_item": {
                            "type": 2,
                            "image_item": {
                                "media": {
                                    "encrypt_query_param": "ref-image-download-param",
                                    "aes_key": "MDEyMzQ1Njc4OWFiY2RlZg==",
                                    "encrypt_type": 1,
                                }
                            },
                        },
                    },
                }
            ],
        }
    )

    context = adapter.build_inbound_context(message)

    assert context.Body == "follow up"
    assert context.MediaType == "image/*"
    assert context.MediaPath is not None
    assert Path(context.MediaPath).read_bytes() == b"image-bytes"
    assert adapter.client.download_calls == [("image", False)]


def test_build_inbound_context_formats_quoted_text_body_and_skips_voice_download_when_transcript_exists(
    tmp_path: Path,
) -> None:
    adapter = OpenClawWeixinAdapter(
        FakeOpenClawClient(),
        account_id="wx-account-1",
        state_dir=tmp_path / "state",
    )
    quoted = "[\u5f15\u7528: previous | original body]\nreply body"
    message = WeixinMessage.from_dict(
        {
            "from_user_id": "user@im.wechat",
            "item_list": [
                {
                    "type": 1,
                    "text_item": {"text": "reply body"},
                    "ref_msg": {
                        "title": "previous",
                        "message_item": {
                            "type": 1,
                            "text_item": {"text": "original body"},
                        },
                    },
                },
                {
                    "type": 3,
                    "voice_item": {
                        "text": "voice transcript",
                        "media": {
                            "encrypt_query_param": "voice-download-param",
                            "aes_key": "MDEyMzQ1Njc4OWFiY2RlZg==",
                            "encrypt_type": 1,
                        },
                    },
                },
            ],
        }
    )

    context = adapter.build_inbound_context(message)

    assert context.Body == quoted
    assert context.MediaPath is None
    assert context.MediaType is None
    assert adapter.client.download_calls == []


def test_markdown_to_plain_text_strips_links_images_and_code_fences() -> None:
    text = "**Bold** [docs](https://example.com)\n![alt](https://example.com/image.png)\n```python\nprint('x')\n```"

    lines = [line for line in markdown_to_plain_text(text).splitlines() if line.strip()]

    assert lines == ["Bold docs", "print('x')"]


def test_send_reply_uses_stored_context_token_and_routes_image_media(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    store = FileContextTokenStore(state_dir)
    store.save("wx-account-1", "user@im.wechat", "ctx-1")
    adapter = OpenClawWeixinAdapter(
        FakeOpenClawClient(),
        account_id="wx-account-1",
        state_dir=state_dir,
        context_token_store=store,
    )
    image_path = tmp_path / "reply.png"
    image_path.write_bytes(b"image")

    client_id = adapter.send_reply(
        to_user_id="user@im.wechat",
        text="**caption**",
        media_path=image_path,
    )

    assert client_id == "image-client-id"
    assert adapter.client.send_calls == [
        (
            "send_text",
            {
                "to_user_id": "user@im.wechat",
                "text": "caption",
                "context_token": "ctx-1",
                "client_id": None,
            },
        ),
        (
            "upload_image",
            {
                "file_path": "reply.png",
                "to_user_id": "user@im.wechat",
            },
        ),
        (
            "send_image",
            {
                "to_user_id": "user@im.wechat",
                "uploaded": "image-filekey",
                "context_token": "ctx-1",
                "client_id": None,
            },
        ),
    ]


def test_send_reply_uses_distinct_client_ids_for_text_and_media(tmp_path: Path) -> None:
    adapter = OpenClawWeixinAdapter(
        FakeOpenClawClient(),
        account_id="wx-account-1",
        state_dir=tmp_path / "state",
    )
    context = adapter.build_outbound_context(
        to_user_id="user@im.wechat",
        context_token="ctx-1",
    )
    image_path = tmp_path / "reply.png"
    image_path.write_bytes(b"image")

    client_id = adapter.send_reply_from_context(
        context,
        text="caption",
        media_path=image_path,
        client_id="media-client-id",
    )

    assert client_id == "media-client-id"
    assert adapter.client.send_calls == [
        (
            "send_text",
            {
                "to_user_id": "user@im.wechat",
                "text": "caption",
                "context_token": "ctx-1",
                "client_id": None,
            },
        ),
        (
            "upload_image",
            {
                "file_path": "reply.png",
                "to_user_id": "user@im.wechat",
            },
        ),
        (
            "send_image",
            {
                "to_user_id": "user@im.wechat",
                "uploaded": "image-filekey",
                "context_token": "ctx-1",
                "client_id": "media-client-id",
            },
        ),
    ]


def test_send_reply_routes_non_image_non_video_media_as_file_attachment(
    tmp_path: Path,
) -> None:
    adapter = OpenClawWeixinAdapter(
        FakeOpenClawClient(),
        account_id="wx-account-1",
        state_dir=tmp_path / "state",
    )
    context = adapter.build_outbound_context(
        to_user_id="user@im.wechat",
        context_token="ctx-1",
    )
    file_path = tmp_path / "report.md"
    file_path.write_text("# report", encoding="utf-8")

    client_id = adapter.send_reply_from_context(
        context,
        media_path=file_path,
    )

    assert client_id == "file-client-id"
    assert adapter.client.send_calls == [
        (
            "upload_file",
            {
                "file_path": "report.md",
                "to_user_id": "user@im.wechat",
            },
        ),
        (
            "send_file",
            {
                "to_user_id": "user@im.wechat",
                "file_name": "report.md",
                "uploaded": "file-filekey",
                "context_token": "ctx-1",
                "client_id": None,
            },
        ),
    ]


def test_build_inbound_context_auto_extracts_zip_and_points_media_to_first_extracted_file(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("docs/readme.md", "# readme")
        archive.writestr("notes/todo.txt", "todo")

    adapter = OpenClawWeixinAdapter(
        FakeOpenClawClient(),
        account_id="wx-account-1",
        state_dir=tmp_path / "state",
    )
    message = WeixinMessage.from_dict(
        {
            "from_user_id": "user@im.wechat",
            "item_list": [
                {
                    "type": 4,
                    "file_item": {
                        "media": {
                            "encrypt_query_param": "file-download-param",
                            "aes_key": "MDEyMzQ1Njc4OWFiY2RlZg==",
                            "encrypt_type": 1,
                        },
                        "file_name": "bundle.zip",
                    },
                }
            ],
        }
    )
    adapter.client.download_message_item = lambda item, thumb=False: archive_path.read_bytes()

    context = adapter.build_inbound_context(message)

    assert context.ArchiveExtracted is True
    assert context.ArchivePath is not None
    assert Path(context.ArchivePath).exists()
    assert context.MediaDir is not None
    assert Path(context.MediaDir).is_dir()
    assert context.MediaPath is not None
    assert Path(context.MediaPath).exists()
    assert context.MediaType == "text/markdown"
    assert context.MediaPaths is not None
    assert context.MediaTypes is not None
    assert len(context.MediaPaths) == 2
    assert sorted(Path(path).name for path in context.MediaPaths) == ["readme.md", "todo.txt"]
    assert sorted(context.MediaTypes) == ["text/markdown", "text/plain"]
    assert "Archive extracted: bundle.zip" in context.Body
    assert "- docs/readme.md" in context.Body
    assert "- notes/todo.txt" in context.Body


def test_send_reply_routes_audio_media_as_voice_message(tmp_path: Path) -> None:
    adapter = OpenClawWeixinAdapter(
        FakeOpenClawClient(),
        account_id="wx-account-1",
        state_dir=tmp_path / "state",
    )
    context = adapter.build_outbound_context(
        to_user_id="user@im.wechat",
        context_token="ctx-1",
    )
    audio_path = tmp_path / "reply.wav"
    audio_path.write_bytes(b"wav")

    client_id = adapter.send_reply_from_context(
        context,
        text="voice reply",
        media_path=audio_path,
    )

    assert client_id == "voice-client-id"
    assert adapter.client.send_calls == [
        (
            "send_text",
            {
                "to_user_id": "user@im.wechat",
                "text": "voice reply",
                "context_token": "ctx-1",
                "client_id": None,
            },
        ),
        (
            "upload_voice",
            {
                "file_path": "reply.wav",
                "to_user_id": "user@im.wechat",
            },
        ),
        (
            "send_voice",
            {
                "to_user_id": "user@im.wechat",
                "uploaded": "voice-filekey",
                "context_token": "ctx-1",
                "client_id": None,
                "encode_type": None,
                "bits_per_sample": None,
                "sample_rate": None,
                "playtime": None,
                "text": None,
            },
        ),
    ]
