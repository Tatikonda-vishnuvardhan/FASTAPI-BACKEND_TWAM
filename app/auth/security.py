"""
app/auth/security.py
─────────────────────
JWT creation/verification and password utilities.

Changes vs original:
  - PASSWORD_CIPHER and CLIENT_ENCRYPT_KEY are no longer hardcoded.
    They are loaded at runtime from the AppSettings DB cache
    (app/shared/app_settings.py).  On first boot seed_defaults() inserts
    the original values so existing data stays compatible.
  - JWT config (SECRET_KEY, ALGORITHM, etc.) still comes from config.py /
    environment variables — those are infrastructure-level secrets that
    belong in .env, not in user-editable DB rows.
"""
import os
import base64
import hashlib
import hmac
import struct
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

from config import settings

# ── JWT Config (from .env via config.py — no hardcoded defaults) ─────────────
SECRET_KEY      = settings.secret_key
ALGORITHM       = settings.jwt_algorithm
ISSUER          = settings.jwt_issuer
AUDIENCE        = settings.jwt_audience
EXPIRES_MINUTES = settings.jwt_expires_minutes


# ── Runtime secret accessors (read from AppSettings cache) ───────────────────

def _get_password_cipher() -> str:
    """
    TWAM server-side password hash cipher.
    Loaded from AppSettings key 'password_cipher'.
    Falls back to the original hardcoded value so existing password hashes
    remain valid before the first DB migration.
    """
    from app.shared.app_settings import get_setting
    return get_setting("password_cipher", "TWAM@D&E*V@Tr@d@1#2$30%")


def _get_client_encrypt_key() -> bytes:
    """
    AES-CBC key Angular uses to pre-encrypt passwords before sending.
    Loaded from AppSettings key 'client_encrypt_key'.
    """
    from app.shared.app_settings import get_setting
    raw = get_setting("client_encrypt_key", "8080808080808080")
    return raw.encode("utf-8")


# ── Client password decryption ────────────────────────────────────────────────
# Angular CryptoService.encryptData() uses AES-CBC with the client_encrypt_key.

def _decrypt_client_password(cipher_text: str) -> str:
    key       = _get_client_encrypt_key()
    encrypted = base64.b64decode(cipher_text)
    cipher    = Cipher(algorithms.AES(key), modes.CBC(key))
    decryptor = cipher.decryptor()
    padded    = decryptor.update(encrypted) + decryptor.finalize()
    unpadder  = padding.PKCS7(128).unpadder()
    return (unpadder.update(padded) + unpadder.finalize()).decode("utf-8")


# ── TWAM server-side hash ─────────────────────────────────────────────────────

def generate_sha256_hash_with_salt(password: str, pwd_salt_key: str) -> str:
    step1   = hashlib.sha256(pwd_salt_key.encode("ascii")).digest()
    ba_hash = hashlib.sha256(step1).digest()
    salt    = bytes([1, 2, 3, 4, 5, 6, 7, 8])
    derived = hashlib.pbkdf2_hmac("sha1", ba_hash, salt, 1000, dklen=48)
    aes_key = derived[:32]
    aes_iv  = derived[32:48]

    pw_bytes = password.encode("utf-8")
    padder   = padding.PKCS7(128).padder()
    padded   = padder.update(pw_bytes) + padder.finalize()

    cipher    = Cipher(algorithms.AES(aes_key), modes.CBC(aes_iv))
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(encrypted).decode("utf-8")


# ── ASP.NET Core Identity password verification ───────────────────────────────

def verify_aspnet_identity_password(hashed_password: str, provided_password: str) -> bool:
    try:
        data    = base64.b64decode(hashed_password)
        version = data[0]

        if version == 0x01:
            prf        = struct.unpack(">I", data[1:5])[0]
            iter_count = struct.unpack(">I", data[5:9])[0]
            salt_len   = struct.unpack(">I", data[9:13])[0]
            salt       = data[13:13 + salt_len]
            stored     = data[13 + salt_len:]
            algo       = {1: "sha256", 2: "sha512"}.get(prf)
            if not algo:
                return False
            derived = hashlib.pbkdf2_hmac(
                algo, provided_password.encode("utf-8"), salt, iter_count, dklen=len(stored)
            )
            return hmac.compare_digest(derived, bytes(stored))

        elif version == 0x00:
            salt   = data[1:17]
            stored = data[17:]
            derived = hashlib.pbkdf2_hmac(
                "sha1", provided_password.encode("utf-8"), salt, 1000, dklen=len(stored)
            )
            return hmac.compare_digest(derived, bytes(stored))

    except Exception:
        pass
    return False


# ── Full password verification pipeline ──────────────────────────────────────

def verify_password(
    encrypted_password: str,
    stored_hash: str,
    is_client_encrypted: bool = True,
) -> bool:
    """
    Full TWAM verification pipeline.
    is_client_encrypted=True  → AES-decrypt first (Angular login flow)
    is_client_encrypted=False → use plain text directly (admin/testing)
    """
    try:
        plain        = _decrypt_client_password(encrypted_password) if is_client_encrypted else encrypted_password
        intermediate = generate_sha256_hash_with_salt(plain, _get_password_cipher())
        return verify_aspnet_identity_password(stored_hash, intermediate)
    except Exception:
        return False


# ── Create user password hash ─────────────────────────────────────────────────

def _aspnet_hash_password(password: str) -> str:
    salt       = os.urandom(16)
    iter_count = 10000
    subkey     = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iter_count, dklen=32)
    data = (
        bytes([0x01])
        + struct.pack(">I", 1)
        + struct.pack(">I", iter_count)
        + struct.pack(">I", len(salt))
        + salt + subkey
    )
    return base64.b64encode(data).decode("utf-8")


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(user_claims: dict, expires_minutes: int = EXPIRES_MINUTES) -> str:
    now    = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    payload = {
        **user_claims,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "nbf": int(now.timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode a regular login/access token — requires email_id claim."""
    return jwt.decode(
        token, SECRET_KEY, algorithms=[ALGORITHM],
        audience=AUDIENCE, issuer=ISSUER,
        options={"require": ["exp", "iss", "aud", "email_id"]},
    )


def decode_reset_token(token: str) -> dict:
    """Decode a password-reset token — only requires exp, iss, aud (no email_id)."""
    return jwt.decode(
        token, SECRET_KEY, algorithms=[ALGORITHM],
        audience=AUDIENCE, issuer=ISSUER,
        options={"require": ["exp", "iss", "aud"]},
    )
