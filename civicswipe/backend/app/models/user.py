"""
SQLAlchemy models for users and profiles
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, ARRAY, LargeBinary, Enum, Numeric
from sqlalchemy.dialects.postgresql import UUID, BYTEA, ENUM
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum

from app.core.database import Base


# Define the auth_provider enum to match the database
class AuthProviderEnum(str, enum.Enum):
    password = "password"
    google = "google"
    apple = "apple"


# Create PostgreSQL ENUM type that references the existing database enum
auth_provider_enum = ENUM('password', 'google', 'apple', name='auth_provider', create_type=False)


class User(Base):
    """User account"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, unique=True, index=True, nullable=True)
    provider = Column(auth_provider_enum, nullable=False, default='password')
    password_hash = Column(Text, nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    birthday = Column(DateTime, nullable=True)
    state = Column(String(2), nullable=True, index=True)  # Required state for filtering legislation
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    divisions = relationship("UserDivision", back_populates="user", cascade="all, delete-orphan")
    officials = relationship("UserOfficial", back_populates="user", cascade="all, delete-orphan")
    votes = relationship("UserVote", back_populates="user", cascade="all, delete-orphan")
    match_results = relationship("MatchResult", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class UserProfile(Base):
    """User profile with address (encrypted)"""
    __tablename__ = "user_profile"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    
    # Encrypted address fields
    address_line1_enc = Column(BYTEA, nullable=False)
    address_line2_enc = Column(BYTEA, nullable=True)
    city = Column(String, nullable=False, index=True)
    state = Column(String, nullable=False, index=True)
    postal_code = Column(String, nullable=False, index=True)
    country = Column(String, nullable=False, default="US")
    
    # Geospatial (numeric(9,6) in database)
    lat = Column(Numeric(9, 6), nullable=True)
    lon = Column(Numeric(9, 6), nullable=True)
    
    # Address hash for deduplication
    address_hash = Column(String, nullable=False, unique=True, index=True)
    
    timezone = Column(String, nullable=False, default="America/Phoenix")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="profile")
    
    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, city={self.city}, state={self.state})>"


class UserPreferences(Base):
    """User preferences and settings"""
    __tablename__ = "user_preferences"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    topics = Column(ARRAY(String), nullable=False, default=[])
    notify_enabled = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="preferences")
    
    def __repr__(self):
        return f"<UserPreferences(user_id={self.user_id}, topics={self.topics})>"
