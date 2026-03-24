from __future__ import annotations

from _bootstrap import add_repo_src_to_path

add_repo_src_to_path()

from _example_state import load_last_context, load_session
from wechat_link import Client


TEXT = "this is a proactive message in the same session"


def main() -> None:
    session = load_session()
    context = load_last_context()

    client = Client(
        bot_token=session["bot_token"],
        base_url=session.get("base_url", "https://ilinkai.weixin.qq.com"),
    )

    try:
        client_id = client.send_text(
            to_user_id=context["from_user_id"],
            text=TEXT,
            context_token=context["context_token"],
        )
        print("sent text:", TEXT)
        print("to_user_id:", context["from_user_id"])
        print("context_token:", context["context_token"])
        print("client_id:", client_id)
    finally:
        client.close()


if __name__ == "__main__":
    main()
