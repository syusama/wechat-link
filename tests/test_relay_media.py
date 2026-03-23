from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi.testclient import TestClient

from wechat_link.models import UploadedMedia
from wechat_link.relay import create_relay_app


class FakeRelayMediaClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def _uploaded(self, suffix: str) -> UploadedMedia:
        return UploadedMedia(
            filekey=f"file-{suffix}",
            download_encrypted_query_param=f"download-{suffix}",
            aes_key_hex="0123456789abcdef0123456789abcdef",
            file_size=18,
            file_size_ciphertext=32,
        )

    def upload_image(self, *, file_path: str | Path, to_user_id: str) -> UploadedMedia:
        self.calls.append(("upload_image", {"file_path": Path(file_path).name, "to_user_id": to_user_id}))
        return self._uploaded("image")

    def send_image(self, *, to_user_id: str, uploaded: UploadedMedia, context_token: str, client_id: str | None = None) -> str:
        self.calls.append(
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
        return client_id or "generated-image-client"

    def upload_file(self, *, file_path: str | Path, to_user_id: str) -> UploadedMedia:
        self.calls.append(("upload_file", {"file_path": Path(file_path).name, "to_user_id": to_user_id}))
        return self._uploaded("file")

    def send_file(
        self,
        *,
        to_user_id: str,
        file_name: str,
        uploaded: UploadedMedia,
        context_token: str,
        client_id: str | None = None,
    ) -> str:
        self.calls.append(
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
        return client_id or "generated-file-client"

    def upload_video(
        self,
        *,
        file_path: str | Path,
        to_user_id: str,
        thumb_path: str | Path | None = None,
    ) -> UploadedMedia:
        self.calls.append(
            (
                "upload_video",
                {
                    "file_path": Path(file_path).name,
                    "to_user_id": to_user_id,
                    "thumb_path": Path(thumb_path).name if thumb_path else None,
                },
            )
        )
        return self._uploaded("video")

    def send_video(self, *, to_user_id: str, uploaded: UploadedMedia, context_token: str, client_id: str | None = None) -> str:
        self.calls.append(
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
        return client_id or "generated-video-client"

    def upload_voice(self, *, file_path: str | Path, to_user_id: str) -> UploadedMedia:
        self.calls.append(("upload_voice", {"file_path": Path(file_path).name, "to_user_id": to_user_id}))
        return self._uploaded("voice")

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
        self.calls.append(
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
        return client_id or "generated-voice-client"


def test_relay_image_upload_endpoint_uploads_and_sends() -> None:
    fake_client = FakeRelayMediaClient()
    app = create_relay_app(client=fake_client)
    http_client = TestClient(app)

    response = http_client.post(
        "/messages/image/upload",
        data={"to_user_id": "user@im.wechat", "context_token": "ctx-1", "client_id": "client-image"},
        files={"file": ("demo.jpg", b"image-bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "client_id": "client-image",
        "uploaded": asdict(fake_client._uploaded("image")),
    }
    assert fake_client.calls == [
        ("upload_image", {"file_path": "demo.jpg", "to_user_id": "user@im.wechat"}),
        (
            "send_image",
            {
                "to_user_id": "user@im.wechat",
                "uploaded": "file-image",
                "context_token": "ctx-1",
                "client_id": "client-image",
            },
        ),
    ]


def test_relay_file_upload_endpoint_uploads_and_sends() -> None:
    fake_client = FakeRelayMediaClient()
    app = create_relay_app(client=fake_client)
    http_client = TestClient(app)

    response = http_client.post(
        "/messages/file/upload",
        data={"to_user_id": "user@im.wechat", "context_token": "ctx-1", "client_id": "client-file"},
        files={"file": ("report.txt", b"report", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["client_id"] == "client-file"
    assert response.json()["uploaded"]["filekey"] == "file-file"
    assert fake_client.calls == [
        ("upload_file", {"file_path": "report.txt", "to_user_id": "user@im.wechat"}),
        (
            "send_file",
            {
                "to_user_id": "user@im.wechat",
                "file_name": "report.txt",
                "uploaded": "file-file",
                "context_token": "ctx-1",
                "client_id": "client-file",
            },
        ),
    ]


def test_relay_video_upload_endpoint_uploads_and_sends() -> None:
    fake_client = FakeRelayMediaClient()
    app = create_relay_app(client=fake_client)
    http_client = TestClient(app)

    response = http_client.post(
        "/messages/video/upload",
        data={"to_user_id": "user@im.wechat", "context_token": "ctx-1", "client_id": "client-video"},
        files={"file": ("demo.mp4", b"video", "video/mp4")},
    )

    assert response.status_code == 200
    assert response.json()["client_id"] == "client-video"
    assert response.json()["uploaded"]["filekey"] == "file-video"
    assert fake_client.calls == [
        ("upload_video", {"file_path": "demo.mp4", "to_user_id": "user@im.wechat", "thumb_path": None}),
        (
            "send_video",
            {
                "to_user_id": "user@im.wechat",
                "uploaded": "file-video",
                "context_token": "ctx-1",
                "client_id": "client-video",
            },
        ),
    ]


def test_relay_video_upload_endpoint_accepts_optional_thumb_file() -> None:
    fake_client = FakeRelayMediaClient()
    app = create_relay_app(client=fake_client)
    http_client = TestClient(app)

    response = http_client.post(
        "/messages/video/upload",
        data={"to_user_id": "user@im.wechat", "context_token": "ctx-1", "client_id": "client-video-thumb"},
        files={
            "file": ("demo.mp4", b"video", "video/mp4"),
            "thumb_file": ("thumb.jpg", b"thumb", "image/jpeg"),
        },
    )

    assert response.status_code == 200
    assert response.json()["client_id"] == "client-video-thumb"
    assert fake_client.calls == [
        ("upload_video", {"file_path": "demo.mp4", "to_user_id": "user@im.wechat", "thumb_path": "thumb.jpg"}),
        (
            "send_video",
            {
                "to_user_id": "user@im.wechat",
                "uploaded": "file-video",
                "context_token": "ctx-1",
                "client_id": "client-video-thumb",
            },
        ),
    ]


def test_relay_voice_upload_endpoint_uploads_and_sends_with_metadata() -> None:
    fake_client = FakeRelayMediaClient()
    app = create_relay_app(client=fake_client)
    http_client = TestClient(app)

    response = http_client.post(
        "/messages/voice/upload",
        data={
            "to_user_id": "user@im.wechat",
            "context_token": "ctx-1",
            "client_id": "client-voice",
            "encode_type": "6",
            "sample_rate": "16000",
            "playtime": "1200",
            "text": "hello",
        },
        files={"file": ("demo.silk", b"voice", "audio/ogg")},
    )

    assert response.status_code == 200
    assert response.json()["client_id"] == "client-voice"
    assert response.json()["uploaded"]["filekey"] == "file-voice"
    assert fake_client.calls == [
        ("upload_voice", {"file_path": "demo.silk", "to_user_id": "user@im.wechat"}),
        (
            "send_voice",
            {
                "to_user_id": "user@im.wechat",
                "uploaded": "file-voice",
                "context_token": "ctx-1",
                "client_id": "client-voice",
                "encode_type": 6,
                "bits_per_sample": None,
                "sample_rate": 16000,
                "playtime": 1200,
                "text": "hello",
            },
        ),
    ]
