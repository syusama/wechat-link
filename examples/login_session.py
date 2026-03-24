from __future__ import annotations

import time
from pathlib import Path

import httpx

from _bootstrap import add_repo_src_to_path

add_repo_src_to_path()

from _example_state import STATE_DIR, save_session
from wechat_link import Client


QR_IMAGE_PATH = STATE_DIR / "wechat-login-qrcode.png"


def issue_login_qrcode(client: Client):
    qr = client.get_bot_qrcode()
    image_path = client.save_qrcode_image(
        qr.qrcode_img_content,
        output_path=QR_IMAGE_PATH,
    )

    print("scan this QR code with WeChat.")
    print("qrcode:", qr.qrcode)
    print("qrcode_url:", qr.qrcode_img_content)
    print("qrcode_image:", Path(image_path).resolve())
    print("terminal qr:")
    client.print_qrcode_terminal(qr.qrcode_img_content)
    return qr


def main() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    client = Client()
    qr = issue_login_qrcode(client)

    try:
        while True:
            try:
                status = client.get_qrcode_status(qr.qrcode)
            except httpx.TimeoutException:
                print("QR status request timed out, keep waiting...")
                continue

            print("qr status:", status.status)

            if status.status == "confirmed" and status.bot_token:
                session_path = save_session(
                    {
                        "bot_token": status.bot_token,
                        "base_url": status.baseurl or "https://ilinkai.weixin.qq.com",
                        "ilink_bot_id": status.ilink_bot_id or "",
                        "ilink_user_id": status.ilink_user_id or "",
                    }
                )
                print("session saved to:", session_path.resolve())
                return

            if status.status == "expired":
                print("QR code expired, refreshing...")
                qr = issue_login_qrcode(client)
                continue

            time.sleep(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
