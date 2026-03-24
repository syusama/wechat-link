from __future__ import annotations

from pathlib import Path

from _bootstrap import add_repo_src_to_path

add_repo_src_to_path()

from _example_state import load_session
from wechat_link import Client
from wechat_link.relay import create_relay_app
from wechat_link.store import FileCursorStore


STATE_DIR = Path(__file__).resolve().parents[1] / ".state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

session = load_session()
client = Client(
    bot_token=session["bot_token"],
    base_url=session.get("base_url", "https://ilinkai.weixin.qq.com"),
)
cursor_store = FileCursorStore(STATE_DIR / "get_updates_buf.json")
app = create_relay_app(client=client, cursor_store=cursor_store)
