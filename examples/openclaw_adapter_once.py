from __future__ import annotations

import json

import httpx

from _bootstrap import add_repo_src_to_path

add_repo_src_to_path()

from _example_state import STATE_DIR, ensure_state_dir, load_session
from wechat_link import Client, FileCursorStore, OpenClawWeixinAdapter


CURSOR_PATH = STATE_DIR / "openclaw_adapter_cursor.json"


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
    store = FileCursorStore(CURSOR_PATH)
    cursor = store.load() or ""

    print("waiting for one new message to normalize into OpenClaw context...")

    try:
        try:
            updates = client.get_updates(cursor=cursor)
        except httpx.TimeoutException:
            print("no new message arrived during this polling window.")
            return

        if updates.next_cursor:
            store.save(updates.next_cursor)

        if not updates.messages:
            print("received 0 messages.")
            return

        message = updates.messages[0]
        context = adapter.build_inbound_context(message)
        print(json.dumps(context.to_dict(), ensure_ascii=False, indent=2))

        if context.MediaPath:
            print("media saved to:", context.MediaPath)
        if context.MediaPaths:
            print("media paths:")
            for path in context.MediaPaths:
                print("  -", path)
        if context.ArchiveExtracted:
            print("archive extracted:", context.ArchivePath or "")
            for entry in context.ArchiveEntries or []:
                print("  -", entry)

        # If you want to test the outbound side too, uncomment this:
        # adapter.send_reply_from_context(context, text="**received** via OpenClaw adapter")
    finally:
        client.close()


if __name__ == "__main__":
    main()
