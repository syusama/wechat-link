from __future__ import annotations

import base64
import re

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


HEX_KEY_RE = re.compile(r"^[0-9a-fA-F]{32}$")


def encrypt_aes_ecb(plaintext: bytes, key: bytes) -> bytes:
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    encryptor = cipher.encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def decrypt_aes_ecb(ciphertext: bytes, key: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


def aes_ecb_padded_size(plaintext_size: int) -> int:
    return ((plaintext_size // 16) + 1) * 16


def parse_cdn_aes_key(aes_key_base64: str) -> bytes:
    decoded = base64.b64decode(aes_key_base64)
    if len(decoded) == 16:
        return decoded
    ascii_value = decoded.decode("ascii")
    if len(decoded) == 32 and HEX_KEY_RE.fullmatch(ascii_value):
        return bytes.fromhex(ascii_value)
    raise ValueError("aes_key must decode to 16 raw bytes or 32 hex characters")


def encode_cdn_aes_key_from_hex(hex_key: str) -> str:
    if not HEX_KEY_RE.fullmatch(hex_key):
        raise ValueError("hex_key must be 32 hex characters")
    return base64.b64encode(hex_key.encode("ascii")).decode("utf-8")

