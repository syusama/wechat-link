from __future__ import annotations

from contextlib import contextmanager, suppress
from dataclasses import asdict
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Protocol

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel, Field

from wechat_link.store import FileCursorStore


class RelaySDKClient(Protocol):
    def get_bot_qrcode(self, *, bot_type: int = 3): ...

    def get_qrcode_status(self, qrcode: str): ...

    def get_config(self, *, ilink_user_id: str, context_token: str | None = None): ...

    def send_typing(self, *, ilink_user_id: str, typing_ticket: str, status: int = 1): ...

    def get_updates(self, *, cursor: str = ""): ...

    def send_text(
        self,
        *,
        to_user_id: str,
        text: str,
        context_token: str,
        client_id: str | None = None,
    ) -> str: ...

    def upload_image(self, *, file_path: str | Path, to_user_id: str): ...

    def send_image(
        self,
        *,
        to_user_id: str,
        uploaded,
        context_token: str,
        client_id: str | None = None,
    ) -> str: ...

    def upload_file(self, *, file_path: str | Path, to_user_id: str): ...

    def send_file(
        self,
        *,
        to_user_id: str,
        file_name: str,
        uploaded,
        context_token: str,
        client_id: str | None = None,
    ) -> str: ...

    def upload_video(
        self,
        *,
        file_path: str | Path,
        to_user_id: str,
        thumb_path: str | Path | None = None,
    ): ...

    def send_video(
        self,
        *,
        to_user_id: str,
        uploaded,
        context_token: str,
        client_id: str | None = None,
    ) -> str: ...

    def upload_voice(self, *, file_path: str | Path, to_user_id: str): ...

    def send_voice(
        self,
        *,
        to_user_id: str,
        uploaded,
        context_token: str,
        client_id: str | None = None,
        encode_type: int | None = None,
        bits_per_sample: int | None = None,
        sample_rate: int | None = None,
        playtime: int | None = None,
        text: str | None = None,
    ) -> str: ...


class ConfigRequest(BaseModel):
    ilink_user_id: str
    context_token: str | None = None


class TypingRequest(BaseModel):
    ilink_user_id: str
    typing_ticket: str
    status: int = Field(default=1)


class PollRequest(BaseModel):
    cursor: str | None = None


class TextMessageRequest(BaseModel):
    to_user_id: str
    text: str
    context_token: str
    client_id: str | None = None


def _save_upload_to_temp(file: UploadFile) -> Path:
    temp_dir = Path(mkdtemp(prefix="wechat-link-"))
    file_name = Path(file.filename or "upload.bin").name
    temp_path = temp_dir / file_name
    temp_path.write_bytes(file.file.read())
    return temp_path


def _cleanup_temp_path(temp_path: Path | None) -> None:
    if temp_path is None:
        return
    with suppress(FileNotFoundError):
        temp_path.unlink()
    with suppress(FileNotFoundError):
        rmtree(temp_path.parent)


@contextmanager
def _temporary_upload_path(file: UploadFile | None):
    if file is None:
        yield None
        return

    temp_path = _save_upload_to_temp(file)
    try:
        yield temp_path
    finally:
        _cleanup_temp_path(temp_path)


def _upload_and_send(upload, send) -> dict:
    uploaded = upload()
    message_client_id = send(uploaded)
    return {"client_id": message_client_id, "uploaded": asdict(uploaded)}


