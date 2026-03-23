import base64

from wechat_link.crypto import (
    aes_ecb_padded_size,
    decrypt_aes_ecb,
    encrypt_aes_ecb,
    parse_cdn_aes_key,
)


def test_aes_ecb_round_trip_restores_plaintext() -> None:
    key = b"0123456789abcdef"
    plaintext = b"hello wechat link"

    ciphertext = encrypt_aes_ecb(plaintext, key)
    decrypted = decrypt_aes_ecb(ciphertext, key)

    assert ciphertext != plaintext
    assert decrypted == plaintext


def test_aes_ecb_padded_size_matches_pkcs7_boundaries() -> None:
    assert aes_ecb_padded_size(1) == 16
    assert aes_ecb_padded_size(16) == 32
    assert aes_ecb_padded_size(17) == 32


def test_parse_cdn_aes_key_accepts_base64_raw_key() -> None:
    key = b"0123456789abcdef"
    encoded = base64.b64encode(key).decode("utf-8")

    assert parse_cdn_aes_key(encoded) == key


def test_parse_cdn_aes_key_accepts_base64_of_hex_string() -> None:
    hex_key = b"30313233343536373839616263646566"
    encoded = base64.b64encode(hex_key).decode("utf-8")

    assert parse_cdn_aes_key(encoded) == bytes.fromhex(hex_key.decode("ascii"))

