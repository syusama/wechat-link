from __future__ import annotations

from dataclasses import asdict, dataclass
import shutil
import mimetypes
from pathlib import Path
from pathlib import PurePosixPath
import re
import secrets
import tarfile
from typing import Any
import zipfile

from wechat_link.models import InboundMessageItem, WeixinMessage
from wechat_link.store import FileContextTokenStore


_EXTENSION_TO_MIME = {
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".zip": "application/zip",
    ".tar": "application/x-tar",
    ".gz": "application/gzip",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
    ".silk": "audio/silk",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


@dataclass(frozen=True)
class OpenClawInboundContext:
    Body: str
    From: str
    To: str
    AccountId: str
    OriginatingChannel: str = "openclaw-weixin"
    OriginatingTo: str = ""
    MessageSid: str = ""
    Timestamp: int | None = None
    Provider: str = "openclaw-weixin"
    ChatType: str = "direct"
    SessionKey: str | None = None
    context_token: str | None = None
    MediaUrl: str | None = None
    MediaPath: str | None = None
    MediaType: str | None = None
    MediaUrls: list[str] | None = None
    MediaPaths: list[str] | None = None
    MediaTypes: list[str] | None = None
    MediaDir: str | None = None
    ArchivePath: str | None = None
    ArchiveExtracted: bool | None = None
    ArchiveEntries: list[str] | None = None
    CommandBody: str | None = None
    CommandAuthorized: bool | None = None

    def to_dict(self, *, omit_none: bool = True) -> dict[str, Any]:
        payload = asdict(self)
        if not omit_none:
            return payload
        return {key: value for key, value in payload.items() if value is not None}


@dataclass(frozen=True)
class OpenClawOutboundContext:
    to_user_id: str
    context_token: str | None = None


@dataclass(frozen=True)
class _ResolvedInboundMedia:
    primary_path: str
    primary_type: str
    media_paths: list[str]
    media_types: list[str]
    media_dir: str
    archive_path: str | None = None
    archive_extracted: bool = False
    archive_entries: list[str] | None = None


def markdown_to_plain_text(text: str) -> str:
    result = text
    result = re.sub(
        r"```[^\n]*\n?([\s\S]*?)```",
        lambda match: match.group(1).strip(),
        result,
    )
    result = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", result)
    result = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", result)
    result = re.sub(r"^\|[\s:|-]+\|$", "", result, flags=re.MULTILINE)
    result = re.sub(
        r"^\|(.+)\|$",
        lambda match: "  ".join(cell.strip() for cell in match.group(1).split("|")),
        result,
        flags=re.MULTILINE,
    )
    result = re.sub(r"`([^`]*)`", r"\1", result)
    result = re.sub(r"^\s{0,3}#{1,6}\s*", "", result, flags=re.MULTILINE)
    result = re.sub(r"^\s{0,3}>\s?", "", result, flags=re.MULTILINE)
    result = re.sub(r"^\s*[-*+]\s+", "", result, flags=re.MULTILINE)
    for marker in ("**", "__", "~~", "*", "_"):
        result = result.replace(marker, "")
    result = re.sub(r"[ \t]+\n", "\n", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


class OpenClawWeixinAdapter:
    def __init__(
        self,
        client,
        *,
        account_id: str,
        state_dir: str | Path = ".state",
        inbound_media_dir: str | Path | None = None,
        context_token_store: FileContextTokenStore | None = None,
    ) -> None:
        self.client = client
        self.account_id = account_id
        self.state_dir = Path(state_dir)
        self.inbound_media_dir = (
            Path(inbound_media_dir)
            if inbound_media_dir is not None
            else self.state_dir / "openclaw-weixin" / "inbound-media"
        )
        self.context_token_store = context_token_store or FileContextTokenStore(self.state_dir)

    def build_inbound_context(
        self,
        message: WeixinMessage,
        *,
        media_dir: str | Path | None = None,
    ) -> OpenClawInboundContext:
        from_user_id = message.from_user_id or ""
        if message.context_token and from_user_id:
            self.context_token_store.save(
                self.account_id,
                from_user_id,
                message.context_token,
            )

        body = _body_from_item_list(message.item_list)
        media_item = _select_media_item(message.item_list)
        media_path: str | None = None
        media_type: str | None = None
        media_paths: list[str] | None = None
        media_types: list[str] | None = None
        media_dir_value: str | None = None
        archive_path: str | None = None
        archive_extracted: bool | None = None
        archive_entries: list[str] | None = None

        if media_item is not None:
            saved_path = self._save_inbound_media(
                message=message,
                item=media_item,
                media_dir=Path(media_dir) if media_dir is not None else self.inbound_media_dir,
            )
            resolved_media = self._resolve_inbound_media(
                item=media_item,
                saved_path=saved_path,
            )
            media_path = resolved_media.primary_path
            media_type = resolved_media.primary_type
            media_paths = resolved_media.media_paths
            media_types = resolved_media.media_types
            media_dir_value = resolved_media.media_dir
            archive_path = resolved_media.archive_path
            archive_extracted = resolved_media.archive_extracted
            archive_entries = resolved_media.archive_entries
            if archive_extracted and archive_entries:
                body = _append_archive_summary(
                    body=body,
                    archive_name=media_item.file_name or Path(archive_path or saved_path).name,
                    archive_entries=archive_entries,
                )

        return OpenClawInboundContext(
            Body=body,
            From=from_user_id,
            To=from_user_id,
            AccountId=self.account_id,
            OriginatingTo=from_user_id,
            MessageSid=_generate_message_sid(),
            Timestamp=message.create_time_ms,
            context_token=message.context_token,
            MediaUrl=media_path,
            MediaPath=media_path,
            MediaType=media_type,
            MediaUrls=media_paths,
            MediaPaths=media_paths,
            MediaTypes=media_types,
            MediaDir=media_dir_value,
            ArchivePath=archive_path,
            ArchiveExtracted=archive_extracted,
            ArchiveEntries=archive_entries,
        )

    def build_outbound_context(
        self,
        *,
        to_user_id: str,
        context_token: str | None = None,
    ) -> OpenClawOutboundContext:
        return OpenClawOutboundContext(
            to_user_id=to_user_id,
            context_token=context_token,
        )

    def send_reply_from_context(
        self,
        context: OpenClawInboundContext | OpenClawOutboundContext,
        *,
        text: str = "",
        media_path: str | Path | None = None,
        client_id: str | None = None,
        thumb_path: str | Path | None = None,
    ) -> str:
        if isinstance(context, OpenClawInboundContext):
            to_user_id = context.To or context.From
            context_token = context.context_token
        else:
            to_user_id = context.to_user_id
            context_token = context.context_token

        return self.send_reply(
            to_user_id=to_user_id,
            text=text,
            media_path=media_path,
            context_token=context_token,
            client_id=client_id,
            thumb_path=thumb_path,
        )

    def send_reply(
        self,
        *,
        to_user_id: str,
        text: str = "",
        media_path: str | Path | None = None,
        context_token: str | None = None,
        client_id: str | None = None,
        thumb_path: str | Path | None = None,
    ) -> str:
        resolved_context_token = context_token or self.context_token_store.load(
            self.account_id,
            to_user_id,
        )
        if not resolved_context_token:
            raise ValueError("context_token is required")

        plain_text = markdown_to_plain_text(text).strip()
        last_client_id = ""
        # OpenClaw sends caption text and media as separate downstream messages.
        text_client_id = client_id if media_path is None else None

        if plain_text:
            last_client_id = self.client.send_text(
                to_user_id=to_user_id,
                text=plain_text,
                context_token=resolved_context_token,
                client_id=text_client_id,
            )

        if media_path is None:
            if last_client_id:
                return last_client_id
            raise ValueError("text or media_path is required")

        path = Path(media_path)
        mime_type = _mime_from_filename(path.name)

        if mime_type.startswith("video/"):
            uploaded = self.client.upload_video(
                file_path=path,
                to_user_id=to_user_id,
                thumb_path=thumb_path,
            )
            return self.client.send_video(
                to_user_id=to_user_id,
                uploaded=uploaded,
                context_token=resolved_context_token,
                client_id=client_id,
            )

        if mime_type.startswith("image/"):
            uploaded = self.client.upload_image(
                file_path=path,
                to_user_id=to_user_id,
            )
            return self.client.send_image(
                to_user_id=to_user_id,
                uploaded=uploaded,
                context_token=resolved_context_token,
                client_id=client_id,
            )

        if mime_type.startswith("audio/"):
            uploaded = self.client.upload_voice(
                file_path=path,
                to_user_id=to_user_id,
            )
            return self.client.send_voice(
                to_user_id=to_user_id,
                uploaded=uploaded,
                context_token=resolved_context_token,
                client_id=client_id,
            )

        uploaded = self.client.upload_file(
            file_path=path,
            to_user_id=to_user_id,
        )
        return self.client.send_file(
            to_user_id=to_user_id,
            file_name=path.name,
            uploaded=uploaded,
            context_token=resolved_context_token,
            client_id=client_id,
        )

    def _save_inbound_media(
        self,
        *,
        message: WeixinMessage,
        item: InboundMessageItem,
        media_dir: Path,
    ) -> Path:
        media_dir.mkdir(parents=True, exist_ok=True)
        suffix = _suffix_for_item(item)
        message_key = str(message.message_id) if message.message_id is not None else "message"
        token = secrets.token_hex(4)
        if item.file_name:
            base_name = Path(item.file_name).name
            file_name = f"{message_key}-{token}-{base_name}"
        else:
            file_name = f"{message_key}-{item.kind}-{token}{suffix}"

        output_path = media_dir / file_name
        output_path.write_bytes(self.client.download_message_item(item))
        return output_path

    def _resolve_inbound_media(
        self,
        *,
        item: InboundMessageItem,
        saved_path: Path,
    ) -> _ResolvedInboundMedia:
        default_type = _media_type_for_item(item)
        default_path = str(saved_path)

        if item.kind == "file" and item.file_name:
            extracted = self._try_extract_archive(
                saved_path=saved_path,
                original_name=item.file_name,
            )
            if extracted is not None:
                return extracted

        return _ResolvedInboundMedia(
            primary_path=default_path,
            primary_type=default_type,
            media_paths=[default_path],
            media_types=[default_type],
            media_dir=str(saved_path.parent),
        )

    def _try_extract_archive(
        self,
        *,
        saved_path: Path,
        original_name: str,
    ) -> _ResolvedInboundMedia | None:
        archive_entries: list[str] = []
        archive_stem = _archive_stem(original_name)
        extraction_dir = saved_path.parent / f"{archive_stem}-extracted-{secrets.token_hex(4)}"

        if zipfile.is_zipfile(saved_path):
            archive_entries = _extract_zip_archive(saved_path, extraction_dir)
        elif tarfile.is_tarfile(saved_path):
            archive_entries = _extract_tar_archive(saved_path, extraction_dir)
        else:
            return None

        extracted_files = sorted(path for path in extraction_dir.rglob("*") if path.is_file())
        if not extracted_files:
            shutil.rmtree(extraction_dir, ignore_errors=True)
            return None

        media_paths = [str(path) for path in extracted_files]
        media_types = [_mime_from_filename(path.name) for path in extracted_files]
        return _ResolvedInboundMedia(
            primary_path=media_paths[0],
            primary_type=media_types[0],
            media_paths=media_paths,
            media_types=media_types,
            media_dir=str(extraction_dir),
            archive_path=str(saved_path),
            archive_extracted=True,
            archive_entries=archive_entries,
        )


def _generate_message_sid() -> str:
    return f"openclaw-weixin-{secrets.token_hex(8)}"


def _mime_from_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in _EXTENSION_TO_MIME:
        return _EXTENSION_TO_MIME[suffix]
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def _suffix_for_item(item: InboundMessageItem) -> str:
    if item.kind == "image":
        return ".jpg"
    if item.kind == "video":
        return ".mp4"
    if item.kind == "voice":
        return ".silk"
    if item.file_name:
        return Path(item.file_name).suffix or ".bin"
    return ".bin"


def _media_type_for_item(item: InboundMessageItem) -> str:
    if item.kind == "image":
        return "image/*"
    if item.kind == "video":
        return "video/mp4"
    if item.kind == "voice":
        return "audio/silk"
    if item.file_name:
        return _mime_from_filename(item.file_name)
    return "application/octet-stream"


def _append_archive_summary(
    *,
    body: str,
    archive_name: str,
    archive_entries: list[str],
) -> str:
    summary_lines = [f"Archive extracted: {archive_name}", *[f"- {entry}" for entry in archive_entries]]
    summary = "\n".join(summary_lines)
    if body:
        return f"{body}\n\n{summary}"
    return summary


def _archive_stem(file_name: str) -> str:
    lower_name = file_name.lower()
    for suffix in (".tar.gz", ".tar.bz2", ".tar.xz"):
        if lower_name.endswith(suffix):
            return file_name[: -len(suffix)]
    return Path(file_name).stem


def _extract_zip_archive(source: Path, target_dir: Path) -> list[str]:
    target_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[str] = []
    root = target_dir.resolve()

    with zipfile.ZipFile(source) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            relative_name = _normalize_archive_member_name(info.filename)
            if relative_name is None:
                continue
            destination = _safe_archive_destination(root, relative_name)
            if destination is None:
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source_file, destination.open("wb") as destination_file:
                shutil.copyfileobj(source_file, destination_file)
            extracted.append(relative_name)

    return extracted


def _extract_tar_archive(source: Path, target_dir: Path) -> list[str]:
    target_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[str] = []
    root = target_dir.resolve()

    with tarfile.open(source, "r:*") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            relative_name = _normalize_archive_member_name(member.name)
            if relative_name is None:
                continue
            destination = _safe_archive_destination(root, relative_name)
            if destination is None:
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            extracted_file = archive.extractfile(member)
            if extracted_file is None:
                continue
            with extracted_file, destination.open("wb") as destination_file:
                shutil.copyfileobj(extracted_file, destination_file)
            extracted.append(relative_name)

    return extracted


def _normalize_archive_member_name(name: str) -> str | None:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute():
        return None

    cleaned_parts: list[str] = []
    for part in path.parts:
        if part in ("", "."):
            continue
        if part == "..":
            return None
        cleaned_parts.append(part)

    if not cleaned_parts:
        return None
    return "/".join(cleaned_parts)


def _safe_archive_destination(root: Path, relative_name: str) -> Path | None:
    destination = (root / relative_name).resolve()
    try:
        destination.relative_to(root)
    except ValueError:
        return None
    return destination


def _body_from_item_list(item_list: list[dict[str, Any]]) -> str:
    for raw_item in item_list:
        if not isinstance(raw_item, dict):
            continue

        item = InboundMessageItem.from_dict(raw_item)
        if item.kind == "text" and item.text:
            ref_msg = raw_item.get("ref_msg")
            if not isinstance(ref_msg, dict):
                return item.text

            ref_item_raw = ref_msg.get("message_item")
            if isinstance(ref_item_raw, dict):
                ref_item = InboundMessageItem.from_dict(ref_item_raw)
                if ref_item.media is not None:
                    return item.text
            else:
                ref_item = None

            parts: list[str] = []
            title = ref_msg.get("title")
            if title:
                parts.append(str(title))
            if ref_item is not None:
                ref_body = _body_from_item_list([ref_item_raw])
                if ref_body:
                    parts.append(ref_body)

            if not parts:
                return item.text
            return f"[\u5f15\u7528: {' | '.join(parts)}]\n{item.text}"

        if item.kind == "voice" and item.text:
            return item.text

    return ""


def _select_media_item(item_list: list[dict[str, Any]]) -> InboundMessageItem | None:
    for kind in ("image", "video", "file", "voice"):
        for raw_item in item_list:
            if not isinstance(raw_item, dict):
                continue
            item = InboundMessageItem.from_dict(raw_item)
            if item.kind != kind or item.media is None:
                continue
            if item.kind == "voice" and item.text:
                continue
            return item

    for raw_item in item_list:
        if not isinstance(raw_item, dict):
            continue
        item = InboundMessageItem.from_dict(raw_item)
        if item.kind != "text":
            continue
        ref_msg = raw_item.get("ref_msg")
        if not isinstance(ref_msg, dict):
            continue
        ref_item_raw = ref_msg.get("message_item")
        if not isinstance(ref_item_raw, dict):
            continue
        ref_item = InboundMessageItem.from_dict(ref_item_raw)
        if ref_item.media is not None:
            return ref_item

    return None
