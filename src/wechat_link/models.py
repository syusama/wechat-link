from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    from_user_id: str | None = None
    to_user_id: str | None = None
    context_token: str | None = None
    item_list: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WeixinMessage":
        return cls(
            from_user_id=payload.get("from_user_id"),
            to_user_id=payload.get("to_user_id"),
            context_token=payload.get("context_token"),
            item_list=list(payload.get("item_list", [])),
        )

    def text(self) -> str:
        for item in self.item_list:
            if item.get("type") == 1 and isinstance(item.get("text_item"), dict):
                return str(item["text_item"].get("text", ""))
            if item.get("type") == 3 and isinstance(item.get("voice_item"), dict):
                return str(item["voice_item"].get("text", ""))
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
