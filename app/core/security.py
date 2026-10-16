"""Security utilities for encrypting and decrypting sensitive external tokens at rest."""

import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings


def _get_fernet() -> Fernet:
    """Derive a consistent 32-byte urlsafe Fernet key from configured ENCRYPTION_KEY."""
    key_bytes = settings.ENCRYPTION_KEY.encode("utf-8")
    derived_key = base64.urlsafe_b64encode(hashlib.sha256(key_bytes).digest())
    return Fernet(derived_key)


def encrypt_token(token: str) -> str:
    """Encrypt a plain text token for safe database persistence."""
    if not token:
        return ""
    fernet = _get_fernet()
    return fernet.encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a ciphertext token stored in the database."""
    if not encrypted_token:
        return ""
    fernet = _get_fernet()
    return fernet.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
