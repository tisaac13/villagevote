"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum
from uuid import UUID
import re


# Enums
class JurisdictionLevel(str, Enum):
    FEDERAL = "federal"
    STATE = "state"
    COUNTY = "county"
    CITY = "city"


class MeasureStatus(str, Enum):
    INTRODUCED = "introduced"
    SCHEDULED = "scheduled"
    IN_COMMITTEE = "in_committee"
    PASSED = "passed"
    FAILED = "failed"
    TABLED = "tabled"
    WITHDRAWN = "withdrawn"
    UNKNOWN = "unknown"


class VoteValue(str, Enum):
    YES = "yes"
    NO = "no"


class OfficialVoteValue(str, Enum):
    YEA = "yea"
    NAY = "nay"
    ABSTAIN = "abstain"
    ABSENT = "absent"
    PRESENT = "present"
    NOT_VOTING = "not_voting"
    UNKNOWN = "unknown"


class FeedMode(str, Enum):
    UPCOMING = "upcoming"
    HISTORICAL = "historical"


class ContentType(str, Enum):
    HTML = "html"
    PDF = "pdf"
    API = "api"
    TEXT = "text"


# Address schemas
class Address(BaseModel):
    line1: str = Field(..., min_length=1, max_length=200)
    line2: Optional[str] = Field(None, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=2)
    postal_code: str = Field(..., min_length=5, max_length=10)
    country: str = Field(default="US", min_length=2, max_length=2)


class AddressPublic(BaseModel):
    """Public address info (no line1/line2)"""
    city: str
    state: str
    postal_code: str
    country: str


# Auth schemas
class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    birthday: date = Field(..., description="User's birthday (YYYY-MM-DD)")
    state: str = Field(..., min_length=2, max_length=2, description="US state code (e.g., AZ)")
    address: Optional[Address] = Field(None, description="Optional home address for city legislation")

    @field_validator('state')
    @classmethod
    def validate_state(cls, v):
        valid_states = [
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
        ]
        if v.upper() not in valid_states:
            raise ValueError('Invalid US state code')
        return v.upper()

    @field_validator('birthday')
    @classmethod
    def validate_birthday(cls, v):
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 13:
            raise ValueError('Must be at least 13 years old')
        if age > 120:
            raise ValueError('Invalid birthday')
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenRefresh(BaseModel):
    refresh_token: str


class Tokens(BaseModel):
    access_token: str
    refresh_token: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    state: str
    birthday: Optional[date] = None


