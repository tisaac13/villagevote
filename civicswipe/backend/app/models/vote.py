"""
SQLAlchemy models for votes (official roll calls and user votes)
"""
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, UniqueConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class VoteEvent(Base):
    """
    An official vote event (roll call, voice vote, etc.)
    """
    __tablename__ = "vote_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    measure_id = Column(UUID(as_uuid=True), ForeignKey("measures.id", ondelete="CASCADE"), nullable=False, index=True)
    
    body = Column(String, nullable=False)  # e.g., "U.S. House", "AZ Senate", "Phoenix City Council"
    external_id = Column(String, nullable=True, index=True)  # Roll call number, etc.
    
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    held_at = Column(DateTime(timezone=True), nullable=True, index=True)
    result = Column(String, nullable=False, default="unknown")  # Enum: passed, failed, tabled, unknown
    
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    measure = relationship("Measure", back_populates="vote_events")
    official_votes = relationship("OfficialVote", back_populates="vote_event", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<VoteEvent(id={self.id}, body={self.body}, result={self.result})>"


class OfficialVote(Base):
    """
    How an individual official voted on a specific vote event
    """
    __tablename__ = "official_votes"
    
    vote_event_id = Column(UUID(as_uuid=True), ForeignKey("vote_events.id", ondelete="CASCADE"), primary_key=True)
    official_id = Column(UUID(as_uuid=True), ForeignKey("officials.id", ondelete="CASCADE"), primary_key=True)
    vote = Column(String, nullable=False, default="unknown")  # Enum: yea, nay, abstain, absent, present, not_voting, unknown
    
    # Relationships
    vote_event = relationship("VoteEvent", back_populates="official_votes")
    official = relationship("Official", back_populates="votes")
    
    def __repr__(self):
        return f"<OfficialVote(vote_event_id={self.vote_event_id}, official_id={self.official_id}, vote={self.vote})>"


class UserVote(Base):
    """
    User's vote (swipe) on a measure
    """
    __tablename__ = "user_votes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    measure_id = Column(UUID(as_uuid=True), ForeignKey("measures.id", ondelete="CASCADE"), nullable=False, index=True)
    vote = Column(String, nullable=False)  # Enum: yes, no
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", back_populates="votes")
    measure = relationship("Measure", back_populates="user_votes")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'measure_id', name='uq_user_vote_user_measure'),
    )
    
    def __repr__(self):
        return f"<UserVote(id={self.id}, user_id={self.user_id}, measure_id={self.measure_id}, vote={self.vote})>"


class MatchResult(Base):
    """
    Comparison of user's vote vs their officials' votes
    """
    __tablename__ = "match_results"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    measure_id = Column(UUID(as_uuid=True), ForeignKey("measures.id", ondelete="CASCADE"), primary_key=True)
    
    computed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    match_score = Column(Numeric(4, 3), nullable=False, default=0.000)  # 0.000 to 1.000
    breakdown = Column(JSONB, nullable=False, default={})  # Per-official comparison details
    notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="match_results")
    measure = relationship("Measure", back_populates="match_results")
    
    def __repr__(self):
        return f"<MatchResult(user_id={self.user_id}, measure_id={self.measure_id}, match_score={self.match_score})>"
