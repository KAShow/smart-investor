"""Symmetric encryption for PII at rest.

Use Fernet (AES-128 in CBC + HMAC-SHA256) when FERNET_KEY is configured.
Falls back to plaintext storage when not configured (with a warning) so the app
remains functional in dev — production deploys MUST set FERNET_KEY.
"""
import logging
from functools import lru_cache

from config import Config

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _fernet():
    if not Config.FERNET_KEY:
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(Config.FERNET_KEY.encode() if isinstance(Config.FERNET_KEY, str) else Config.FERNET_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Fernet: {e}")
        return None


def fernet_available() -> bool:
    return _fernet() is not None


def encrypt_pii(plaintext: str | None) -> str:
    if not plaintext:
        return ''
    f = _fernet()
    if not f:
        logger.warning("FERNET_KEY not set — storing PII in plaintext")
        return plaintext
    try:
        return f.encrypt(plaintext.encode('utf-8')).decode('ascii')
    except Exception as e:
        logger.error(f"PII encryption failed: {e}")
        return plaintext


def decrypt_pii(ciphertext: str | None) -> str:
    if not ciphertext:
        return ''
    f = _fernet()
    if not f:
        return ciphertext
    try:
        return f.decrypt(ciphertext.encode('ascii')).decode('utf-8')
    except Exception:
        return ciphertext
