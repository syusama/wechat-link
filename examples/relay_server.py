from __future__ import annotations

from wechat_link.client import WeChatLinkClient
from wechat_link.relay import create_relay_app
from wechat_link.store import FileCursorStore


client = WeChatLinkClient(bot_token="your-bot-token")
cursor_store = FileCursorStore(".state/get_updates_buf.json")
app = create_relay_app(client=client, cursor_store=cursor_store)
