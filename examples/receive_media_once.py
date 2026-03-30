from __future__ import annotations

import httpx

from _bootstrap import add_repo_src_to_path

add_repo_src_to_path()

from _example_state import STATE_DIR, ensure_state_dir, load_session
from wechat_link import Client, FileCursorStore


CURSOR_PATH = STATE_DIR / "receive_media_once_cursor.json"
MEDIA_DIR = STATE_DIR / "inbound-media"


def _media_output_name(*, message_index: int, item_index: int, kind: str, file_name: str | None) -> str:
    if file_name:
        return file_name
    return f"message-{message_index}-item-{item_index}-{kind}.bin"


def main() -> None:
    ensure_state_dir()
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    session = load_session()
    client = Client(
        bot_token=session["bot_token"],
        base_url=session.get("base_url", "https://ilinkai.weixin.qq.com"),
    )
    store = FileCursorStore(CURSOR_PATH)
    cursor = store.load() or ""

    print("waiting for one new message...")
    print("send a media message to the bot from WeChat now.")

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

        for message_index, message in enumerate(updates.messages, start=1):
            print(f"message #{message_index}")
            print("  kind:", message.kind())
            print("  from_user_id:", message.from_user_id or "")
            print("  context_token:", message.context_token or "")
            print("  text:", message.text().strip())

            items = message.items()
            if not items:
                print("  parsed_items: 0")
                continue

            for item_index, item in enumerate(items, start=1):
                print(f"  item #{item_index}: {item.kind}")

                if item.file_name:
                    print("    file_name:", item.file_name)
                if item.size is not None:
                    print("    size:", item.size)
                if item.width is not None and item.height is not None:
                    print("    thumb:", f"{item.width}x{item.height}")
                if item.playtime is not None:
                    print("    playtime:", item.playtime)

                if item.media is None:
                    continue

                output_name = _media_output_name(
                    message_index=message_index,
                    item_index=item_index,
                    kind=item.kind,
                    file_name=item.file_name,
                )
                output_path = MEDIA_DIR / output_name
                output_path.write_bytes(client.download_message_item(item))
                print("    saved_to:", output_path.resolve())
    finally:
        client.close()


if __name__ == "__main__":
    main()
