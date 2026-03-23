from __future__ import annotations

from dataclasses import dataclass
import hashlib
import secrets
from pathlib import Path
from typing import Callable

from PIL import Image

from wechat_link.cdn import upload_buffer_to_cdn
from wechat_link.crypto import aes_ecb_padded_size
from wechat_link.models import UploadUrlResponse, UploadedMedia


MEDIA_TYPE_IMAGE = 1
MEDIA_TYPE_VIDEO = 2
MEDIA_TYPE_FILE = 3
MEDIA_TYPE_VOICE = 4


@dataclass(frozen=True)
class _PreparedUploadSource:
    plaintext: bytes
    file_size: int
    file_size_ciphertext: int
    raw_md5: str
    filekey: str
    aes_key: bytes
    aes_key_hex: str


@dataclass(frozen=True)
class _PreparedThumbSource:
    plaintext: bytes
    file_size: int
    file_size_ciphertext: int
    raw_md5: str
    width: int
    height: int


def _prepare_upload_source(file_path: str | Path) -> _PreparedUploadSource:
    path = Path(file_path)
    plaintext = path.read_bytes()
    file_size = len(plaintext)
    aes_key = secrets.token_bytes(16)
    return _PreparedUploadSource(
        plaintext=plaintext,
        file_size=file_size,
        file_size_ciphertext=aes_ecb_padded_size(file_size),
        raw_md5=hashlib.md5(plaintext).hexdigest(),
        filekey=secrets.token_hex(16),
        aes_key=aes_key,
        aes_key_hex=aes_key.hex(),
    )


def _prepare_thumb_source(file_path: str | Path) -> _PreparedThumbSource:
    path = Path(file_path)
    plaintext = path.read_bytes()
    file_size = len(plaintext)
    with Image.open(path) as image:
        width, height = image.size
    return _PreparedThumbSource(
        plaintext=plaintext,
        file_size=file_size,
        file_size_ciphertext=aes_ecb_padded_size(file_size),
        raw_md5=hashlib.md5(plaintext).hexdigest(),
        width=width,
        height=height,
    )


def _upload_prepared_source(
    *,
    plaintext: bytes,
    upload_param: str,
    filekey: str,
    cdn_base_url: str,
    aes_key: bytes,
    cdn_transport=None,
) -> str:
    return upload_buffer_to_cdn(
        buffer=plaintext,
        upload_param=upload_param,
        filekey=filekey,
        cdn_base_url=cdn_base_url,
        aes_key=aes_key,
        transport=cdn_transport,
    )


def upload_media_from_path(
    *,
    file_path: str | Path,
    to_user_id: str,
    media_type: int,
    cdn_base_url: str,
    request_upload_url: Callable[..., UploadUrlResponse],
    cdn_transport=None,
) -> UploadedMedia:
    prepared = _prepare_upload_source(file_path)

    upload_url = request_upload_url(
        filekey=prepared.filekey,
        media_type=media_type,
        to_user_id=to_user_id,
        rawsize=prepared.file_size,
        rawfilemd5=prepared.raw_md5,
        filesize=prepared.file_size_ciphertext,
        no_need_thumb=True,
        aeskey=prepared.aes_key_hex,
    )
    if not upload_url.upload_param:
        raise ValueError("get_upload_url returned no upload_param")

    download_param = _upload_prepared_source(
        plaintext=prepared.plaintext,
        upload_param=upload_url.upload_param,
        filekey=prepared.filekey,
        cdn_base_url=cdn_base_url,
        aes_key=prepared.aes_key,
        cdn_transport=cdn_transport,
    )
    return UploadedMedia(
        filekey=prepared.filekey,
        download_encrypted_query_param=download_param,
        aes_key_hex=prepared.aes_key_hex,
        file_size=prepared.file_size,
        file_size_ciphertext=prepared.file_size_ciphertext,
        raw_md5=prepared.raw_md5,
    )


def upload_video_with_thumb_from_path(
    *,
    file_path: str | Path,
    to_user_id: str,
    cdn_base_url: str,
    request_upload_url: Callable[..., UploadUrlResponse],
    cdn_transport=None,
    thumb_path: str | Path | None = None,
) -> UploadedMedia:
    prepared = _prepare_upload_source(file_path)
    thumb_prepared = _prepare_thumb_source(thumb_path) if thumb_path is not None else None

    upload_url = request_upload_url(
        filekey=prepared.filekey,
        media_type=MEDIA_TYPE_VIDEO,
        to_user_id=to_user_id,
        rawsize=prepared.file_size,
        rawfilemd5=prepared.raw_md5,
        filesize=prepared.file_size_ciphertext,
        thumb_rawsize=thumb_prepared.file_size if thumb_prepared is not None else None,
        thumb_rawfilemd5=thumb_prepared.raw_md5 if thumb_prepared is not None else None,
        thumb_filesize=thumb_prepared.file_size_ciphertext if thumb_prepared is not None else None,
        no_need_thumb=thumb_prepared is None,
        aeskey=prepared.aes_key_hex,
    )
    if not upload_url.upload_param:
        raise ValueError("get_upload_url returned no upload_param")

    download_param = _upload_prepared_source(
        plaintext=prepared.plaintext,
        upload_param=upload_url.upload_param,
        filekey=prepared.filekey,
        cdn_base_url=cdn_base_url,
        aes_key=prepared.aes_key,
        cdn_transport=cdn_transport,
    )

    thumb_download_param: str | None = None
    if thumb_prepared is not None:
        if not upload_url.thumb_upload_param:
            raise ValueError("get_upload_url returned no thumb_upload_param")
        thumb_download_param = _upload_prepared_source(
            plaintext=thumb_prepared.plaintext,
            upload_param=upload_url.thumb_upload_param,
            filekey=prepared.filekey,
            cdn_base_url=cdn_base_url,
            aes_key=prepared.aes_key,
            cdn_transport=cdn_transport,
        )

    return UploadedMedia(
        filekey=prepared.filekey,
        download_encrypted_query_param=download_param,
        aes_key_hex=prepared.aes_key_hex,
        file_size=prepared.file_size,
        file_size_ciphertext=prepared.file_size_ciphertext,
        raw_md5=prepared.raw_md5,
        thumb_download_encrypted_query_param=thumb_download_param,
        thumb_file_size=thumb_prepared.file_size if thumb_prepared is not None else None,
        thumb_file_size_ciphertext=thumb_prepared.file_size_ciphertext if thumb_prepared is not None else None,
        thumb_width=thumb_prepared.width if thumb_prepared is not None else None,
        thumb_height=thumb_prepared.height if thumb_prepared is not None else None,
    )
