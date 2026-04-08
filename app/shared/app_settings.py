"""
app/shared/app_settings.py
───────────────────────────
Runtime key-value settings loaded from the twam.AppSettings DB table.

AppSettings MODEL stays in app/common/models.py exactly as it is.
This file is just a helper that reads rows from that table into a
fast in-process cache so every request can call get_setting() without
hitting the DB each time.

Startup sequence (main.py lifespan):
  1. seed_defaults(db)  → INSERT missing rows (skips existing rows)
  2. load_settings(db)  → fills in-process cache from DB

Then anywhere in the app:
  from app.shared.app_settings import get_setting
  cipher = get_setting("password_cipher")

Keys managed here (all stored in twam."AppSettings"):
  oauth_client_id      – OAuth2 client_id accepted by /connect/token
  oauth_client_secret  – OAuth2 client_secret accepted by /connect/token
  password_cipher      – TWAM server-side password hash salt
  client_encrypt_key   – AES-CBC key Angular uses to encrypt passwords
  ekart_webhook_secret – HMAC secret for verifying Ekart webhook calls
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

# ── In-process cache (populated once at startup by load_settings) ──────────
_cache: dict[str, str] = {}

# ── Built-in defaults ──────────────────────────────────────────────────────
# These match the values that were previously hardcoded in source files.
# They are inserted by seed_defaults() the first time the server boots so
# existing password hashes remain valid.
# key → (default_value, description)
_DEFAULTS: dict[str, tuple[str, str]] = {
    "oauth_client_id":      ("twam-web-portal",         "OAuth2 client_id for /connect/token"),
    "oauth_client_secret":  ("twamsecret",               "OAuth2 client_secret for /connect/token"),
    "password_cipher":      ("TWAM@D&E*V@Tr@d@1#2$30%", "TWAM server-side password hash cipher"),
    "client_encrypt_key":   ("8080808080808080",         "AES-CBC key Angular uses to pre-encrypt passwords"),
    "ekart_webhook_secret": ("",                         "HMAC-SHA256 secret for Ekart webhook (blank = dev mode)"),
}


# ── Public API ─────────────────────────────────────────────────────────────

def seed_defaults(db) -> None:
    """
    Insert missing AppSettings rows with their default values.
    Skips rows that already exist — safe to run every startup.
    No column-name changes: uses exact Python attribute names from
    app/common/models.py AppSettings class.
    """
    # Import from common.models where AppSettings actually lives
    from app.common.models import AppSettings

    now = datetime.now(timezone.utc)
    for key, (default_val, description) in _DEFAULTS.items():
        existing = (
            db.query(AppSettings)
            .filter(AppSettings.key == key, AppSettings.deletedInd == False)
            .first()
        )
        if existing is None:
            db.add(AppSettings(
                key          = key,
                value        = default_val,
                description  = description,
                isActive     = True,
                createdDate  = now,
                modifiedDate = now,
                deletedInd   = False,
            ))
    db.commit()


def load_settings(db) -> None:
    """
    Read all active AppSettings rows into the in-process cache.
    Call after seed_defaults() in main.py lifespan.
    """
    from app.common.models import AppSettings

    rows = (
        db.query(AppSettings)
        .filter(AppSettings.isActive == True, AppSettings.deletedInd == False)
        .all()
    )
    for row in rows:
        if row.key and row.value is not None:
            _cache[row.key] = row.value

    # Fill any gaps from built-in defaults
    for key, (default_val, _) in _DEFAULTS.items():
        if key not in _cache:
            _cache[key] = default_val


def get_setting(key: str, default: Optional[str] = None) -> str:
    """
    Return cached value for *key*.
    Falls back to built-in default for known keys, then to *default*.
    Safe to call before load_settings() — returns built-in defaults.
    """
    if key in _cache:
        return _cache[key]
    if key in _DEFAULTS:
        return _DEFAULTS[key][0]
    return default or ""


def reload_settings(db) -> None:
    """
    Clear and repopulate the cache.
    Call from an admin endpoint after updating a setting via the API.
    """
    _cache.clear()
    load_settings(db)