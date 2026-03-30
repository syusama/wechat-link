from __future__ import annotations

from dataclasses import dataclass, field
import secrets
import time
from pathlib import Path

from wechat_link.models import WeixinMessage
from wechat_link.openclaw_adapter import OpenClawInboundContext, OpenClawWeixinAdapter


@dataclass
class _PendingInboundBatch:
    contexts: list[OpenClawInboundContext] = field(default_factory=list)
    first_seen_at: float = 0.0
    last_seen_at: float = 0.0


class OpenClawInboundAggregator:
    def __init__(
        self,
        adapter: OpenClawWeixinAdapter,
        *,
        merge_window_seconds: float = 8.0,
    ) -> None:
        if merge_window_seconds <= 0:
            raise ValueError("merge_window_seconds must be > 0")

        self.adapter = adapter
        self.merge_window_seconds = float(merge_window_seconds)
        self._pending: dict[str, _PendingInboundBatch] = {}

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def ingest(
        self,
        message: WeixinMessage,
        *,
        now: float | None = None,
        media_dir: str | Path | None = None,
    ) -> list[OpenClawInboundContext]:
        current_now = time.monotonic() if now is None else now
        emitted = self.flush_ready(now=current_now)

        context = self.adapter.build_inbound_context(message, media_dir=media_dir)
        key = _conversation_key(context)
        pending = self._pending.get(key)
        has_media = _context_has_media(context)
        has_user_text = bool(message.text().strip())

        if not has_media:
            if pending is None:
                emitted.append(context)
                return emitted

            pending.contexts.append(context)
            pending.last_seen_at = current_now
            emitted.append(self._emit_pending(key))
            return emitted

        if pending is None:
            self._pending[key] = _PendingInboundBatch(
                contexts=[context],
                first_seen_at=current_now,
                last_seen_at=current_now,
            )
        else:
            pending.contexts.append(context)
            pending.last_seen_at = current_now

        if has_user_text:
            emitted.append(self._emit_pending(key))

        return emitted

    def flush_ready(self, *, now: float | None = None) -> list[OpenClawInboundContext]:
        current_now = time.monotonic() if now is None else now
        ready_keys = [
            key
            for key, pending in self._pending.items()
            if current_now - pending.last_seen_at >= self.merge_window_seconds
        ]
        return [self._emit_pending(key) for key in ready_keys]

    def flush_all(self) -> list[OpenClawInboundContext]:
        return [self._emit_pending(key) for key in list(self._pending)]

    def _emit_pending(self, key: str) -> OpenClawInboundContext:
        pending = self._pending.pop(key)
        return _merge_contexts(pending.contexts)


def _conversation_key(context: OpenClawInboundContext) -> str:
    return "\x1f".join(
        (
            context.AccountId,
            context.From,
            context.context_token or "",
        )
    )


def _context_has_media(context: OpenClawInboundContext) -> bool:
    return bool(context.MediaPath or context.MediaPaths)


def _merge_contexts(contexts: list[OpenClawInboundContext]) -> OpenClawInboundContext:
    if not contexts:
        raise ValueError("contexts must not be empty")

    latest = contexts[-1]
    body = "\n".join(_dedupe_preserve_order(_normalized_bodies(contexts)))
    media_pairs = _collect_media_pairs(contexts)
    media_paths = [path for path, _ in media_pairs] or None
    media_types = [media_type for _, media_type in media_pairs] or None
    primary_media_path = media_paths[0] if media_paths else None
    primary_media_type = media_types[0] if media_types else None
    archive_context = next((context for context in contexts if context.ArchivePath), None)

    return OpenClawInboundContext(
        Body=body,
        From=_latest_string(contexts, "From"),
        To=_latest_string(contexts, "To"),
        AccountId=latest.AccountId,
        OriginatingChannel=latest.OriginatingChannel,
        OriginatingTo=_latest_string(contexts, "OriginatingTo"),
        MessageSid=_generate_aggregate_message_sid(),
        Timestamp=_latest_value(contexts, "Timestamp"),
        Provider=latest.Provider,
        ChatType=latest.ChatType,
        SessionKey=_latest_string(contexts, "SessionKey"),
        context_token=_latest_string(contexts, "context_token"),
        MediaUrl=primary_media_path,
        MediaPath=primary_media_path,
        MediaType=primary_media_type,
        MediaUrls=media_paths,
        MediaPaths=media_paths,
        MediaTypes=media_types,
        MediaDir=_shared_media_dir(contexts),
        ArchivePath=archive_context.ArchivePath if archive_context is not None else None,
        ArchiveExtracted=archive_context.ArchiveExtracted if archive_context is not None else None,
        ArchiveEntries=archive_context.ArchiveEntries if archive_context is not None else None,
        CommandBody=_latest_string(contexts, "CommandBody"),
        CommandAuthorized=_latest_value(contexts, "CommandAuthorized"),
    )


def _collect_media_pairs(contexts: list[OpenClawInboundContext]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    seen_paths: set[str] = set()

    for context in contexts:
        paths = context.MediaPaths or ([context.MediaPath] if context.MediaPath else [])
        types = context.MediaTypes or ([context.MediaType] if context.MediaType else [])

        for index, path in enumerate(paths):
            if not path or path in seen_paths:
                continue

            media_type = (
                types[index]
                if index < len(types) and types[index]
                else context.MediaType or "application/octet-stream"
            )
            seen_paths.add(path)
            pairs.append((path, media_type))

    return pairs


def _normalized_bodies(contexts: list[OpenClawInboundContext]) -> list[str]:
    return [context.Body.strip() for context in contexts if context.Body and context.Body.strip()]


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []

    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)

    return deduped


def _shared_media_dir(contexts: list[OpenClawInboundContext]) -> str | None:
    media_dirs = [context.MediaDir for context in contexts if context.MediaDir]
    if not media_dirs:
        return None
    if len(set(media_dirs)) == 1:
        return media_dirs[0]
    return None


def _latest_string(contexts: list[OpenClawInboundContext], field_name: str) -> str | None:
    for context in reversed(contexts):
        value = getattr(context, field_name)
        if isinstance(value, str) and value:
            return value
    return None


def _latest_value(contexts: list[OpenClawInboundContext], field_name: str):
    for context in reversed(contexts):
        value = getattr(context, field_name)
        if value is not None:
            return value
    return None


def _generate_aggregate_message_sid() -> str:
    return f"openclaw-weixin-{secrets.token_hex(8)}"
