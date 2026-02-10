"""
Roll Call Vote Ingestion Service

Fetches and stores roll call votes from:
- House Clerk XML (clerk.house.gov)
- Senate XML (senate.gov)

Populates VoteEvent and OfficialVote tables to enable
alignment computation between users and their representatives.
"""
import asyncio
import re
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Measure, Official, VoteEvent, OfficialVote

logger = logging.getLogger(__name__)

# Vote value mappings from XML to our enum
VOTE_MAP = {
    "yea": "yea",
    "aye": "yea",
    "yes": "yea",
    "nay": "nay",
    "no": "nay",
    "present": "present",
    "not voting": "not_voting",
    "not_voting": "not_voting",
}


class RollCallVoteService:
    """
    Fetches and stores roll call votes from House Clerk XML and Senate XML.
    Populates VoteEvent + OfficialVote tables for alignment computation.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    # ──────────────────── House Roll Call Votes ────────────────────

    async def ingest_house_votes(self, congress: int = 119, session: int = 1) -> Dict[str, Any]:
        """
        Fetch all House roll call votes for a congress/session.

        House Clerk XML: https://clerk.house.gov/evs/{year}/roll{NNN}.xml
        The `legislator` element has a `name-id` attribute = bioguide_id.
        """
        stats = {"votes_processed": 0, "official_votes_created": 0, "matched_measures": 0, "errors": 0}
        year = 2025 if session == 1 else 2026

        # Build bioguide -> official_id lookup
        bioguide_map = await self._build_bioguide_map()

        # Iterate roll call numbers starting from 1
        roll_num = 1
        consecutive_404s = 0
        client = await self._get_client()

        while consecutive_404s < 5:  # Stop after 5 consecutive missing rolls
            url = f"https://clerk.house.gov/evs/{year}/roll{roll_num:03d}.xml"
            try:
                response = await client.get(url)
                if response.status_code == 404:
                    consecutive_404s += 1
                    roll_num += 1
                    continue
                response.raise_for_status()
                consecutive_404s = 0

                xml_text = response.text
                await self._process_house_vote_xml(
                    xml_text, congress, session, roll_num, bioguide_map, stats
                )
                stats["votes_processed"] += 1

            except httpx.HTTPStatusError:
                consecutive_404s += 1
            except Exception as e:
                logger.error(f"Error processing House roll {roll_num}: {e}")
                stats["errors"] += 1

            roll_num += 1
            await asyncio.sleep(0.1)  # Be respectful

        logger.info(f"House vote ingestion complete: {stats}")
        return stats

    async def _process_house_vote_xml(
        self, xml_text: str, congress: int, session: int, roll_num: int,
        bioguide_map: Dict[str, UUID], stats: Dict
    ):
        """Parse a single House roll call XML and create VoteEvent + OfficialVotes."""
        root = ET.fromstring(xml_text)

        # Check if this vote event already exists (idempotent)
        external_id = f"house:{congress}:{session}:{roll_num}"
        existing = await self.db.execute(
            select(VoteEvent).where(VoteEvent.external_id == external_id)
        )
        if existing.scalar_one_or_none():
            return  # Already ingested

        # Extract bill reference to match to a Measure
        legis_num_el = root.find(".//legis-num")
        measure_id = None
        if legis_num_el is not None and legis_num_el.text:
            measure_id = await self._match_bill_to_measure(legis_num_el.text, congress)
            if measure_id:
                stats["matched_measures"] += 1

        # Skip votes we can't link to a measure (procedural motions, unmatched bills)
        if not measure_id:
            return

        # Extract vote date
        action_date_el = root.find(".//action-date")
        held_at = None
        if action_date_el is not None:
            date_str = action_date_el.get("date", "")
            if date_str:
                try:
                    from datetime import datetime
                    held_at = datetime.strptime(date_str, "%d-%b-%Y")
                except (ValueError, TypeError):
                    pass

        # Determine result
        result_el = root.find(".//vote-result")
        result = "unknown"
        if result_el is not None and result_el.text:
            result_text = result_el.text.lower()
            if "passed" in result_text or "agreed" in result_text:
                result = "passed"
            elif "failed" in result_text or "rejected" in result_text:
                result = "failed"

        # Create VoteEvent
        vote_event = VoteEvent(
            id=uuid4(),
            measure_id=measure_id,
            body="U.S. House",
            external_id=external_id,
            held_at=held_at,
            result=result,
        )
        self.db.add(vote_event)
        await self.db.flush()

        # Parse individual votes
        for recorded_vote in root.findall(".//recorded-vote"):
            legislator = recorded_vote.find("legislator")
            if legislator is None:
                continue

            bioguide_id = legislator.get("name-id", "")
            vote_text = (recorded_vote.find("vote").text or "").strip().lower() if recorded_vote.find("vote") is not None else ""

            official_id = bioguide_map.get(bioguide_id)
            if not official_id:
                continue  # Unknown legislator

            mapped_vote = VOTE_MAP.get(vote_text, "unknown")

            official_vote = OfficialVote(
                vote_event_id=vote_event.id,
                official_id=official_id,
                vote=mapped_vote,
            )
            self.db.add(official_vote)
            stats["official_votes_created"] += 1

        await self.db.flush()

    # ──────────────────── Senate Roll Call Votes ────────────────────

    async def ingest_senate_votes(self, congress: int = 119, session: int = 1) -> Dict[str, Any]:
        """
        Fetch all Senate roll call votes for a congress/session.

        Senate XML: https://www.senate.gov/legislative/LIS/roll_call_votes/
            vote{congress}{session}/vote_{congress}_{session}_{NNNNN}.xml
        Uses lis_member_id for senator matching.
        """
        stats = {"votes_processed": 0, "official_votes_created": 0, "matched_measures": 0, "errors": 0}

        # Build lis_member_id -> official_id lookup (+ fallback name+state map)
        lis_map, name_state_map = await self._build_senate_maps()

        client = await self._get_client()
        vote_num = 1
        consecutive_404s = 0

        while consecutive_404s < 5:
            url = (
                f"https://www.senate.gov/legislative/LIS/roll_call_votes/"
                f"vote{congress}{session}/vote_{congress}_{session}_{vote_num:05d}.xml"
            )
            try:
                response = await client.get(url)
                if response.status_code == 404:
                    consecutive_404s += 1
                    vote_num += 1
                    continue
                response.raise_for_status()
                consecutive_404s = 0

                xml_text = response.text
                await self._process_senate_vote_xml(
                    xml_text, congress, session, vote_num, lis_map, name_state_map, stats
                )
                stats["votes_processed"] += 1

            except httpx.HTTPStatusError:
                consecutive_404s += 1
            except Exception as e:
                logger.error(f"Error processing Senate vote {vote_num}: {e}")
                stats["errors"] += 1

            vote_num += 1
            await asyncio.sleep(0.1)

        logger.info(f"Senate vote ingestion complete: {stats}")
        return stats

    async def _process_senate_vote_xml(
        self, xml_text: str, congress: int, session: int, vote_num: int,
        lis_map: Dict[str, UUID], name_state_map: Dict[tuple, "Official"], stats: Dict
    ):
        """Parse a single Senate roll call XML and create VoteEvent + OfficialVotes."""
        root = ET.fromstring(xml_text)

        external_id = f"senate:{congress}:{session}:{vote_num}"
        existing = await self.db.execute(
            select(VoteEvent).where(VoteEvent.external_id == external_id)
        )
        if existing.scalar_one_or_none():
            return  # Already ingested

        # Extract document (bill reference)
        doc_el = root.find(".//document/document_name")
        measure_id = None
        if doc_el is not None and doc_el.text:
            measure_id = await self._match_bill_to_measure(doc_el.text, congress)
            if measure_id:
                stats["matched_measures"] += 1

        # Skip votes we can't link to a measure (nominations, procedural, unmatched)
        if not measure_id:
            return

        # Extract vote date
        vote_date_el = root.find(".//vote_date")
        held_at = None
        if vote_date_el is not None and vote_date_el.text:
            try:
                from datetime import datetime
                # Senate dates: "February 04, 2025, 05:36 PM" or similar
                date_str = vote_date_el.text.strip()
                # Try common formats
                for fmt in ["%B %d, %Y, %I:%M %p", "%B %d, %Y"]:
                    try:
                        held_at = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

        # Determine result
        result_el = root.find(".//vote_result")
        result = "unknown"
        if result_el is not None and result_el.text:
            result_text = result_el.text.lower()
            if "agreed" in result_text or "passed" in result_text or "confirmed" in result_text:
                result = "passed"
            elif "rejected" in result_text or "failed" in result_text:
                result = "failed"

        vote_event = VoteEvent(
            id=uuid4(),
            measure_id=measure_id,
            body="U.S. Senate",
            external_id=external_id,
            held_at=held_at,
            result=result,
        )
        self.db.add(vote_event)
        await self.db.flush()

        # Parse member votes
        for member in root.findall(".//members/member"):
            lis_id_el = member.find("lis_member_id")
            lis_id = lis_id_el.text.strip() if lis_id_el is not None and lis_id_el.text else ""

            vote_el = member.find("vote_cast")
            vote_text = (vote_el.text or "").strip().lower() if vote_el is not None else ""

            # Try lis_member_id lookup first
            official_id = lis_map.get(lis_id)

            # Fallback: match by last_name + state
            if not official_id:
                last_name_el = member.find("last_name")
                state_el = member.find("state")
                if last_name_el is not None and state_el is not None:
                    last_name = (last_name_el.text or "").strip().lower()
                    state = (state_el.text or "").strip().upper()
                    key = (last_name, state)
                    matched_official = name_state_map.get(key)
                    if matched_official:
                        official_id = matched_official.id
                        # Store lis_member_id for future lookups
                        if lis_id and not matched_official.lis_member_id:
                            matched_official.lis_member_id = lis_id

            if not official_id:
                continue

            mapped_vote = VOTE_MAP.get(vote_text, "unknown")

            official_vote = OfficialVote(
                vote_event_id=vote_event.id,
                official_id=official_id,
                vote=mapped_vote,
            )
            self.db.add(official_vote)
            stats["official_votes_created"] += 1

        await self.db.flush()

    # ──────────────────── Matching Helpers ────────────────────

    async def _match_bill_to_measure(self, bill_ref: str, congress: int) -> Optional[UUID]:
        """
        Match a bill reference (e.g., 'H.R. 1228', 'S. 5', 'H R 1228') to a Measure.
        Uses canonical_key: us:congress:{congress}:{bill_type}:{bill_number}
        """
        # Normalize bill reference
        ref = bill_ref.strip().upper()

        # Parse common formats: "H.R. 1228", "H R 1228", "S. 5", "S 5", "H.J.Res. 12"
        patterns = [
            (r"H\.?\s*R\.?\s*(\d+)", "hr"),
            (r"S\.?\s*(\d+)", "s"),
            (r"H\.?\s*J\.?\s*RES\.?\s*(\d+)", "hjres"),
            (r"S\.?\s*J\.?\s*RES\.?\s*(\d+)", "sjres"),
            (r"H\.?\s*CON\.?\s*RES\.?\s*(\d+)", "hconres"),
            (r"S\.?\s*CON\.?\s*RES\.?\s*(\d+)", "sconres"),
            (r"H\.?\s*RES\.?\s*(\d+)", "hres"),
            (r"S\.?\s*RES\.?\s*(\d+)", "sres"),
        ]

        for pattern, bill_type in patterns:
            match = re.search(pattern, ref, re.IGNORECASE)
            if match:
                bill_number = match.group(1)
                canonical_key = f"us:congress:{congress}:{bill_type}:{bill_number}"
                result = await self.db.execute(
                    select(Measure.id).where(Measure.canonical_key == canonical_key)
                )
                measure_id = result.scalar_one_or_none()
                if measure_id:
                    return measure_id
                break

        return None

    async def _build_bioguide_map(self) -> Dict[str, UUID]:
        """Build mapping from bioguide_id -> official.id for House vote matching."""
        result = await self.db.execute(
            select(Official.id, Official.bioguide_id).where(
                Official.bioguide_id.isnot(None),
                Official.bioguide_id != "",
            )
        )
        return {row[1]: row[0] for row in result.fetchall()}

    async def _build_senate_maps(self):
        """
        Build two maps for Senate vote matching:
        1. lis_member_id -> official.id (direct lookup)
        2. (last_name_lower, state_upper) -> Official (fallback)
        """
        result = await self.db.execute(
            select(Official).where(Official.chamber == "us_senate")
        )
        senators = result.scalars().all()

        lis_map: Dict[str, UUID] = {}
        name_state_map: Dict[tuple, Official] = {}

        for s in senators:
            if s.lis_member_id:
                lis_map[s.lis_member_id] = s.id

            # Parse last name from "LastName, FirstName" format
            name = s.name or ""
            if "," in name:
                last_name = name.split(",")[0].strip().lower()
            else:
                parts = name.split()
                last_name = parts[-1].lower() if parts else ""

            # district_label for senators is the state code (e.g. "CA")
            state = (s.district_label or "").upper()
            if last_name and state:
                name_state_map[(last_name, state)] = s

        return lis_map, name_state_map
