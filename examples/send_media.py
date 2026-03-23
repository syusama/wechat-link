from __future__ import annotations

from _bootstrap import add_repo_src_to_path

add_repo_src_to_path()

from wechat_link import Client


def main() -> None:
    client = Client(bot_token="your-bot-token")

    uploaded = client.upload_image(
        file_path="demo.jpg",
        to_user_id="user@im.wechat",
    )

    client.send_image(
        to_user_id="user@im.wechat",
        uploaded=uploaded,
        context_token="ctx-from-inbound-message",
    )

    uploaded_video = client.upload_video(
        file_path="demo.mp4",
        to_user_id="user@im.wechat",
        thumb_path="thumb.jpg",
    )

    client.send_video(
        to_user_id="user@im.wechat",
        uploaded=uploaded_video,
        context_token="ctx-from-inbound-message",
    )

    client.close()


if __name__ == "__main__":
    main()
