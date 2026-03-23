# wechat-link

Unofficial Python SDK for iLink-compatible Weixin Bot integration.

`wechat-link` 是一个面向 iLink-compatible Weixin Bot 集成的 Python SDK，重点放在协议层、媒体链路和一个可选的轻量 Relay 上，而不是去做一个大而全的 Bot 平台。

## What it currently provides

- QR login primitives: `get_bot_qrcode()` / `get_qrcode_status()`
- Long polling: `get_updates()`
- Text messaging: `send_text()`
- Typing support: `get_config()` / `send_typing()`
- Media workflow:
  - `get_upload_url()`
  - `upload_image()` / `send_image()`
  - `upload_file()` / `send_file()`
  - `upload_video()` / `send_video()`
  - `upload_voice()` / `send_voice()`
- Optional FastAPI relay layer

## Installation

```bash
pip install wechat-link
```

Relay extras:

```bash
pip install "wechat-link[relay]"
```

## Minimal usage example

```python
from wechat_link import Client

client = Client(bot_token="your-bot-token")
updates = client.get_updates(cursor="")

print("next_cursor:", updates.next_cursor)
print("messages:", len(updates.messages))

client.close()
```

## Quick example

```python
import time

from wechat_link import Client, FileCursorStore

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
```

## Project links

- Repository: <https://github.com/syusama/wechat-link>
- Issues: <https://github.com/syusama/wechat-link/issues>
- Chinese README: <https://github.com/syusama/wechat-link/blob/main/README.md>
- English README: <https://github.com/syusama/wechat-link/blob/main/README.en.md>
- Japanese README: <https://github.com/syusama/wechat-link/blob/main/README.ja.md>

## Notes

- This is an **unofficial** project.
- It should not be described as a Tencent official SDK or official platform replacement.
- The PyPI page keeps the package overview concise; the full documentation and examples live in the GitHub repository.
