from __future__ import annotations

from io import BytesIO

from fastapi import UploadFile


def test_temporary_upload_path_saves_file_and_cleans_up() -> None:
    from wechat_link.relay import _temporary_upload_path

    upload = UploadFile(filename="demo.jpg", file=BytesIO(b"image-bytes"))

    with _temporary_upload_path(upload) as temp_path:
        assert temp_path is not None
        assert temp_path.name == "demo.jpg"
        assert temp_path.exists()
        assert temp_path.read_bytes() == b"image-bytes"
        parent = temp_path.parent

    assert not parent.exists()


def test_temporary_upload_path_allows_missing_optional_upload() -> None:
    from wechat_link.relay import _temporary_upload_path

    with _temporary_upload_path(None) as temp_path:
        assert temp_path is None
