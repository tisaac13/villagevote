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
def get_encryption_key() -> bytes:
    """Get or generate encryption key"""
    key = settings.ENCRYPTION_KEY.encode()
    # Ensure key is 32 bytes for Fernet
    return base64.urlsafe_b64encode(hashlib.sha256(key).digest())

fernet = Fernet(get_encryption_key())


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
    """Encrypt address for storage"""
    return fernet.encrypt(address.encode())


def decrypt_address(encrypted_address: bytes) -> str:
    """Decrypt stored address"""
    return fernet.decrypt(encrypted_address).decode()


def hash_address(address_line1: str, city: str, state: str, postal_code: str, country: str) -> str:
    """
    Create a stable hash of address components for deduplication
    Format: line1|city|state|zip|country (normalized and lowercased)
    """
    normalized = f"{address_line1}|{city}|{state}|{postal_code}|{country}".lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()
