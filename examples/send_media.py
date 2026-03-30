from __future__ import annotations

from _bootstrap import add_repo_src_to_path

add_repo_src_to_path()

from wechat_link import Client


def main() -> None:
    client = Client(bot_token="your-bot-token")
    context_token = "ctx-from-inbound-message"
    to_user_id = "user@im.wechat"

    uploaded = client.upload_image(
        file_path="demo.jpg",
        to_user_id=to_user_id,
    )

    client.send_image(
        to_user_id=to_user_id,
        uploaded=uploaded,
        context_token=context_token,
    )

    uploaded_file = client.upload_file(
        file_path="report.md",
        to_user_id=to_user_id,
    )

    client.send_file(
        to_user_id=to_user_id,
        file_name="report.md",
        uploaded=uploaded_file,
        context_token=context_token,
    )

    uploaded_video = client.upload_video(
        file_path="demo.mp4",
        to_user_id=to_user_id,
        thumb_path="thumb.jpg",
    )

    client.send_video(
        to_user_id=to_user_id,
        uploaded=uploaded_video,
        context_token=context_token,
    )

    uploaded_voice = client.upload_voice(
        file_path="demo.wav",
        to_user_id=to_user_id,
    )

    client.send_voice(
        to_user_id=to_user_id,
        uploaded=uploaded_voice,
        context_token=context_token,
        text="voice reply",
    )

    client.close()


if __name__ == "__main__":
    main()
