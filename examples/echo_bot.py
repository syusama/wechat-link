from __future__ import annotations

import time

from wechat_link import Client, FileCursorStore


def main() -> None:
client = Client(bot_token="your-bot-token")
    store = FileCursorStore(".state/get_updates_buf.json")
    cursor = store.load() or ""

    try:
        while True:
            updates = client.get_updates(cursor=cursor)
            if updates.next_cursor:
                cursor = updates.next_cursor
                store.save(cursor)

            for message in updates.messages:
                text = message.text().strip()
                if not text or not message.from_user_id or not message.context_token:
                    continue

                client.send_text(
                    to_user_id=message.from_user_id,
                    text=f"echo: {text}",
                    context_token=message.context_token,
                )

            time.sleep(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
