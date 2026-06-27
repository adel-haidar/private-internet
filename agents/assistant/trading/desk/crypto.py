"""Symmetric encryption for stored broker credentials (Trading 212 API key/secret).

Broker secrets are stored as CIPHERTEXT in `trading_broker_connection` (db.py just
persists/returns the encrypted strings). Encryption/decryption happens HERE, in the
service layer, so the database never sees plaintext.

Fernet (AES-128-CBC + HMAC) from the `cryptography` library. The key is derived
deterministically from env `TRADING_SECRET_KEY` (falling back to `SECRET_KEY`) so the
same process can always decrypt what it wrote, without a separate key-management
system. NEVER log plaintext keys or the derived Fernet key.
"""

import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class CryptoError(RuntimeError):
    """Raised when encryption/decryption cannot proceed (missing key, bad token)."""


def _derive_fernet_key() -> bytes:
    """Derive a urlsafe-base64 32-byte Fernet key from the configured secret.

    A Fernet key must be 32 url-safe base64-encoded bytes. The operator-supplied
    secret is an arbitrary string, so we hash it to a fixed 32 bytes (SHA-256) and
    base64-encode that. Deterministic: the same secret always yields the same key.
    """
    secret = os.environ.get("TRADING_SECRET_KEY") or os.environ.get("SECRET_KEY")
    if not secret:
        raise CryptoError(
            "No encryption secret configured — set TRADING_SECRET_KEY (or SECRET_KEY)."
        )
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet:
    return Fernet(_derive_fernet_key())


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext secret, returning a urlsafe ciphertext string.

    Raises CryptoError if no secret is configured. Never logs the plaintext.
    """
    if plaintext is None:
        raise CryptoError("Cannot encrypt None.")
    token = _fernet().encrypt(plaintext.encode("utf-8"))
    return token.decode("ascii")


def decrypt(ciphertext: str) -> str:
    """Decrypt a ciphertext produced by `encrypt`, returning the plaintext.

    Raises CryptoError on a tampered/incompatible token or missing secret. Never
    logs the recovered plaintext.
    """
    if ciphertext is None:
        raise CryptoError("Cannot decrypt None.")
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise CryptoError(
            "Failed to decrypt broker secret — the encryption key may have changed."
        ) from exc
