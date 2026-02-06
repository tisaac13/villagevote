"""
SQLAlchemy models for measures (bills, ordinances, agenda items)
"""
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Boolean, ARRAY, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


# PostgreSQL enum types that match the database schema
source_system_enum = ENUM(
    'congress', 'govinfo', 'openstates', 'legiscan', 'legistar', 'custom',
    name='source_system', create_type=False
)

jurisdiction_level_enum = ENUM(
    'federal', 'state', 'county', 'city',
    name='jurisdiction_level', create_type=False
)

measure_status_enum = ENUM(
    'introduced', 'scheduled', 'in_committee', 'passed', 'failed', 'tabled', 'withdrawn', 'unknown',
    name='measure_status', create_type=False
)

content_type_enum = ENUM(
    'html', 'pdf', 'api', 'text',
    name='content_type', create_type=False
)


class Measure(Base):
    """
    A legislative measure (bill, ordinance, resolution, agenda item)
    """
    __tablename__ = "measures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(source_system_enum, nullable=False)  # Enum: congress, openstates, legistar, etc.
    external_id = Column(String, nullable=False)  # ID from source system
    title = Column(Text, nullable=False)

    level = Column(jurisdiction_level_enum, nullable=False)  # Enum: federal, state, county, city
    division_id = Column(UUID(as_uuid=True), ForeignKey("divisions.id", ondelete="SET NULL"), nullable=True)

    status = Column(measure_status_enum, nullable=False, default="unknown")  # Enum: introduced, scheduled, passed, failed, etc.
    introduced_at = Column(DateTime(timezone=True), nullable=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=True, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    topic_tags = Column(ARRAY(String), nullable=False, default=[])
    summary_short = Column(Text, nullable=True)
    summary_long = Column(Text, nullable=True)
    
    canonical_key = Column(String, nullable=True, index=True)  # For deduplication
    
    # Relationships
    division = relationship("Division", back_populates="measures")
    sources = relationship("MeasureSource", back_populates="measure", cascade="all, delete-orphan")
    status_events = relationship("MeasureStatusEvent", back_populates="measure", cascade="all, delete-orphan")
    vote_events = relationship("VoteEvent", back_populates="measure", cascade="all, delete-orphan")
    user_votes = relationship("UserVote", back_populates="measure", cascade="all, delete-orphan")
    match_results = relationship("MatchResult", back_populates="measure", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('source', 'external_id', name='uq_measure_source_external_id'),
    )
    
    def __repr__(self):
        return f"<Measure(id={self.id}, title={self.title[:50]}..., level={self.level}, status={self.status})>"


class MeasureSource(Base):
    """
    Source links for a measure (official pages, PDFs, etc.)
    """
    __tablename__ = "measure_sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    measure_id = Column(UUID(as_uuid=True), ForeignKey("measures.id", ondelete="CASCADE"), nullable=False)
    label = Column(String, nullable=False)  # e.g., "Official page", "Agenda PDF"
    url = Column(Text, nullable=False)
    ctype = Column(content_type_enum, nullable=False, default="html")  # Enum: html, pdf, api, text
    is_primary = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    measure = relationship("Measure", back_populates="sources")
    
    def __repr__(self):
        return f"<MeasureSource(id={self.id}, label={self.label}, measure_id={self.measure_id})>"


class MeasureStatusEvent(Base):
    """
    Timeline of status changes for a measure
    """
    __tablename__ = "measure_status_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    measure_id = Column(UUID(as_uuid=True), ForeignKey("measures.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(measure_status_enum, nullable=False)  # Enum: same as measure.status
    effective_at = Column(DateTime(timezone=True), nullable=False, index=True)
    source_url = Column(Text, nullable=True)
    raw_ref = Column(Text, nullable=True)  # Reference to blob storage (S3/GCS) if needed
    
    # Relationships
    measure = relationship("Measure", back_populates="status_events")
    
    def __repr__(self):
        return f"<MeasureStatusEvent(id={self.id}, measure_id={self.measure_id}, status={self.status})>"
