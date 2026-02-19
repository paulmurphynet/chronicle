# Encryption helpers (optional)

Chronicle provides optional helper functions in `chronicle/core/encryption.py` for encrypting/decrypting bytes with AES-256-GCM.

Install extra dependencies:

```bash
pip install -e ".[encryption]"
```

Available helpers:

- `generate_key_b64()` -> generate a base64url 32-byte key
- `encrypt_bytes(key_b64, plaintext)` -> returns `nonce + ciphertext_and_tag`
- `decrypt_bytes(key_b64, blob)` -> decrypts output of `encrypt_bytes`

Notes:

- These are low-level helpers. Chronicle does not automatically encrypt project databases or evidence files.
- Key management and rotation are your responsibility.
- For production deployments, combine these helpers with secure key storage (for example, KMS or HSM-backed secrets).

See also: [POSTGRES](POSTGRES.md), [to_do](to_do.md).
