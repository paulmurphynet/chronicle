# Optional encryption helpers for .chronicle or evidence at rest. See docs/ENCRYPTION.md.
# Requires pip install -e ".[encryption]" (cryptography).

from __future__ import annotations

import base64
import os
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    pass

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    AESGCM = None  # type: ignore[misc, assignment]

NONCE_BYTES = 12
KEY_BYTES = 32  # AES-256


def _key_from_b64(key_b64: str) -> bytes:
    s = key_b64.encode("ascii")
    pad = 4 - len(s) % 4
    if pad != 4:
        s += b"=" * pad
    raw = base64.urlsafe_b64decode(s)
    if len(raw) != KEY_BYTES:
        raise ValueError(f"Key must be {KEY_BYTES} bytes (base64-encoded)")
    return raw


def encrypt_bytes(key_b64: str, plaintext: bytes) -> bytes:
    """Encrypt with AES-256-GCM. Key is 32-byte base64url. Returns nonce + ciphertext (ciphertext includes tag)."""
    if AESGCM is None:
        raise ImportError("Encryption requires pip install -e '.[encryption]' (cryptography)")
    key = _key_from_b64(key_b64)
    nonce = os.urandom(NONCE_BYTES)
    aad = b""
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext, aad)
    return cast(bytes, nonce + ct)


def decrypt_bytes(key_b64: str, blob: bytes) -> bytes:
    """Decrypt blob produced by encrypt_bytes (nonce + ciphertext+tag)."""
    if AESGCM is None:
        raise ImportError("Encryption requires pip install -e '.[encryption]' (cryptography)")
    if len(blob) < NONCE_BYTES + 16:
        raise ValueError("Blob too short")
    key = _key_from_b64(key_b64)
    nonce = blob[:NONCE_BYTES]
    ct = blob[NONCE_BYTES:]
    aad = b""
    aesgcm = AESGCM(key)
    return cast(bytes, aesgcm.decrypt(nonce, ct, aad))


def generate_key_b64() -> str:
    """Return a new 32-byte key as base64url (for CHRONICLE_ENCRYPTION_KEY)."""
    if AESGCM is None:
        raise ImportError("Encryption requires pip install -e '.[encryption]' (cryptography)")
    key = os.urandom(KEY_BYTES)
    return base64.urlsafe_b64encode(key).decode("ascii").rstrip("=")
