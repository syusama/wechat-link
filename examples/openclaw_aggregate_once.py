from __future__ import annotations

import json

import httpx

from _bootstrap import add_repo_src_to_path

add_repo_src_to_path()

from _example_state import STATE_DIR, ensure_state_dir, load_session
from wechat_link import (
    Client,
    FileCursorStore,
    OpenClawInboundAggregator,
    OpenClawWeixinAdapter,
)


CURSOR_PATH = STATE_DIR / "openclaw_aggregate_cursor.json"


def _print_context(context) -> None:
    print(json.dumps(context.to_dict(), ensure_ascii=False, indent=2))
    if context.MediaPaths:
        print("media paths:")
        for path in context.MediaPaths:
            print("  -", path)


def main() -> None:
    ensure_state_dir()

    session = load_session()
    client = Client(
        bot_token=session["bot_token"],
        base_url=session.get("base_url", "https://ilinkai.weixin.qq.com"),
    )
    adapter = OpenClawWeixinAdapter(
        client,
        account_id=session.get("ilink_bot_id") or "wechat-account-1",
        state_dir=STATE_DIR,
    )
    aggregator = OpenClawInboundAggregator(adapter, merge_window_seconds=8)
    store = FileCursorStore(CURSOR_PATH)
    cursor = store.load() or ""

    print("send an image first, then send a follow-up question within 8 seconds.")
    print("the script will emit one merged OpenClaw context once the turn is ready.")

    try:
        while True:
            emitted = []

            try:
                updates = client.get_updates(cursor=cursor)
            except httpx.TimeoutException:
                updates = None

            if updates is not None:
                if updates.next_cursor:
                    cursor = updates.next_cursor
                    store.save(cursor)

                for message in updates.messages:
                    emitted.extend(aggregator.ingest(message))

            emitted.extend(aggregator.flush_ready())

            if not emitted:
                continue

            _print_context(emitted[0])
            return
    finally:
        client.close()


if __name__ == "__main__":
    main()
