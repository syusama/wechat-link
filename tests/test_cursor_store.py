from pathlib import Path

from wechat_link.store import FileCursorStore


def test_file_cursor_store_round_trip(tmp_path: Path) -> None:
    store = FileCursorStore(tmp_path / "cursor.json")

    assert store.load() is None

    store.save("next-cursor")

    assert store.load() == "next-cursor"