def create_relay_app(
    *,
    client: RelaySDKClient,
    cursor_store: FileCursorStore | None = None,
) -> FastAPI:
    app = FastAPI(title="wechat-link relay", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/login/qrcode")
    def login_qrcode(bot_type: int = 3) -> dict:
        return asdict(client.get_bot_qrcode(bot_type=bot_type))

    @app.get("/login/status")
    def login_status(qrcode: str) -> dict:
        return asdict(client.get_qrcode_status(qrcode))

    @app.post("/config")
    def get_config(payload: ConfigRequest) -> dict:
        return asdict(
            client.get_config(
                ilink_user_id=payload.ilink_user_id,
                context_token=payload.context_token,
            )
        )

    @app.post("/typing")
    def send_typing(payload: TypingRequest) -> dict:
        return asdict(
            client.send_typing(
                ilink_user_id=payload.ilink_user_id,
                typing_ticket=payload.typing_ticket,
                status=payload.status,
            )
        )

    @app.post("/updates/poll")
    def poll_updates(payload: PollRequest) -> dict:
        cursor = payload.cursor
        if cursor is None and cursor_store is not None:
            cursor = cursor_store.load()
        updates = client.get_updates(cursor=cursor or "")
        if cursor_store is not None and updates.next_cursor:
            cursor_store.save(updates.next_cursor)
        return asdict(updates)

    @app.post("/messages/text")
    def send_text(payload: TextMessageRequest) -> dict[str, str]:
        client_id = client.send_text(
            to_user_id=payload.to_user_id,
            text=payload.text,
            context_token=payload.context_token,
            client_id=payload.client_id,
        )
        return {"client_id": client_id}

    @app.post("/messages/image/upload")
    def upload_and_send_image(
        to_user_id: str = Form(...),
        context_token: str = Form(...),
        client_id: str | None = Form(default=None),
        file: UploadFile = File(...),
    ) -> dict:
        with _temporary_upload_path(file) as temp_path:
            return _upload_and_send(
                upload=lambda: client.upload_image(file_path=temp_path, to_user_id=to_user_id),
                send=lambda uploaded: client.send_image(
                    to_user_id=to_user_id,
                    uploaded=uploaded,
                    context_token=context_token,
                    client_id=client_id,
                ),
            )

    @app.post("/messages/file/upload")
    def upload_and_send_file(
        to_user_id: str = Form(...),
        context_token: str = Form(...),
        client_id: str | None = Form(default=None),
        file: UploadFile = File(...),
    ) -> dict:
        with _temporary_upload_path(file) as temp_path:
            return _upload_and_send(
                upload=lambda: client.upload_file(file_path=temp_path, to_user_id=to_user_id),
                send=lambda uploaded: client.send_file(
                    to_user_id=to_user_id,
                    file_name=file.filename or temp_path.name,
                    uploaded=uploaded,
                    context_token=context_token,
                    client_id=client_id,
                ),
            )

    @app.post("/messages/video/upload")
    def upload_and_send_video(
        to_user_id: str = Form(...),
        context_token: str = Form(...),
        client_id: str | None = Form(default=None),
        file: UploadFile = File(...),
        thumb_file: UploadFile | None = File(default=None),
    ) -> dict:
        with _temporary_upload_path(file) as temp_path, _temporary_upload_path(thumb_file) as thumb_temp_path:
            return _upload_and_send(
                upload=lambda: client.upload_video(
                    file_path=temp_path,
                    to_user_id=to_user_id,
                    thumb_path=thumb_temp_path,
                ),
                send=lambda uploaded: client.send_video(
                    to_user_id=to_user_id,
                    uploaded=uploaded,
                    context_token=context_token,
                    client_id=client_id,
                ),
            )

    @app.post("/messages/voice/upload")
    def upload_and_send_voice(
        to_user_id: str = Form(...),
        context_token: str = Form(...),
        client_id: str | None = Form(default=None),
        encode_type: int | None = Form(default=None),
        bits_per_sample: int | None = Form(default=None),
        sample_rate: int | None = Form(default=None),
        playtime: int | None = Form(default=None),
        text: str | None = Form(default=None),
        file: UploadFile = File(...),
    ) -> dict:
        with _temporary_upload_path(file) as temp_path:
            return _upload_and_send(
                upload=lambda: client.upload_voice(file_path=temp_path, to_user_id=to_user_id),
                send=lambda uploaded: client.send_voice(
                    to_user_id=to_user_id,
                    uploaded=uploaded,
                    context_token=context_token,
                    client_id=client_id,
                    encode_type=encode_type,
                    bits_per_sample=bits_per_sample,
                    sample_rate=sample_rate,
                    playtime=playtime,
                    text=text,
                ),
            )

    return app
