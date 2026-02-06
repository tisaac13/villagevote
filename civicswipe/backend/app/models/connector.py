"""
SQLAlchemy models for data connectors and ingestion pipeline
"""
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


# PostgreSQL enum types that match the database schema
source_system_enum = ENUM(
    'congress', 'govinfo', 'openstates', 'legiscan', 'legistar', 'custom',
    name='source_system', create_type=False
)

content_type_enum = ENUM(
    'html', 'pdf', 'api', 'text',
    name='content_type', create_type=False
)


class Connector(Base):
    """
    Configuration for a data source connector
    """
    __tablename__ = "connectors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True, index=True)  # e.g., "phoenix_legistar", "congress"
    source = Column(source_system_enum, nullable=False)  # Enum: congress, govinfo, openstates, legiscan, legistar, custom
    enabled = Column(Boolean, nullable=False, default=True)
    config = Column(JSONB, nullable=False, default={})  # Connector-specific configuration (URLs, keys, etc.)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    ingestion_runs = relationship("IngestionRun", back_populates="connector", cascade="all, delete-orphan")
    raw_artifacts = relationship("RawArtifact", back_populates="connector", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Connector(id={self.id}, name={self.name}, source={self.source}, enabled={self.enabled})>"


class IngestionRun(Base):
    """
    Record of an ingestion run (scheduled or manual)
    """
    __tablename__ = "ingestion_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connector_id = Column(UUID(as_uuid=True), ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default="running")  # running, succeeded, failed
    stats = Column(JSONB, nullable=False, default={})  # e.g., {"measures_fetched": 42, "new_measures": 10}
    error = Column(Text, nullable=True)
    
    # Relationships
    connector = relationship("Connector", back_populates="ingestion_runs")
    
    def __repr__(self):
        return f"<IngestionRun(id={self.id}, connector_id={self.connector_id}, status={self.status})>"


class RawArtifact(Base):
    """
    Raw data artifacts (HTML pages, PDFs, API responses) for audit/debugging
    References blob storage (S3/GCS) rather than storing content directly
    """
    __tablename__ = "raw_artifacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connector_id = Column(UUID(as_uuid=True), ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False, index=True)
    measure_id = Column(UUID(as_uuid=True), ForeignKey("measures.id", ondelete="SET NULL"), nullable=True, index=True)
    url = Column(Text, nullable=True)
    ctype = Column(content_type_enum, nullable=True)  # Enum: html, pdf, api, text
    fetched_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    blob_ref = Column(Text, nullable=False)  # S3/GCS key or local path
    sha256 = Column(String, nullable=True, index=True)  # For deduplication
    
    # Relationships
    connector = relationship("Connector", back_populates="raw_artifacts")
    
    def __repr__(self):
        return f"<RawArtifact(id={self.id}, url={self.url}, connector_id={self.connector_id})>"
