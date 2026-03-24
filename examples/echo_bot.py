from __future__ import annotations

import time

import httpx

from _bootstrap import add_repo_src_to_path

add_repo_src_to_path()

from _example_state import STATE_DIR, load_session
from wechat_link import Client, FileCursorStore


CURSOR_PATH = STATE_DIR / "get_updates_buf.json"


def main() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    session = load_session()
    client = Client(
        bot_token=session["bot_token"],
        base_url=session.get("base_url", "https://ilinkai.weixin.qq.com"),
    )
    store = FileCursorStore(CURSOR_PATH)
    cursor = store.load() or ""

    print("echo bot started.")
    print("waiting for new inbound messages...")

    try:
        while True:
            try:
                updates = client.get_updates(cursor=cursor)
            except httpx.TimeoutException:
                print("no new messages yet, continue polling...")
                continue

            if updates.next_cursor:
                cursor = updates.next_cursor
                store.save(cursor)

            for message in updates.messages:
                text = message.text().strip()
                if not text or not message.from_user_id or not message.context_token:
                    continue

                print("received:", text)
                print("from_user_id:", message.from_user_id)
                print("context_token:", message.context_token)

                client_id = client.send_text(
                    to_user_id=message.from_user_id,
                    text=f"echo: {text}",
                    context_token=message.context_token,
                )
                print("reply sent, client_id:", client_id)

            time.sleep(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
