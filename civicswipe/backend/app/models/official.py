"""
SQLAlchemy models for elected officials
"""
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Official(Base):
    """
    Elected official (Representative, Senator, Council Member, etc.)
    """
    __tablename__ = "officials"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String, unique=True, nullable=True, index=True)  # From external API (Open States, etc.)
    name = Column(String, nullable=False)
    office = Column(String, nullable=True)  # e.g., "U.S. Senator", "State Representative"
    party = Column(String, nullable=True)  # D, R, I, etc.
    chamber = Column(String, nullable=True)  # e.g., "us_senate", "az_house", "phoenix_council"
    district_label = Column(String, nullable=True)  # e.g., "CD-03", "LD-05", "District 7"
    photo_url = Column(String, nullable=True)  # Official portrait URL
    bioguide_id = Column(String, nullable=True, index=True)  # Congress bioguide ID
    lis_member_id = Column(String, nullable=True, index=True)  # Senate LIS member ID (e.g. "S354")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    divisions = relationship("OfficialDivision", back_populates="official", cascade="all, delete-orphan")
    user_officials = relationship("UserOfficial", back_populates="official", cascade="all, delete-orphan")
    votes = relationship("OfficialVote", back_populates="official", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Official(id={self.id}, name={self.name}, office={self.office})>"


class OfficialDivision(Base):
    """
    Maps officials to the divisions they represent
    A U.S. Representative represents one congressional district
    A State Senator represents one state senate district
    A Phoenix Council Member represents one city council district
    """
    __tablename__ = "official_divisions"
    
    official_id = Column(UUID(as_uuid=True), ForeignKey("officials.id", ondelete="CASCADE"), primary_key=True)
    division_id = Column(UUID(as_uuid=True), ForeignKey("divisions.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String, nullable=True)  # "member", "chair", etc.
    
    # Relationships
    official = relationship("Official", back_populates="divisions")
    division = relationship("Division", back_populates="official_divisions")
    
    def __repr__(self):
        return f"<OfficialDivision(official_id={self.official_id}, division_id={self.division_id})>"


class UserOfficial(Base):
    """
    Snapshot of which officials represent a user at a given time
    Useful for historical tracking when districts change
    """
    __tablename__ = "user_officials"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    official_id = Column(UUID(as_uuid=True), ForeignKey("officials.id", ondelete="CASCADE"), primary_key=True)
    active = Column(Boolean, nullable=False, default=True)
    derived_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="officials")
    official = relationship("Official", back_populates="user_officials")
    
    def __repr__(self):
        return f"<UserOfficial(user_id={self.user_id}, official_id={self.official_id}, active={self.active})>"
