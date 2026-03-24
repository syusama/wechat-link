from __future__ import annotations

import httpx

from _bootstrap import add_repo_src_to_path

add_repo_src_to_path()

from _example_state import STATE_DIR, load_session, save_last_context
from wechat_link import Client, FileCursorStore


CURSOR_PATH = STATE_DIR / "reply_once_cursor.json"


def main() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    session = load_session()

    client = Client(
        bot_token=session["bot_token"],
        base_url=session.get("base_url", "https://ilinkai.weixin.qq.com"),
    )
    store = FileCursorStore(CURSOR_PATH)
    cursor = store.load() or ""

    print("waiting for one new message to reply...")
    print("send a text message to the bot from WeChat now.")

    try:
        try:
            updates = client.get_updates(cursor=cursor)
        except httpx.TimeoutException:
            print("no new message arrived during this polling window.")
            return

        if updates.next_cursor:
            store.save(updates.next_cursor)

        for message in updates.messages:
            text = message.text().strip()
            if not text or not message.from_user_id or not message.context_token:
                continue

            context_path = save_last_context(
                from_user_id=message.from_user_id,
                context_token=message.context_token,
                text=text,
            )
            print("received:", text)
            print("from_user_id:", message.from_user_id)
            print("context_token:", message.context_token)
            print("saved context to:", context_path.resolve())

            client_id = client.send_text(
                to_user_id=message.from_user_id,
                text=f"received: {text}",
                context_token=message.context_token,
            )
            print("reply sent, client_id:", client_id)
            return

        print("received messages, but none were text messages with reply context.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
