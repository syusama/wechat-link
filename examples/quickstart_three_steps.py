from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

from _bootstrap import add_repo_src_to_path

add_repo_src_to_path()

from wechat_link import Client, FileCursorStore


REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = REPO_ROOT / ".state"
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


def save_qr_image(client: Client, qrcode_img_content: str) -> Path | None:
    if not qrcode_img_content:
        return None

    try:
        return client.save_qrcode_image(
            qrcode_img_content,
            output_path=QR_IMAGE_PATH,
        )
    except Exception:
        return None


def print_qr_in_terminal(client: Client, qrcode_img_content: str) -> bool:
    if not qrcode_img_content:
        return False

    try:
        print("terminal qr:")
        client.print_qrcode_terminal(qrcode_img_content)
        return True
    except Exception:
        return False


def login() -> dict[str, str]:
    client = Client()
    qr = client.get_bot_qrcode()

    print("Step 1/3: scan the QR code with WeChat")
    print("qrcode:", qr.qrcode)
    print("qrcode_url:", qr.qrcode_img_content)

    image_path = save_qr_image(client, qr.qrcode_img_content)
    if image_path:
        print("qr image saved to:", image_path.resolve())
    else:
        print("could not save QR image automatically, open qrcode_url directly")

    if not print_qr_in_terminal(client, qr.qrcode_img_content):
        print("could not render terminal QR automatically")

    try:
        while True:
            try:
                status = client.get_qrcode_status(qr.qrcode)
            except httpx.TimeoutException:
                print("QR status request timed out, keep waiting...")
                continue

            print("qr status:", status.status)

            if status.status == "confirmed" and status.bot_token:
                session = {
                    "bot_token": status.bot_token,
                    "base_url": status.baseurl or "https://ilinkai.weixin.qq.com",
                    "ilink_bot_id": status.ilink_bot_id or "",
                    "ilink_user_id": status.ilink_user_id or "",
                }
                save_session(session)
                print("login confirmed, session saved to:", SESSION_PATH.resolve())
                return session

            time.sleep(1)
    finally:
        client.close()


def get_or_login_session() -> dict[str, str]:
    session = load_session()
    if session and session.get("bot_token"):
        print("Step 1/3: found local session, skip QR login")
        return session
    return login()


def start_echo(session: dict[str, str]) -> None:
    print("Step 2/3: initialize Client")
    client = Client(
        bot_token=session["bot_token"],
        base_url=session.get("base_url", "https://ilinkai.weixin.qq.com"),
    )
    store = FileCursorStore(CURSOR_PATH)
    cursor = store.load() or ""

    print("Step 3/3: start echo loop")
    print("send a text message to the bot from WeChat now.")

    try:
        while True:
            try:
                updates = client.get_updates(cursor=cursor)
            except httpx.TimeoutException:
                print("get_updates timed out, continue polling...")
                continue

            if updates.next_cursor:
                cursor = updates.next_cursor
                store.save(cursor)

            if not updates.messages:
                print("received 0 messages in this polling round.")
                time.sleep(1)
                continue

            for message in updates.messages:
                text = message.text().strip()
                if not text or not message.from_user_id or not message.context_token:
                    continue

                print("message:", text)
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
