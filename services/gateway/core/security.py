"""
Security & Cryptography Utilities.
Handles secure PBKDF2 password hashing, SHA-256 API key hashing, and JWT tokens.
"""

import os
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "mcp_gateway_super_secure_jwt_secret_key_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


# ============================================================================
# Password Hashing (PBKDF2-HMAC-SHA256 with 200,000 iterations)
# Standard, robust, zero native C-library dependencies.
# Format: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
# ============================================================================
def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with a unique random salt."""
    salt = secrets.token_bytes(16)
    iterations = 200_000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a stored PBKDF2 hash using constant-time comparison."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_derived = bytes.fromhex(parts[3])
        actual_derived = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual_derived, expected_derived)
    except Exception:
        return False


# ============================================================================
# API Key Generation and Hashing (SHA-256)
# Format of raw key: mcp_live_<32-byte-hex>
# Display prefix: mcp_live_<first 8 chars>...
# Stored hash: SHA-256 hex digest
# ============================================================================
def generate_api_key(prefix: str = "mcp_live_") -> tuple[str, str, str]:
    """
    Generates a cryptographically strong API key.
    Returns:
        (raw_key, key_hash, display_prefix)
    """
    random_bytes = secrets.token_hex(24)
    raw_key = f"{prefix}{random_bytes}"
    key_hash = hash_api_key(raw_key)
    display_prefix = f"{raw_key[:16]}...{raw_key[-4:]}"
    return raw_key, key_hash, display_prefix


def hash_api_key(raw_key: str) -> str:
    """Computes the SHA-256 hash of a raw API key for secure database storage."""
    return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()


# ============================================================================
# JWT Access Tokens for Dashboard REST Sessions
# ============================================================================
def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Encodes a JWT payload with expiration."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
