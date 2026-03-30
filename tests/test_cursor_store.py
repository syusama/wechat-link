from pathlib import Path

from wechat_link.store import FileContextTokenStore, FileCursorStore


def test_file_cursor_store_round_trip(tmp_path: Path) -> None:
    store = FileCursorStore(tmp_path / "cursor.json")

    assert store.load() is None

    store.save("next-cursor")

    assert store.load() == "next-cursor"


def test_file_context_token_store_isolates_accounts(tmp_path: Path) -> None:
    store = FileContextTokenStore(tmp_path / "state")

    assert store.load("account-a", "user@im.wechat") is None

    store.save("account-a", "user@im.wechat", "ctx-a")
    store.save("account-b", "user@im.wechat", "ctx-b")

    assert store.load("account-a", "user@im.wechat") == "ctx-a"
    assert store.load("account-b", "user@im.wechat") == "ctx-b"
