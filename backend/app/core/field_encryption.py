"""Field-level symmetric encryption for sensitive member identifiers."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_fernet_cache: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet_cache
    if _fernet_cache is None:
        _fernet_cache = Fernet(settings.FIELD_ENCRYPTION_KEY.encode("utf-8"))
    return _fernet_cache


def reset_fernet_cache() -> None:
    """Drop the cached Fernet so a rotated FIELD_ENCRYPTION_KEY takes effect."""
    global _fernet_cache
    _fernet_cache = None


def encrypt_field(plaintext: str) -> bytes:
    if not plaintext:
        raise ValueError("Refusing to encrypt an empty field")
    return _get_fernet().encrypt(plaintext.encode("utf-8"))


def decrypt_field(ciphertext: bytes | bytearray | memoryview | None) -> str | None:
    if ciphertext is None:
        return None
    try:
        return _get_fernet().decrypt(bytes(ciphertext)).decode("utf-8")
    except InvalidToken:
        return None


def derive_member_last4(member_id: str) -> str:
    """Masked display fragment: last 4 digits, else up to last 4 alphanumerics."""
    digits = "".join(ch for ch in member_id if ch.isdigit())
    if len(digits) >= 4:
        return digits[-4:]
    tail = member_id[-4:].replace(" ", "").upper()
    return tail if tail else ""