class LocationResolution(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    divisions_resolved: bool


class SignupResponse(BaseModel):
    user: UserResponse
    tokens: Tokens
    location: LocationResolution


# Profile schemas
class Location(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None


class Preferences(BaseModel):
    topics: List[str] = Field(default_factory=list)
    notify_enabled: bool = True


class ProfileResponse(BaseModel):
    user: UserResponse
    address: Optional[AddressPublic] = None
    location: Location
    preferences: Preferences


class ProfileUpdateRequest(BaseModel):
    """Request to update user profile fields. All fields optional — only provided fields are updated."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    birthday: Optional[date] = None
    current_password: Optional[str] = Field(None, description="Required when changing email")

    @field_validator('first_name', 'last_name', mode='before')
    @classmethod
    def sanitize_name(cls, v):
        if v is None:
            return v
        # Strip HTML tags
        v = re.sub(r'<[^>]+>', '', v)
        # Strip leading/trailing whitespace
        v = v.strip()
        # Reject if empty after stripping
        if not v:
            raise ValueError('Name cannot be empty')
        # Only allow letters, spaces, hyphens, apostrophes, periods
        if not re.match(r"^[a-zA-Z\s\-'.]+$", v):
            raise ValueError('Name contains invalid characters')
        return v

    @field_validator('birthday')
    @classmethod
    def validate_birthday(cls, v):
        if v is None:
            return v
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 13:
            raise ValueError('Must be at least 13 years old')
        if age > 120:
            raise ValueError('Invalid birthday')
        return v


class ProfileUpdateResponse(BaseModel):
    updated: bool
    changed_fields: List[str]
    user: UserResponse


# Feed schemas
class Source(BaseModel):
    label: str
    url: str
    ctype: ContentType


class FeedCard(BaseModel):
    measure_id: UUID
    title: str
    level: JurisdictionLevel
    jurisdiction_name: str
    status: MeasureStatus
    scheduled_for: Optional[datetime] = None
    topic_tags: List[str]
    summary_short: Optional[str] = None
    sources: List[Source]
    user_vote: Optional[VoteValue] = None
    external_id: Optional[str] = None  # For identifying chamber (hr = House, s = Senate)


class FeedResponse(BaseModel):
    items: List[FeedCard]
    next_cursor: Optional[str] = None
    total_remaining: int = 0  # Total unvoted bills matching current filters (not just this batch)


# Measure detail schemas
class VoteEvent(BaseModel):
    id: UUID
    body: str
    scheduled_for: Optional[datetime] = None
    held_at: Optional[datetime] = None
    result: MeasureStatus


class StatusEvent(BaseModel):
    status: MeasureStatus
    effective_at: datetime


class MeasureInfo(BaseModel):
    id: UUID
    title: str
    level: JurisdictionLevel
    status: MeasureStatus
    introduced_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None
    summary_short: Optional[str] = None
    summary_long: Optional[str] = None


class UserVote(BaseModel):
    vote: VoteValue
    created_at: datetime


class MeasureDetail(BaseModel):
    measure: MeasureInfo
    sources: List[Source]
    timeline: List[StatusEvent]
    vote_events: List[VoteEvent]
    user_vote: Optional[UserVote] = None


# Voting schemas
class SwipeRequest(BaseModel):
    vote: VoteValue


class SwipeResponse(BaseModel):
    saved: bool
    user_vote: UserVote


# My Votes schemas
class MyVoteItem(BaseModel):
    measure_id: UUID
    title: str
    summary_short: Optional[str] = None
    level: JurisdictionLevel
    user_vote: str  # yes, no, or skip
    voted_at: datetime
    status: MeasureStatus
    scheduled_for: Optional[datetime] = None
    outcome: Optional[str] = None  # passed, failed, or None if still pending
    outcome_matches_user: Optional[bool] = None  # True if user voted same as outcome


class MyVotesResponse(BaseModel):
    items: List[MyVoteItem]
    next_cursor: Optional[str] = None


# Dashboard schemas
class DashboardStats(BaseModel):
    total_votes: int
    yea_votes: int
    nay_votes: int
    skipped: int
    measures_passed: int
    measures_failed: int
    measures_pending: int
    alignment_score: Optional[float] = None  # % of time user's vote matched outcome
    house_alignment: Optional[float] = None
    senate_alignment: Optional[float] = None
    congress_alignment: Optional[float] = None


class RecentActivity(BaseModel):
    measure_id: UUID
    title: str
    level: JurisdictionLevel
    user_vote: str
    voted_at: datetime
    outcome: Optional[str] = None


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_activity: List[RecentActivity]


# Matching schemas
class MatchSummary(BaseModel):
    measure_id: UUID
    title: str
    level: JurisdictionLevel
    user_vote: VoteValue
    outcome: MeasureStatus
    match_score: float
    computed_at: datetime


class MatchesResponse(BaseModel):
    items: List[MatchSummary]
    next_cursor: Optional[str] = None


class OfficialMatch(BaseModel):
    official_id: UUID
    name: str
    office: str
    official_vote: OfficialVoteValue
    matches_user: bool


class MatchBreakdown(BaseModel):
    officials: List[OfficialMatch]


class Match(BaseModel):
    match_score: float
    breakdown: MatchBreakdown


class MatchDetail(BaseModel):
    measure_id: UUID
    title: str
    level: JurisdictionLevel
    user_vote: VoteValue
    vote_event: VoteEvent
    match: Match


# Representatives schemas
class RepresentativeItem(BaseModel):
    id: UUID
    name: str
    office: str
    party: Optional[str] = None
    chamber: Optional[str] = None
    district_label: Optional[str] = None
    photo_url: Optional[str] = None
    alignment_percentage: Optional[float] = None
    votes_compared: int = 0


class RepresentativesResponse(BaseModel):
    representatives: List[RepresentativeItem]
    has_address: bool = True


class RepresentativeRefreshResponse(BaseModel):
    refreshed: bool
    count: int


# Admin schemas
class ConnectorConfig(BaseModel):
    """Base connector configuration"""
    base_url: Optional[str] = None
    poll_interval_minutes: Optional[int] = 15


class ConnectorCreate(BaseModel):
    name: str
    source: str
    enabled: bool = True
    config: dict


class Connector(BaseModel):
    id: UUID
    name: str
    source: str
    enabled: bool
    config: dict
    updated_at: datetime


class IngestionRunRequest(BaseModel):
    connector_name: str


class IngestionRunResponse(BaseModel):
    run_id: UUID
    status: str


# Error schema
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail
