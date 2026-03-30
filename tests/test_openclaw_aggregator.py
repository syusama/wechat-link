from __future__ import annotations

from pathlib import Path

from wechat_link.models import WeixinMessage
from wechat_link.openclaw_adapter import OpenClawWeixinAdapter
from wechat_link.openclaw_aggregator import OpenClawInboundAggregator


class FakeAggregatingClient:
    def __init__(self) -> None:
        self.download_calls: list[tuple[str, bool]] = []

    def download_message_item(self, item, *, thumb: bool = False) -> bytes:
        self.download_calls.append((item.kind, thumb))
        payloads = {
            "image": b"image-bytes",
            "video": b"video-bytes",
            "file": b"file-bytes",
            "voice": b"voice-bytes",
        }
        return payloads[item.kind]


def _image_message(*, context_token: str = "ctx-1", create_time_ms: int = 1710000000000) -> WeixinMessage:
    return WeixinMessage.from_dict(
        {
            "from_user_id": "user@im.wechat",
            "to_user_id": "bot@im.bot",
            "context_token": context_token,
            "create_time_ms": create_time_ms,
            "item_list": [
                {
                    "type": 2,
                    "image_item": {
                        "media": {
                            "encrypt_query_param": "image-download-param",
                            "aes_key": "MDEyMzQ1Njc4OWFiY2RlZg==",
                            "encrypt_type": 1,
                        }
                    },
                }
            ],
        }
    )


def _text_message(
    *,
    text: str,
    context_token: str = "ctx-1",
    create_time_ms: int = 1710000005000,
) -> WeixinMessage:
    return WeixinMessage.from_dict(
        {
            "from_user_id": "user@im.wechat",
            "to_user_id": "bot@im.bot",
            "context_token": context_token,
            "create_time_ms": create_time_ms,
            "item_list": [
                {
                    "type": 1,
                    "text_item": {"text": text},
                }
            ],
        }
    )


def test_aggregator_merges_recent_media_with_follow_up_text_within_8_seconds(
    tmp_path: Path,
) -> None:
    adapter = OpenClawWeixinAdapter(
        FakeAggregatingClient(),
        account_id="wx-account-1",
        state_dir=tmp_path / "state",
    )
    aggregator = OpenClawInboundAggregator(adapter, merge_window_seconds=8)

    assert aggregator.ingest(_image_message(), now=100.0) == []

    contexts = aggregator.ingest(
        _text_message(text="what breed is this dog"),
        now=107.5,
    )

    assert len(contexts) == 1
    context = contexts[0]
    assert context.Body == "what breed is this dog"
    assert context.MediaPath is not None
    assert Path(context.MediaPath).exists()
    assert context.MediaPaths == [context.MediaPath]
    assert context.Timestamp == 1710000005000
    assert aggregator.pending_count == 0


def test_aggregator_flushes_media_only_context_after_8_seconds(tmp_path: Path) -> None:
    adapter = OpenClawWeixinAdapter(
        FakeAggregatingClient(),
        account_id="wx-account-1",
        state_dir=tmp_path / "state",
    )
    aggregator = OpenClawInboundAggregator(adapter, merge_window_seconds=8)

    assert aggregator.ingest(_image_message(), now=100.0) == []
    assert aggregator.flush_ready(now=107.9) == []

    contexts = aggregator.flush_ready(now=108.0)

    assert len(contexts) == 1
    context = contexts[0]
    assert context.Body == ""
    assert context.MediaPath is not None
    assert aggregator.pending_count == 0


def test_aggregator_does_not_delay_plain_text_messages_without_pending_media(
    tmp_path: Path,
) -> None:
    adapter = OpenClawWeixinAdapter(
        FakeAggregatingClient(),
        account_id="wx-account-1",
        state_dir=tmp_path / "state",
    )
    aggregator = OpenClawInboundAggregator(adapter, merge_window_seconds=8)

    contexts = aggregator.ingest(
        _text_message(text="plain text"),
        now=100.0,
    )

    assert len(contexts) == 1
    assert contexts[0].Body == "plain text"
    assert contexts[0].MediaPath is None
    assert aggregator.pending_count == 0


def test_aggregator_collects_multiple_recent_media_before_follow_up_text(
    tmp_path: Path,
) -> None:
    adapter = OpenClawWeixinAdapter(
        FakeAggregatingClient(),
        account_id="wx-account-1",
        state_dir=tmp_path / "state",
    )
    aggregator = OpenClawInboundAggregator(adapter, merge_window_seconds=8)

    first = _image_message(create_time_ms=1710000000000)
    second = _image_message(create_time_ms=1710000003000)

    assert aggregator.ingest(first, now=100.0) == []
    assert aggregator.ingest(second, now=104.0) == []

    contexts = aggregator.ingest(
        _text_message(text="compare these two images", create_time_ms=1710000006000),
        now=107.0,
    )

    assert len(contexts) == 1
    context = contexts[0]
    assert context.Body == "compare these two images"
    assert context.MediaPaths is not None
    assert len(context.MediaPaths) == 2
    assert context.MediaTypes == ["image/*", "image/*"]
