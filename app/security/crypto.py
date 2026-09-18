from __future__ import annotations
from cryptography.fernet import Fernet
from pathlib import Path
from app.settings import settings

_KEYFILE = Path(settings.data_dir) / "local_key.bin"

def _get_or_create_key() -> bytes:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    if _KEYFILE.exists():
        return _KEYFILE.read_bytes()
    key = Fernet.generate_key()
    _KEYFILE.write_bytes(key)
    return key

def encrypt_str(plaintext: str) -> str:
    f = Fernet(_get_or_create_key())
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")

def decrypt_str(ciphertext: str) -> str:
    f = Fernet(_get_or_create_key())
    return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def get_local_secret() -> bytes:
    """Return a stable per-machine secret (created on first run).

    Used for local-only integrity seals (HMAC) and proof-of-creation stamps.
    """
    return _get_or_create_key()
