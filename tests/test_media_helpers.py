import hashlib
from pathlib import Path

from PIL import Image


def test_prepare_upload_source_derives_common_upload_metadata(tmp_path: Path) -> None:
    from wechat_link.media import _prepare_upload_source

    file_path = tmp_path / "demo.bin"
    file_path.write_bytes(b"wechat-link-media")

    prepared = _prepare_upload_source(file_path)

    assert prepared.file_size == len(b"wechat-link-media")
    assert prepared.file_size_ciphertext == 32
    assert prepared.raw_md5 == hashlib.md5(b"wechat-link-media").hexdigest()
    assert len(prepared.filekey) == 32
    assert len(prepared.aes_key) == 16
    assert prepared.aes_key_hex == prepared.aes_key.hex()


def test_prepare_thumb_source_reads_dimensions(tmp_path: Path) -> None:
    from wechat_link.media import _prepare_thumb_source

    thumb_path = tmp_path / "thumb.jpg"
    Image.new("RGB", (120, 80), color="red").save(thumb_path, format="JPEG")

    prepared = _prepare_thumb_source(thumb_path)

    assert prepared.file_size > 0
    assert prepared.file_size_ciphertext >= prepared.file_size
    assert prepared.raw_md5
    assert prepared.width == 120
    assert prepared.height == 80
