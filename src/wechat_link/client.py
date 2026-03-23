from __future__ import annotations

import base64
import json
import sys
from io import BytesIO
from pathlib import Path
from typing import Any, TextIO

import httpx
from PIL import Image, UnidentifiedImageError

from wechat_link.headers import build_wechat_headers
from wechat_link.media import (
    MEDIA_TYPE_FILE,
    MEDIA_TYPE_IMAGE,
    MEDIA_TYPE_VIDEO,
    MEDIA_TYPE_VOICE,
    upload_media_from_path,
    upload_video_with_thumb_from_path,
)
from wechat_link.message_builders import (
    build_file_payload,
    build_image_payload,
    build_text_payload,
    build_video_payload,
    build_voice_payload,
)
from wechat_link.models import (
    ConfigResponse,
    LoginQRCode,
    QRCodeStatus,
    TypingResponse,
    UploadUrlResponse,
    UploadedMedia,
    UpdatesResponse,
)


class Client:
    def __init__(
        self,
        *,
        base_url: str = "https://ilinkai.weixin.qq.com",
        bot_token: str | None = None,
        channel_version: str = "0.1.0",
        timeout: float | httpx.Timeout | None = None,
        cdn_base_url: str = "https://novac2c.cdn.weixin.qq.com/c2c",
        transport: httpx.BaseTransport | None = None,
        cdn_transport: httpx.BaseTransport | None = None,
    ) -> None:
        normalized_base_url = base_url.rstrip("/") + "/"
        self.base_url = normalized_base_url
        self.bot_token = bot_token
        self.channel_version = channel_version
        self.cdn_base_url = cdn_base_url.rstrip("/")
        self._cdn_transport = cdn_transport
        client_timeout = timeout or httpx.Timeout(
            connect=15.0,
            read=45.0,
            write=15.0,
            pool=15.0,
        )
        self._client = httpx.Client(
            base_url=normalized_base_url,
            timeout=client_timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def get_bot_qrcode(self, *, bot_type: int = 3) -> LoginQRCode:
        response = self._client.get(
            "ilink/bot/get_bot_qrcode",
            params={"bot_type": str(bot_type)},
        )
        response.raise_for_status()
        return LoginQRCode.from_dict(response.json())

    def get_qrcode_status(self, qrcode: str) -> QRCodeStatus:
        response = self._client.get(
            "ilink/bot/get_qrcode_status",
            params={"qrcode": qrcode},
            headers={"iLink-App-ClientVersion": "1"},
        )
        response.raise_for_status()
        return QRCodeStatus.from_dict(response.json())

    def save_qrcode_image(
        self,
        qrcode_img_content: str,
        *,
        output_path: str | Path,
    ) -> Path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        source_type, payload = self._resolve_qrcode_source(qrcode_img_content)
        image_bytes = payload if source_type == "image" else self._build_qrcode_png(payload)
        destination.write_bytes(image_bytes)
        return destination

    def render_qrcode_terminal(
        self,
        qrcode_img_content: str,
        *,
        black: str = "██",
        white: str = "  ",
        padding: int = 1,
    ) -> str:
        if padding < 0:
            raise ValueError("padding must be >= 0")

        source_type, payload = self._resolve_qrcode_source(qrcode_img_content)
        if source_type == "text":
            return self._render_qrcode_from_text(
                payload,
                black=black,
                white=white,
                padding=padding,
            )

        image = Image.open(BytesIO(payload)).convert("L")
        binary = image.point(lambda value: 0 if value < 128 else 255, mode="1")

        rows: list[str] = []
        empty_row = white * (binary.width + padding * 2)

        for _ in range(padding):
            rows.append(empty_row)

        for y in range(binary.height):
            cells = [white] * padding
            for x in range(binary.width):
                cells.append(black if binary.getpixel((x, y)) == 0 else white)
            cells.extend([white] * padding)
            rows.append("".join(cells))

        for _ in range(padding):
            rows.append(empty_row)

        return "\n".join(rows)

    def print_qrcode_terminal(
        self,
        qrcode_img_content: str,
        *,
        stream: TextIO | None = None,
        black: str = "██",
        white: str = "  ",
        padding: int = 1,
    ) -> str:
        rendered = self.render_qrcode_terminal(
            qrcode_img_content,
            black=black,
            white=white,
            padding=padding,
        )
        output = stream or sys.stdout
        output.write(rendered + "\n")
        return rendered

    def get_updates(self, *, cursor: str = "") -> UpdatesResponse:
        payload = {
            "get_updates_buf": cursor,
            "base_info": {"channel_version": self.channel_version},
        }
        response = self._post_json("ilink/bot/getupdates", payload)
        return UpdatesResponse.from_dict(response)

    def get_config(
        self,
        *,
        ilink_user_id: str,
        context_token: str | None = None,
    ) -> ConfigResponse:
        payload = {
            "ilink_user_id": ilink_user_id,
            "context_token": context_token,
            "base_info": {"channel_version": self.channel_version},
        }
        response = self._post_json("ilink/bot/getconfig", payload)
        return ConfigResponse.from_dict(response)

    def send_typing(
        self,
        *,
        ilink_user_id: str,
        typing_ticket: str,
        status: int = 1,
    ) -> TypingResponse:
        payload = {
            "ilink_user_id": ilink_user_id,
            "typing_ticket": typing_ticket,
            "status": status,
            "base_info": {"channel_version": self.channel_version},
        }
        response = self._post_json("ilink/bot/sendtyping", payload)
        return TypingResponse.from_dict(response)

    def send_text(
        self,
        *,
        to_user_id: str,
        text: str,
        context_token: str,
        client_id: str | None = None,
    ) -> str:
        outbound_client_id, payload = build_text_payload(
            channel_version=self.channel_version,
            to_user_id=to_user_id,
            text=text,
            context_token=context_token,
            client_id=client_id,
        )
        self._post_json("ilink/bot/sendmessage", payload)
        return outbound_client_id

    def get_upload_url(
        self,
        *,
        filekey: str,
        media_type: int,
        to_user_id: str,
        rawsize: int,
        rawfilemd5: str,
        filesize: int,
        thumb_rawsize: int | None = None,
        thumb_rawfilemd5: str | None = None,
        thumb_filesize: int | None = None,
        no_need_thumb: bool = True,
        aeskey: str | None = None,
    ) -> UploadUrlResponse:
        payload = {
            "filekey": filekey,
            "media_type": media_type,
            "to_user_id": to_user_id,
            "rawsize": rawsize,
            "rawfilemd5": rawfilemd5,
            "filesize": filesize,
            "thumb_rawsize": thumb_rawsize,
            "thumb_rawfilemd5": thumb_rawfilemd5,
            "thumb_filesize": thumb_filesize,
            "no_need_thumb": no_need_thumb,
            "aeskey": aeskey,
            "base_info": {"channel_version": self.channel_version},
        }
        response = self._post_json("ilink/bot/getuploadurl", payload)
        return UploadUrlResponse.from_dict(response)

    def upload_image(self, *, file_path: str | Path, to_user_id: str) -> UploadedMedia:
        return upload_media_from_path(
            file_path=file_path,
            to_user_id=to_user_id,
            media_type=MEDIA_TYPE_IMAGE,
            cdn_base_url=self.cdn_base_url,
            request_upload_url=self.get_upload_url,
            cdn_transport=self._cdn_transport,
        )

    def upload_file(self, *, file_path: str | Path, to_user_id: str) -> UploadedMedia:
        return upload_media_from_path(
            file_path=file_path,
            to_user_id=to_user_id,
            media_type=MEDIA_TYPE_FILE,
            cdn_base_url=self.cdn_base_url,
            request_upload_url=self.get_upload_url,
            cdn_transport=self._cdn_transport,
        )

    def upload_video(
        self,
        *,
        file_path: str | Path,
        to_user_id: str,
        thumb_path: str | Path | None = None,
    ) -> UploadedMedia:
        return upload_video_with_thumb_from_path(
            file_path=file_path,
            to_user_id=to_user_id,
            thumb_path=thumb_path,
            cdn_base_url=self.cdn_base_url,
            request_upload_url=self.get_upload_url,
            cdn_transport=self._cdn_transport,
        )

    def upload_voice(self, *, file_path: str | Path, to_user_id: str) -> UploadedMedia:
        return upload_media_from_path(
            file_path=file_path,
            to_user_id=to_user_id,
            media_type=MEDIA_TYPE_VOICE,
            cdn_base_url=self.cdn_base_url,
            request_upload_url=self.get_upload_url,
            cdn_transport=self._cdn_transport,
        )

    def send_image(
        self,
        *,
        to_user_id: str,
        uploaded: UploadedMedia,
        context_token: str,
        client_id: str | None = None,
    ) -> str:
        outbound_client_id, payload = build_image_payload(
            channel_version=self.channel_version,
            to_user_id=to_user_id,
            uploaded=uploaded,
            context_token=context_token,
            client_id=client_id,
        )
        self._post_json("ilink/bot/sendmessage", payload)
        return outbound_client_id

    def send_file(
        self,
        *,
        to_user_id: str,
        file_name: str,
        uploaded: UploadedMedia,
        context_token: str,
        client_id: str | None = None,
    ) -> str:
        outbound_client_id, payload = build_file_payload(
            channel_version=self.channel_version,
            to_user_id=to_user_id,
            file_name=file_name,
            uploaded=uploaded,
            context_token=context_token,
            client_id=client_id,
        )
        self._post_json("ilink/bot/sendmessage", payload)
        return outbound_client_id

    def send_video(
        self,
        *,
        to_user_id: str,
        uploaded: UploadedMedia,
        context_token: str,
        client_id: str | None = None,
    ) -> str:
        outbound_client_id, payload = build_video_payload(
            channel_version=self.channel_version,
            to_user_id=to_user_id,
            uploaded=uploaded,
            context_token=context_token,
            client_id=client_id,
        )
        self._post_json("ilink/bot/sendmessage", payload)
        return outbound_client_id

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
        outbound_client_id, payload = build_voice_payload(
            channel_version=self.channel_version,
            to_user_id=to_user_id,
            uploaded=uploaded,
            context_token=context_token,
            client_id=client_id,
            encode_type=encode_type,
            bits_per_sample=bits_per_sample,
            sample_rate=sample_rate,
            playtime=playtime,
            text=text,
        )
        self._post_json("ilink/bot/sendmessage", payload)
        return outbound_client_id

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = build_wechat_headers(body=body, bot_token=self.bot_token)
        response = self._client.post(path, content=body, headers=headers)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data
        raise TypeError("API response must be a JSON object")

    def _resolve_qrcode_source(self, qrcode_img_content: str) -> tuple[str, bytes | str]:
        if qrcode_img_content.startswith(("http://", "https://")):
            response = self._client.get(qrcode_img_content)
            response.raise_for_status()
            if self._is_image_content(
                response.content,
                response.headers.get("Content-Type", ""),
            ):
                return "image", response.content
            return "text", qrcode_img_content

        payload = qrcode_img_content
        if "," in qrcode_img_content and qrcode_img_content.startswith("data:"):
            payload = qrcode_img_content.split(",", 1)[1]

        return "image", base64.b64decode(payload)

    def _is_image_content(self, content: bytes, content_type: str) -> bool:
        if content_type.lower().startswith("image/"):
            return True

        try:
            with Image.open(BytesIO(content)) as image:
                image.verify()
            return True
        except UnidentifiedImageError:
            return False

    def _build_qrcode_png(self, payload: str) -> bytes:
        import qrcode

        qr = qrcode.QRCode(border=4, box_size=10)
        qr.add_data(payload)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def _render_qrcode_from_text(
        self,
        payload: str,
        *,
        black: str,
        white: str,
        padding: int,
    ) -> str:
        import qrcode

        qr = qrcode.QRCode(border=padding)
        qr.add_data(payload)
        qr.make(fit=True)
        matrix = qr.get_matrix()
        return "\n".join(
            "".join(black if cell else white for cell in row)
            for row in matrix
        )
