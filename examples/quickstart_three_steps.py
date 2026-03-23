from __future__ import annotations

import base64
import json
import time
from pathlib import Path

from wechat_link import Client, FileCursorStore


STATE_DIR = Path(".state")
SESSION_PATH = STATE_DIR / "wechat-link-session.json"
CURSOR_PATH = STATE_DIR / "get_updates_buf.json"
QR_IMAGE_PATH = STATE_DIR / "wechat-login-qrcode.png"


def ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_session() -> dict[str, str] | None:
    if not SESSION_PATH.exists():
        return None
    return json.loads(SESSION_PATH.read_text(encoding="utf-8"))


def save_session(session: dict[str, str]) -> None:
    ensure_state_dir()
    SESSION_PATH.write_text(
        json.dumps(session, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_qr_image(qrcode_img_content: str) -> Path | None:
    if not qrcode_img_content:
        return None

    payload = qrcode_img_content
    if "," in qrcode_img_content and qrcode_img_content.startswith("data:"):
        payload = qrcode_img_content.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(payload)
    except Exception:
        return None

    ensure_state_dir()
    QR_IMAGE_PATH.write_bytes(image_bytes)
    return QR_IMAGE_PATH


def login() -> dict[str, str]:
    client = Client()
    qr = client.get_bot_qrcode()

    print("Step 1/3: 请使用微信扫码登录")
    print("qrcode:", qr.qrcode)

    image_path = save_qr_image(qr.qrcode_img_content)
    if image_path:
        print("二维码图片已保存到:", image_path)

    try:
        while True:
            status = client.get_qrcode_status(qr.qrcode)
            print("扫码状态:", status.status)

            if status.status == "confirmed" and status.bot_token:
                session = {
                    "bot_token": status.bot_token,
                    "base_url": status.baseurl or "https://ilinkai.weixin.qq.com",
                    "ilink_bot_id": status.ilink_bot_id or "",
                    "ilink_user_id": status.ilink_user_id or "",
                }
                save_session(session)
                print("登录成功，凭证已保存到:", SESSION_PATH)
                return session

            time.sleep(1)
    finally:
        client.close()


def get_or_login_session() -> dict[str, str]:
    session = load_session()
    if session and session.get("bot_token"):
        print("Step 1/3: 检测到本地凭证，跳过扫码")
        return session
    return login()


def start_echo(session: dict[str, str]) -> None:
    print("Step 2/3: 初始化 Client")
    client = Client(
        bot_token=session["bot_token"],
        base_url=session.get("base_url", "https://ilinkai.weixin.qq.com"),
    )
    store = FileCursorStore(CURSOR_PATH)
    cursor = store.load() or ""

    print("Step 3/3: 启动 echo 循环，给机器人发消息测试")

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

                print("收到消息:", text)
                client.send_text(
                    to_user_id=message.from_user_id,
                    text=f"echo: {text}",
                    context_token=message.context_token,
                )

            time.sleep(1)
    finally:
        client.close()


def main() -> None:
    ensure_state_dir()
    session = get_or_login_session()
    start_echo(session)


if __name__ == "__main__":
    main()
