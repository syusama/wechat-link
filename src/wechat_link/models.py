from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class InboundMediaRef:
    encrypt_query_param: str
    aes_key: str | None = None
    encrypt_type: int | None = None
    full_url: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "InboundMediaRef | None":
        if not isinstance(payload, dict):
            return None

        encrypt_query_param = str(payload.get("encrypt_query_param", "")).strip()
        if not encrypt_query_param:
            return None

        aes_key = payload.get("aes_key")
        return cls(
            encrypt_query_param=encrypt_query_param,
            aes_key=str(aes_key) if aes_key is not None else None,
            encrypt_type=_as_int(payload.get("encrypt_type")),
            full_url=str(payload.get("full_url")) if payload.get("full_url") else None,
        )


@dataclass(frozen=True)
class InboundMessageItem:
    kind: str
    type: int
    text: str = ""
    media: InboundMediaRef | None = None
    thumb_media: InboundMediaRef | None = None
    file_name: str | None = None
    size: int | None = None
    width: int | None = None
    height: int | None = None
    playtime: int | None = None
    sample_rate: int | None = None
    bits_per_sample: int | None = None
    encode_type: int | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InboundMessageItem":
        item_type = _as_int(payload.get("type")) or 0

        if item_type == 1 and isinstance(payload.get("text_item"), dict):
            text_item = payload["text_item"]
            return cls(
                kind="text",
                type=item_type,
                text=str(text_item.get("text", "")),
            )

        if item_type == 2 and isinstance(payload.get("image_item"), dict):
            image_item = payload["image_item"]
            return cls(
                kind="image",
                type=item_type,
                media=InboundMediaRef.from_dict(image_item.get("media")),
                size=_as_int(image_item.get("mid_size")),
            )

        if item_type == 3 and isinstance(payload.get("voice_item"), dict):
            voice_item = payload["voice_item"]
            return cls(
                kind="voice",
                type=item_type,
                text=str(voice_item.get("text", "")),
                media=InboundMediaRef.from_dict(voice_item.get("media")),
                playtime=_as_int(voice_item.get("playtime")),
                sample_rate=_as_int(voice_item.get("sample_rate")),
                bits_per_sample=_as_int(voice_item.get("bits_per_sample")),
                encode_type=_as_int(voice_item.get("encode_type")),
            )

        if item_type == 4 and isinstance(payload.get("file_item"), dict):
            file_item = payload["file_item"]
            file_name = str(file_item.get("file_name", "")).strip()
            return cls(
                kind="file",
                type=item_type,
                media=InboundMediaRef.from_dict(file_item.get("media")),
                file_name=file_name or None,
                size=_as_int(file_item.get("len")),
            )

        if item_type == 5 and isinstance(payload.get("video_item"), dict):
            video_item = payload["video_item"]
            return cls(
                kind="video",
                type=item_type,
                media=InboundMediaRef.from_dict(video_item.get("media")),
                thumb_media=InboundMediaRef.from_dict(video_item.get("thumb_media")),
                size=_as_int(video_item.get("video_size")),
                width=_as_int(video_item.get("thumb_width")),
                height=_as_int(video_item.get("thumb_height")),
            )

        return cls(kind="unknown", type=item_type)


@dataclass(frozen=True)
class LoginQRCode:
    qrcode: str
    qrcode_img_content: str
    ret: int = 0

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LoginQRCode":
        return cls(
            qrcode=str(payload.get("qrcode", "")),
            qrcode_img_content=str(payload.get("qrcode_img_content", "")),
            ret=int(payload.get("ret", 0)),
        )


@dataclass(frozen=True)
class QRCodeStatus:
    status: str
    bot_token: str | None = None
    baseurl: str | None = None
    ilink_bot_id: str | None = None
    ilink_user_id: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "QRCodeStatus":
        return cls(
            status=str(payload.get("status", "")),
            bot_token=payload.get("bot_token"),
            baseurl=payload.get("baseurl"),
            ilink_bot_id=payload.get("ilink_bot_id"),
            ilink_user_id=payload.get("ilink_user_id"),
        )


@dataclass(frozen=True)
class WeixinMessage:
    seq: int | None = None
    message_id: int | None = None
    from_user_id: str | None = None
    to_user_id: str | None = None
    client_id: str | None = None
    create_time_ms: int | None = None
    update_time_ms: int | None = None
    delete_time_ms: int | None = None
    session_id: str | None = None
    group_id: str | None = None
    message_type: int | None = None
    message_state: int | None = None
    context_token: str | None = None
    item_list: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WeixinMessage":
        item_list = payload.get("item_list", [])
        return cls(
            seq=_as_int(payload.get("seq")),
            message_id=_as_int(payload.get("message_id")),
            from_user_id=payload.get("from_user_id"),
            to_user_id=payload.get("to_user_id"),
            client_id=payload.get("client_id"),
            create_time_ms=_as_int(payload.get("create_time_ms")),
            update_time_ms=_as_int(payload.get("update_time_ms")),
            delete_time_ms=_as_int(payload.get("delete_time_ms")),
            session_id=payload.get("session_id"),
            group_id=payload.get("group_id"),
            message_type=_as_int(payload.get("message_type")),
            message_state=_as_int(payload.get("message_state")),
            context_token=payload.get("context_token"),
            item_list=list(item_list) if isinstance(item_list, list) else [],
        )

    def items(self) -> list[InboundMessageItem]:
        return [
            InboundMessageItem.from_dict(item)
            for item in self.item_list
            if isinstance(item, dict)
        ]

    def media_items(self) -> list[InboundMessageItem]:
        return [item for item in self.items() if item.media is not None]

    def kind(self) -> str:
        items = self.items()
        return items[0].kind if items else "unknown"

    def text(self) -> str:
        for item in self.items():
            if item.kind == "text" and item.text:
                return item.text
            if item.kind == "voice" and item.text:
                return item.text
        return ""


@dataclass(frozen=True)
class UpdatesResponse:
    ret: int
    messages: list[WeixinMessage]
    next_cursor: str | None = None
    longpolling_timeout_ms: int | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UpdatesResponse":
        return cls(
            ret=int(payload.get("ret", 0)),
            messages=[WeixinMessage.from_dict(item) for item in payload.get("msgs", [])],
            next_cursor=payload.get("get_updates_buf"),
            longpolling_timeout_ms=payload.get("longpolling_timeout_ms"),
        )


@dataclass(frozen=True)
class ConfigResponse:
    ret: int
    errmsg: str = ""
    typing_ticket: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ConfigResponse":
        return cls(
            ret=int(payload.get("ret", 0)),
            errmsg=str(payload.get("errmsg", "")),
            typing_ticket=payload.get("typing_ticket"),
        )


@dataclass(frozen=True)
class TypingResponse:
    ret: int
    errmsg: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TypingResponse":
        return cls(
            ret=int(payload.get("ret", 0)),
            errmsg=str(payload.get("errmsg", "")),
        )


@dataclass(frozen=True)
class UploadUrlResponse:
    upload_param: str | None = None
    thumb_upload_param: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UploadUrlResponse":
        return cls(
            upload_param=payload.get("upload_param"),
            thumb_upload_param=payload.get("thumb_upload_param"),
        )


@dataclass(frozen=True)
class UploadedMedia:
    filekey: str
    download_encrypted_query_param: str
    aes_key_hex: str
    file_size: int
    file_size_ciphertext: int
    raw_md5: str | None = None
    thumb_download_encrypted_query_param: str | None = None
    thumb_file_size: int | None = None
    thumb_file_size_ciphertext: int | None = None
    thumb_width: int | None = None
    thumb_height: int | None = None
