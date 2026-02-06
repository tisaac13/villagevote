"""
AI Summarization Service

Uses Anthropic's Claude API to generate neutral, factual summaries of legislative measures.
Summaries are designed to help citizens understand what bills and ordinances actually do
without advocacy language or political spin.
"""
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.config import settings
from app.models import Measure

logger = logging.getLogger(__name__)


class SummarizationService:
    """
    Service for generating AI summaries of legislative measures.
    """

    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY is not configured - summarization disabled")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def _build_summary_prompt(self, title: str, full_text: Optional[str] = None) -> str:
        """
        Build a prompt for generating a plain-language, impact-focused summary.

        Args:
            title: The title of the measure
            full_text: Optional full text of the measure

        Returns:
            Prompt string for the AI model
        """
        context = f"Title: {title}"
        if full_text:
            # Limit text to avoid token limits
            truncated_text = full_text[:8000] if len(full_text) > 8000 else full_text
            context += f"\n\nFull Text:\n{truncated_text}"

        prompt = f"""You are explaining a federal law/bill to your neighbor who didn't go to college. Your job is to help regular people understand what this bill would do if passed.

Summarize this federal legislative measure in 2-3 sentences using PLAIN ENGLISH. Follow these rules strictly:

LANGUAGE RULES:
- Write at an 8th grade reading level
- NO legal jargon (don't say "appropriates", "pursuant to", "whereas", "thereof")
- NO political jargon (don't say "bipartisan", "stakeholders", "fiscal responsibility")
- NO bureaucratic language (don't say "allocate resources", "implement provisions")
- Use everyday words: "spend" not "appropriate", "rules" not "regulations", "allow" not "authorize"

CONTENT RULES - Based on the bill TITLE, explain:
- What would this bill DO if passed?
- Who does it affect? (veterans, businesses, students, etc.)
- What problem is it trying to solve?

IMPORTANT: This is a FEDERAL bill in the U.S. Congress (House or Senate), NOT a local city ordinance.
- Do NOT make up specific dollar amounts unless they're in the title
- Do NOT invent local details like street names or city budgets
- Focus on the NATIONAL policy impact
- If the title doesn't give enough info, provide a reasonable explanation based on the bill's name

EXAMPLES OF GOOD SUMMARIES FOR FEDERAL BILLS:
- "This bill would require Medicare to cover hearing aids for seniors, making them more affordable for millions of Americans."
- "This bill would increase penalties for companies that pollute waterways, giving the EPA more power to enforce clean water rules."
- "This bill would make it easier for veterans to get mental health care by expanding VA telehealth services."
- "This bill would require social media companies to verify users' ages before allowing them to create accounts."
- "This bill would provide tax credits to businesses that hire workers in economically struggling areas."

BAD (making things up): "The city will spend $5 million on a new park downtown."
GOOD (based on title): "This bill aims to protect national parks by limiting commercial development near park boundaries."

{context}

IMPORTANT: Start directly with what the bill does. Do NOT include any intro phrases like "This bill" repeatedly. Just state what it would do and who it affects.

Summary:"""

        return prompt

    def _build_topic_prompt(self, title: str, summary: str) -> str:
        """
        Build a prompt for extracting topic tags.

        Args:
            title: The title of the measure
            summary: The summary of the measure

        Returns:
            Prompt string for topic extraction
        """
        prompt = f"""You are a legislative classifier. Given the following bill title and summary, provide 2-5 topic tags that describe the main subjects.

Title: {title}
Summary: {summary}

Choose from these categories when applicable:
- Education
- Healthcare
- Environment
- Transportation
- Housing
- Public Safety
- Taxes
- Budget
- Civil Rights
- Labor
- Business
- Technology
- Agriculture
- Veterans
- Immigration
- Elections
- Judiciary
- Local Government

Return ONLY a comma-separated list of relevant topics (e.g., "Healthcare, Budget, Public Safety"). No other text."""

        return prompt

    async def summarize_measure(
        self,
        title: str,
        full_text: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a summary for a legislative measure.

        Args:
            title: The title of the measure
            full_text: Optional full text of the measure

        Returns:
            Generated summary or None if summarization fails
        """
        if not self.client:
            logger.warning("Summarization skipped - API client not configured")
            return None

        try:
            prompt = self._build_summary_prompt(title, full_text)

            message = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Fast and cost-effective
                max_tokens=300,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            summary = message.content[0].text.strip()
            return summary

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return None

    async def extract_topics(
        self,
        title: str,
        summary: str
    ) -> List[str]:
        """
        Extract topic tags from a measure title and summary.

        Args:
            title: The title of the measure
            summary: The summary of the measure

        Returns:
            List of topic tags
        """
        if not self.client:
            return []

        try:
            prompt = self._build_topic_prompt(title, summary)

            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=100,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response = message.content[0].text.strip()

            # Parse comma-separated topics
            topics = [t.strip() for t in response.split(",")]
            topics = [t for t in topics if t and len(t) < 50]  # Filter valid topics

            return topics[:5]  # Limit to 5 topics

        except Exception as e:
            logger.error(f"Topic extraction failed: {e}")
            return []

    async def summarize_and_update(
        self,
        db: AsyncSession,
        measure_id: UUID,
        full_text: Optional[str] = None
    ) -> bool:
        """
        Summarize a measure and update it in the database.

        Args:
            db: Database session
            measure_id: ID of the measure to summarize
            full_text: Optional full text of the measure

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the measure
            result = await db.execute(
                select(Measure).where(Measure.id == measure_id)
            )
            measure = result.scalar_one_or_none()

            if not measure:
                logger.error(f"Measure not found: {measure_id}")
                return False

            # Skip if already summarized
            if measure.summary_short:
                logger.info(f"Measure already has summary: {measure_id}")
                return True

            # Generate summary
            summary = await self.summarize_measure(measure.title, full_text)

            if not summary:
                logger.warning(f"Could not generate summary for: {measure_id}")
                return False

            # Extract topics if needed
            new_topics = []
            if not measure.topic_tags or len(measure.topic_tags) == 0:
                new_topics = await self.extract_topics(measure.title, summary)

            # Update measure
            measure.summary_short = summary
            if new_topics:
                measure.topic_tags = new_topics

            await db.commit()
            logger.info(f"Updated summary for measure: {measure_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to summarize measure {measure_id}: {e}")
            await db.rollback()
            return False

    async def batch_summarize(
        self,
        db: AsyncSession,
        limit: int = 10
    ) -> Dict[str, int]:
        """
        Batch summarize measures that don't have summaries.

        Args:
            db: Database session
            limit: Maximum number of measures to summarize

        Returns:
            Statistics about the summarization run
        """
        stats = {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
        }

        try:
            # Get measures without summaries
            result = await db.execute(
                select(Measure)
                .where(Measure.summary_short.is_(None))
                .limit(limit)
            )
            measures = result.scalars().all()

            for measure in measures:
                stats["processed"] += 1

                # Skip procedural items
                if self._is_procedural(measure.title):
                    measure.summary_short = "Procedural item."
                    stats["skipped"] += 1
                    continue

                # Generate summary
                summary = await self.summarize_measure(measure.title)

                if summary:
                    measure.summary_short = summary

                    # Extract topics if needed
                    if not measure.topic_tags or len(measure.topic_tags) == 0:
                        topics = await self.extract_topics(measure.title, summary)
                        if topics:
                            measure.topic_tags = topics

                    stats["success"] += 1
                else:
                    stats["failed"] += 1

            await db.commit()
            logger.info(f"Batch summarization completed: {stats}")

        except Exception as e:
            logger.error(f"Batch summarization failed: {e}")
            await db.rollback()
            raise

        return stats

    def _is_procedural(self, title: str) -> bool:
        """Check if a measure title indicates a procedural item."""
        procedural_keywords = [
            "roll call",
            "call to order",
            "adjournment",
            "adjourns",
            "quorum",
            "minutes of meeting",
            "pledge of allegiance",
            "invocation",
            "moment of silence",
            "recess",
        ]

        title_lower = title.lower()
        return any(keyword in title_lower for keyword in procedural_keywords)


# Global instance
summarization_service = SummarizationService()


async def summarize_measures(db: AsyncSession, limit: int = 10) -> Dict[str, int]:
    """
    Convenience function to batch summarize measures.

    Usage:
        from app.services.summarizer import summarize_measures
        stats = await summarize_measures(db, limit=20)
    """
    return await summarization_service.batch_summarize(db, limit=limit)


async def regenerate_all_summaries(db: AsyncSession, limit: int = 100) -> Dict[str, int]:
    """
    Regenerate ALL summaries with the updated prompt (even existing ones).
    Use this when the prompt has been improved.

    Usage:
        from app.services.summarizer import regenerate_all_summaries
        stats = await regenerate_all_summaries(db, limit=200)
    """
    stats = {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
    }

    try:
        # Get ALL measures (not just ones without summaries)
        result = await db.execute(
            select(Measure).limit(limit)
        )
        measures = result.scalars().all()

        for measure in measures:
            stats["processed"] += 1

            # Skip procedural items
            if summarization_service._is_procedural(measure.title):
                measure.summary_short = "Procedural item - no action needed from voters."
                stats["skipped"] += 1
                continue

            # Generate new summary
            summary = await summarization_service.summarize_measure(measure.title)

            if summary:
                measure.summary_short = summary

                # Re-extract topics too
                topics = await summarization_service.extract_topics(measure.title, summary)
                if topics:
                    measure.topic_tags = topics

                stats["success"] += 1
                logger.info(f"Regenerated summary for: {measure.title[:50]}...")
            else:
                stats["failed"] += 1

        await db.commit()
        logger.info(f"Summary regeneration completed: {stats}")

    except Exception as e:
        logger.error(f"Summary regeneration failed: {e}")
        await db.rollback()
        raise

    return stats
