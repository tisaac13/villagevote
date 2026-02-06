"""
Match engine service - compares user votes to official votes
"""
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import logging

from app.models import (
    UserVote, VoteEvent, OfficialVote, Official, 
    UserOfficial, MatchResult, Measure
)

logger = logging.getLogger(__name__)


class MatchEngine:
    """
    Computes match scores between user votes and official votes
    """
    
    async def compute_matches_for_measure(
        self,
        db: AsyncSession,
        measure_id: UUID
    ) -> int:
        """
        Compute matches for all users who voted on a specific measure
        Triggered when official vote results become available
        
        Args:
            db: Database session
            measure_id: UUID of the measure
        
        Returns:
            Number of match results computed
        """
        try:
            # Get measure
            measure = await db.get(Measure, measure_id)
            if not measure:
                logger.warning(f"Measure {measure_id} not found")
                return 0
            
            # Get vote events for this measure
            stmt = select(VoteEvent).where(VoteEvent.measure_id == measure_id)
            result = await db.execute(stmt)
            vote_events = result.scalars().all()
            
            if not vote_events:
                logger.info(f"No vote events found for measure {measure_id}")
                return 0
            
            # Get all users who voted on this measure
            stmt = select(UserVote).where(UserVote.measure_id == measure_id)
            result = await db.execute(stmt)
            user_votes = result.scalars().all()
            
            if not user_votes:
                logger.info(f"No user votes found for measure {measure_id}")
                return 0
            
            # Compute match for each user
            matches_computed = 0
            for user_vote in user_votes:
                match_result = await self._compute_user_match(
                    db,
                    user_vote,
                    vote_events,
                    measure.level
                )
                
                if match_result:
                    # Upsert match result
                    existing = await db.get(
                        MatchResult,
                        {"user_id": user_vote.user_id, "measure_id": measure_id}
                    )
                    
                    if existing:
                        existing.match_score = match_result["score"]
                        existing.breakdown = match_result["breakdown"]
                        existing.notes = match_result["notes"]
                    else:
                        new_match = MatchResult(
                            user_id=user_vote.user_id,
                            measure_id=measure_id,
                            match_score=match_result["score"],
                            breakdown=match_result["breakdown"],
                            notes=match_result["notes"]
                        )
                        db.add(new_match)
                    
                    matches_computed += 1
            
            await db.commit()
            logger.info(f"Computed {matches_computed} matches for measure {measure_id}")
            return matches_computed
            
        except Exception as e:
            logger.error(f"Match computation failed for measure {measure_id}: {e}")
            await db.rollback()
            return 0
    
    async def _compute_user_match(
        self,
        db: AsyncSession,
        user_vote: UserVote,
        vote_events: List[VoteEvent],
        measure_level: str
    ) -> Dict[str, Any]:
        """
        Compute match for a single user on a measure
        
        Args:
            db: Database session
            user_vote: User's vote on the measure
            vote_events: List of official vote events
            measure_level: Level of measure (federal/state/city)
        
        Returns:
            Dict with score, breakdown, and notes
        """
        # Get user's officials for this jurisdiction level
        stmt = select(Official).join(UserOfficial).where(
            UserOfficial.user_id == user_vote.user_id,
            UserOfficial.active == True
        )
        result = await db.execute(stmt)
        user_officials = result.scalars().all()
        
        if not user_officials:
            return {
                "score": 0.0,
                "breakdown": {"officials": []},
                "notes": "No officials found for user"
            }
        
        # Get official votes for relevant vote events
        vote_event_ids = [ve.id for ve in vote_events]
        stmt = select(OfficialVote).where(
            OfficialVote.vote_event_id.in_(vote_event_ids)
        )
        result = await db.execute(stmt)
        official_votes = result.scalars().all()
        
        # Create lookup: official_id -> vote
        official_vote_map = {ov.official_id: ov.vote for ov in official_votes}
        
        # Compare user vote to each official's vote
        matches = 0
        total = 0
        breakdown_officials = []
        
        user_vote_normalized = user_vote.vote.lower()  # "yes" or "no"
        
        for official in user_officials:
            official_vote_value = official_vote_map.get(official.id)
            
            if not official_vote_value or official_vote_value == "unknown":
                # Official didn't vote or vote not recorded
                breakdown_officials.append({
                    "official_id": str(official.id),
                    "name": official.name,
                    "office": official.office,
                    "official_vote": official_vote_value or "unknown",
                    "matches_user": False,
                    "note": "Vote not recorded"
                })
                continue
            
            # Normalize official vote
            official_vote_normalized = official_vote_value.lower()
            
            # Check for match
            is_match = False
            if user_vote_normalized == "yes" and official_vote_normalized == "yea":
                is_match = True
            elif user_vote_normalized == "no" and official_vote_normalized == "nay":
                is_match = True
            
            if is_match:
                matches += 1
            
            total += 1
            
            breakdown_officials.append({
                "official_id": str(official.id),
                "name": official.name,
                "office": official.office,
                "official_vote": official_vote_value,
                "matches_user": is_match
            })
        
        # Compute match score
        match_score = matches / total if total > 0 else 0.0
        
        return {
            "score": round(match_score, 3),
            "breakdown": {"officials": breakdown_officials},
            "notes": f"Matched {matches} of {total} officials"
        }


# Global instance
match_engine = MatchEngine()
