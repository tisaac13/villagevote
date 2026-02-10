"""
Security utilities for authentication and encryption
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import base64
import hashlib

from app.core.config import settings

# Password hashing - use bcrypt with truncation for long passwords
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

# Initialize Fernet for address encryption
def _derive_key_pbkdf2(key_bytes: bytes) -> bytes:
    """PBKDF2-based key derivation (preferred — new encryptions use this)."""
    salt = hashlib.sha256(b"civicswipe-address-enc-salt" + key_bytes[:8]).digest()[:16]
    derived = hashlib.pbkdf2_hmac("sha256", key_bytes, salt, iterations=600_000)
    return base64.urlsafe_b64encode(derived)


def _derive_key_legacy(key_bytes: bytes) -> bytes:
    """Legacy SHA256 key derivation (for decrypting pre-upgrade data)."""
    return base64.urlsafe_b64encode(hashlib.sha256(key_bytes).digest())


def get_encryption_key() -> bytes:
    """Get Fernet key using PBKDF2 derivation."""
    return _derive_key_pbkdf2(settings.ENCRYPTION_KEY.encode())


# Primary Fernet uses PBKDF2; legacy Fernet used for decryption fallback
fernet = Fernet(get_encryption_key())
_fernet_legacy = Fernet(_derive_key_legacy(settings.ENCRYPTION_KEY.encode()))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash (truncated to 72 bytes for bcrypt compatibility)"""
    return pwd_context.verify(plain_password[:72], hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password (truncated to 72 bytes for bcrypt compatibility)"""
    # Bcrypt has a 72-byte limit
    return pwd_context.hash(password[:72])


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        if payload.get("type") != token_type:
            return None
            
        return payload
    except JWTError:
        return None


def encrypt_address(address: str) -> bytes:
    """Encrypt address for storage (uses PBKDF2-derived key)."""
    return fernet.encrypt(address.encode())


def decrypt_address(encrypted_address: bytes) -> str:
    """
    Decrypt stored address.
    Tries PBKDF2-derived key first, falls back to legacy SHA256 key
    for data encrypted before the key-derivation upgrade.
    """
    try:
        return fernet.decrypt(encrypted_address).decode()
    except Exception:
        # Fallback to legacy key for pre-upgrade data
        return _fernet_legacy.decrypt(encrypted_address).decode()


def hash_address(address_line1: str, city: str, state: str, postal_code: str, country: str) -> str:
    """
    Create a stable hash of address components for deduplication
    Format: line1|city|state|zip|country (normalized and lowercased)
    """
    normalized = f"{address_line1}|{city}|{state}|{postal_code}|{country}".lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


# --- Token blacklist (Redis-backed) ---

async def blacklist_token(token: str, ttl_seconds: Optional[int] = None) -> None:
    """
    Add a token to the Redis blacklist.
    TTL defaults to REFRESH_TOKEN_EXPIRE_DAYS so entries auto-expire.
    """
    from app.core.cache import get_redis

    r = await get_redis()
    if r is None:
        return  # Graceful — if Redis is down we can't blacklist
    try:
        if ttl_seconds is None:
            ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        await r.setex(f"bl:{hashlib.sha256(token.encode()).hexdigest()}", ttl_seconds, "1")
    except Exception:
        pass  # Best-effort


async def is_token_blacklisted(token: str) -> bool:
    """Check if a token has been revoked."""
    from app.core.cache import get_redis

    r = await get_redis()
    if r is None:
        return False  # Fail open — same as rate limiter policy
    try:
        return await r.exists(f"bl:{hashlib.sha256(token.encode()).hexdigest()}") > 0
    except Exception:
        return False
