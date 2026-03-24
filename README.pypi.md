# wechat-link

Connect WeChat to your app, agent, or workflow with a small amount of Python.

Scan to log in, then receive messages, reply, and send media without building a full bot platform first.

`wechat-link` is an unofficial Python SDK for iLink-compatible Weixin Bot integration. It keeps the path intentionally simple: get connected fast, then extend the integration your own way.

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

## Getting started order

If this is your first time using the SDK, follow this order:

1. Run QR login first and obtain `bot_token`
2. Initialize `Client(bot_token=...)`
3. Start polling and sending messages

The SDK returns `bot_token`, `baseurl`, `ilink_bot_id`, and `ilink_user_id` after QR confirmation. The value you need for `Client(...)` is `bot_token`.

For QR display, `qrcode_img_content` is currently a URL. If that URL points to a QR page instead of a raw image, the SDK generates a real QR locally. `Client.save_qrcode_image(...)` saves it to a local file, while `Client.render_qrcode_terminal(...)` / `Client.print_qrcode_terminal(...)` can render it directly in the terminal.

## Minimal usage example

```python
from wechat_link import Client, FileCursorStore

client = Client(bot_token="your-bot-token")
store = FileCursorStore(".state/get_updates_buf.json")
cursor = store.load() or ""
updates = client.get_updates(cursor=cursor)

if updates.next_cursor:
    store.save(updates.next_cursor)

for message in updates.messages:
    print("from_user_id:", message.from_user_id)
    print("context_token:", message.context_token)
    print("text:", message.text())

client.close()
```

## Quick example

If you want the clearest learning path, use these repository examples in order:

1. `python examples/login_session.py`
2. `python examples/receive_once.py`
3. `python examples/reply_once.py`
4. `python examples/send_text_in_session.py`
5. `python examples/echo_bot.py`

The important boundary is that replying or sending within an existing conversation requires the upstream `context_token`.

Core reply example:

```python
client.send_text(
    to_user_id=message.from_user_id,
    text=f"received: {message.text()}",
    context_token=message.context_token,
)
```

## Full three-step example

If you want the full onboarding flow in one runnable file, use:

```bash
python examples/quickstart_three_steps.py
```

The repository version of that example handles QR login, session persistence, and the echo loop end to end. When run from the repository, it prefers local `src/wechat_link` first and writes runtime files into the repository `.state/` directory.

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
