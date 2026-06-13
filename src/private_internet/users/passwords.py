"""Password hashing for platform user accounts.

Uses stdlib ``hashlib.scrypt`` so we add no native dependency (bcrypt/argon2).
Stored format is self-describing so parameters can evolve without a migration:

    scrypt$<n>$<r>$<p>$<salt_b64>$<hash_b64>

Never log raw passwords or these hashes.
"""

import base64
import hmac
import os
from hashlib import scrypt

# Cost parameters. n must be a power of two; 2**14 keeps verification well under
# ~100ms on the EC2 host while staying expensive to brute-force.
_N = 2**14
_R = 8
_P = 1
_DKLEN = 32
_SALT_BYTES = 16

MIN_PASSWORD_LENGTH = 12


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    salt = os.urandom(_SALT_BYTES)
    derived = scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(derived)}"


def verify_password(password: str, stored: str | None) -> bool:
    """Constant-time check of ``password`` against a stored hash. False on any
    malformed/absent hash rather than raising."""
    if not stored:
        return False
    try:
        scheme, n_s, r_s, p_s, salt_b64, hash_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        n, r, p = int(n_s), int(r_s), int(p_s)
        salt = _unb64(salt_b64)
        expected = _unb64(hash_b64)
    except (ValueError, base64.binascii.Error):
        return False
    derived = scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=len(expected))
    return hmac.compare_digest(derived, expected)
