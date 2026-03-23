from __future__ import annotations

import time
from pathlib import Path

from _bootstrap import add_repo_src_to_path

add_repo_src_to_path()

from wechat_link import Client, FileCursorStore


STATE_DIR = Path(__file__).resolve().parents[1] / ".state"
CURSOR_PATH = STATE_DIR / "get_updates_buf.json"


def main() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    client = Client(bot_token="your-bot-token")
    store = FileCursorStore(CURSOR_PATH)
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
