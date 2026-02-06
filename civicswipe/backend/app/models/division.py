"""
SQLAlchemy models for divisions (jurisdictions)
"""
from sqlalchemy import Column, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Division(Base):
    """
    Geographic/political division (country, state, county, city, district)
    Uses Open Civic Data (OCD) IDs where possible
    """
    __tablename__ = "divisions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    division_type = Column(String, nullable=False)  # Enum: country, state, county, city, etc.
    ocd_id = Column(String, nullable=True, index=True)  # e.g., ocd-division/country:us/state:az/place:phoenix
    name = Column(String, nullable=False)
    level = Column(String, nullable=False)  # Enum: federal, state, county, city
    parent_id = Column(UUID(as_uuid=True), ForeignKey("divisions.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    parent = relationship("Division", remote_side=[id], backref="children")
    user_divisions = relationship("UserDivision", back_populates="division", cascade="all, delete-orphan")
    official_divisions = relationship("OfficialDivision", back_populates="division", cascade="all, delete-orphan")
    measures = relationship("Measure", back_populates="division")
    
    __table_args__ = (
        UniqueConstraint('division_type', 'ocd_id', name='uq_division_type_ocd_id'),
    )
    
    def __repr__(self):
        return f"<Division(id={self.id}, name={self.name}, type={self.division_type}, level={self.level})>"


class UserDivision(Base):
    """
    Maps users to their relevant divisions based on address
    A user in Phoenix, AZ would have divisions for:
    - country:us (federal)
    - state:az (state)
    - county:maricopa (county)
    - place:phoenix (city)
    - congressional district
    - state legislative districts
    - city council district
    """
    __tablename__ = "user_divisions"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    division_id = Column(UUID(as_uuid=True), ForeignKey("divisions.id", ondelete="CASCADE"), primary_key=True)
    derived_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="divisions")
    division = relationship("Division", back_populates="user_divisions")
    
    def __repr__(self):
        return f"<UserDivision(user_id={self.user_id}, division_id={self.division_id})>"
