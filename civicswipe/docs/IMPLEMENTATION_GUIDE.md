# Implementation Guide: Next Steps

This guide outlines the specific tasks needed to complete the RepCheck MVP for Phoenix, Arizona.

## 🎯 Current Status

✅ **Completed:**
- Database schema (PostgreSQL)
- API specification (OpenAPI)
- Project structure
- Core configuration
- Security utilities (JWT, encryption)
- Pydantic schemas
- Docker setup

⏳ **In Progress:**
- Backend API endpoints (stubs created)

---

## 📋 Priority Tasks

### 1. Complete Authentication Endpoints (Week 1)

**File:** `backend/app/api/v1/endpoints/auth.py`

**Tasks:**
- [ ] Implement user creation in database
- [ ] Add email/phone uniqueness validation
- [ ] Implement password verification
- [ ] Add rate limiting for login attempts
- [ ] Create SQLAlchemy models for `users` table

**Dependencies:**
- SQLAlchemy models
- Database connection tested

---

### 2. Implement Address Validation & Geocoding (Week 1-2)

**New File:** `backend/app/services/geocoding.py`

**Tasks:**
- [ ] Integrate Census Geocoder API
- [ ] Implement address normalization
- [ ] Create geocoding service:
  ```python
  async def geocode_address(address: Address) -> tuple[float, float]:
      """Returns (lat, lon)"""
  ```
- [ ] Handle geocoding failures gracefully
- [ ] Cache geocoding results

**Alternative:** Use Google Maps Geocoding API (requires API key)

---

### 3. Implement Division Resolution (Week 2)

**New File:** `backend/app/services/division_resolver.py`

**Tasks:**
- [ ] Map coordinates to divisions (federal/state/city)
- [ ] Resolve congressional district
- [ ] Resolve AZ state legislative districts
- [ ] Resolve Phoenix city council district
- [ ] Create function:
  ```python
  async def resolve_divisions(lat: float, lon: float) -> List[Division]:
      """Returns all applicable divisions"""
  ```
- [ ] Populate `divisions` table with Phoenix-specific data
- [ ] Link user to divisions in `user_divisions` table

**Data Sources:**
- Census TIGER/Line shapefiles
- Google Civic Information API
- Manual Phoenix council district boundaries

---

### 4. Implement Official Resolution (Week 2)

**New File:** `backend/app/services/official_resolver.py`

**Tasks:**
- [ ] Fetch current officials for divisions
- [ ] Map officials to divisions
- [ ] Update `officials` and `official_divisions` tables
- [ ] Create function:
  ```python
  async def resolve_officials(divisions: List[Division]) -> List[Official]:
      """Returns officials for given divisions"""
  ```

**Data Sources:**
- Google Civic Information API
- Open States API (for AZ legislature)
- Phoenix.gov (for city council)

---

### 5. Create SQLAlchemy Models (Week 1-2)

**New File:** `backend/app/models/`

Create models for all tables:
- [ ] `models/user.py` - User, UserProfile, UserPreferences
- [ ] `models/division.py` - Division, UserDivision
- [ ] `models/official.py` - Official, OfficialDivision, UserOfficial
- [ ] `models/measure.py` - Measure, MeasureSource, MeasureStatusEvent
- [ ] `models/vote.py` - VoteEvent, OfficialVote, UserVote, MatchResult
- [ ] `models/connector.py` - Connector, IngestionRun, RawArtifact

**Example:**
```python
# models/user.py
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
import uuid

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True)
    # ... rest of fields
```

---

### 6. Build Federal Data Connector (Week 3)

**New File:** `backend/app/connectors/federal.py`

**Tasks:**
- [ ] Integrate Congress.gov API
- [ ] Fetch upcoming House/Senate votes
- [ ] Parse bill metadata
- [ ] Store in `measures` table
- [ ] Store vote events in `vote_events` table
- [ ] Store roll calls in `official_votes` table
- [ ] Implement scheduled polling (Celery task)

**API Endpoints:**
- Congress.gov: https://api.congress.gov/v3/
- Documentation: https://api.congress.gov/

---

### 7. Build Arizona State Connector (Week 3-4)

**New File:** `backend/app/connectors/arizona.py`

**Tasks:**
- [ ] Integrate Open States API v3
- [ ] Fetch AZ bills and votes
- [ ] Map to canonical schema
- [ ] Store in database
- [ ] Implement scheduled polling

**API:**
- Open States: https://v3.openstates.org/
- Documentation: https://docs.openstates.org/api-v3/

---

### 8. Build Phoenix Legistar Connector (Week 4)

**New File:** `backend/app/connectors/phoenix_legistar.py`

**Tasks:**
- [ ] Parse Legistar calendar page
- [ ] Extract meeting details
- [ ] Parse agenda items
- [ ] Extract outcomes when available
- [ ] Store in `measures` and `vote_events`
- [ ] Handle PDF agenda parsing (use PyPDF2)

**URLs:**
- Calendar: https://phoenix.legistar.com/Calendar.aspx
- Meeting detail pages (linked from calendar)

**Parsing Strategy:**
```python
async def fetch_calendar():
    """Fetch upcoming meetings"""
    
async def parse_meeting_detail(meeting_id):
    """Extract agenda items from meeting"""
    
async def parse_agenda_pdf(pdf_url):
    """Extract text from agenda PDF"""
```

---

### 9. Implement AI Summarization (Week 4-5)

**New File:** `backend/app/services/summarizer.py`

**Tasks:**
- [ ] Integrate OpenAI or Anthropic API
- [ ] Create prompt templates for bill summarization
- [ ] Implement neutral summary generation:
  ```python
  async def summarize_measure(text: str) -> str:
      """Generate 2-4 sentence neutral summary"""
  ```
- [ ] Add topic classification
- [ ] Store summaries in `measures.summary_short`
- [ ] Store confidence scores

**Prompt Guidelines:**
- Neutral, factual tone
- 2-4 sentences
- No advocacy language
- Include what the measure does
- Cite sources

---

### 10. Implement Feed Endpoint (Week 5)

**File:** `backend/app/api/v1/endpoints/feed.py`

**Tasks:**
- [ ] Query relevant measures for user
- [ ] Filter by user's divisions
- [ ] Rank by scheduled date (soonest first)
- [ ] Include user's existing vote if present
- [ ] Implement cursor-based pagination
- [ ] Add filters (level, topic, status)

**Query Logic:**
```sql
SELECT measures.*
FROM measures
LEFT JOIN user_votes ON measures.id = user_votes.measure_id 
  AND user_votes.user_id = :user_id
WHERE (
  measures.level = 'federal'
  OR measures.division_id IN (
    SELECT division_id FROM user_divisions WHERE user_id = :user_id
  )
)
AND measures.status = 'scheduled'
ORDER BY measures.scheduled_for ASC
LIMIT :limit
```

---

### 11. Implement Voting Endpoint (Week 5)

**File:** `backend/app/api/v1/endpoints/voting.py`

**Tasks:**
- [ ] Validate measure exists
- [ ] Validate user hasn't already voted (or allow update)
- [ ] Store vote in `user_votes`
- [ ] Support idempotency via `Idempotency-Key` header
- [ ] Return confirmation

---

### 12. Build Match Engine (Week 6)

**New File:** `backend/app/services/match_engine.py`

**Tasks:**
- [ ] Implement match computation:
  ```python
  async def compute_matches(measure_id: UUID):
      """Compute matches for all users who voted on this measure"""
  ```
- [ ] Compare user vote to official votes
- [ ] Calculate match score (0.0 to 1.0)
- [ ] Generate per-official breakdown
- [ ] Store in `match_results` table
- [ ] Trigger as background job when vote_events are updated

**Match Logic:**
```python
# For each user who voted on measure:
user_vote = "yes" or "no"

# Get user's officials for that jurisdiction
officials = get_user_officials(user_id, measure.division_id)

matches = 0
total = 0

for official in officials:
    official_vote = get_official_vote(vote_event_id, official_id)
    
    if official_vote == "yea" and user_vote == "yes":
        matches += 1
    elif official_vote == "nay" and user_vote == "no":
        matches += 1
    
    total += 1

match_score = matches / total if total > 0 else 0.0
```

---

### 13. Implement Background Jobs (Week 6-7)

**New File:** `backend/app/tasks/`

**Tasks:**
- [ ] Set up Celery configuration
- [ ] Create periodic tasks:
  - [ ] Federal ingestion (every 1 hour)
  - [ ] Arizona ingestion (every 2 hours)
  - [ ] Phoenix ingestion (every 30 minutes)
- [ ] Create one-time tasks:
  - [ ] Address geocoding
  - [ ] Division resolution
  - [ ] Match computation
- [ ] Add task monitoring

**Example:**
```python
# tasks/ingestion.py
from celery import shared_task

@shared_task
def ingest_federal_data():
    """Run federal connector"""
    connector = FederalConnector()
    connector.run()

@shared_task
def compute_matches_for_measure(measure_id: str):
    """Compute matches when vote results available"""
    match_engine.compute_matches(measure_id)
```

---

### 14. Implement Remaining Endpoints (Week 7-8)

**Files:**
- `backend/app/api/v1/endpoints/profile.py`
- `backend/app/api/v1/endpoints/my_votes.py`
- `backend/app/api/v1/endpoints/matching.py`
- `backend/app/api/v1/endpoints/admin.py`

**Tasks:**
- [ ] Profile: GET /me, PATCH /me/address, PATCH /me/preferences
- [ ] My Votes: GET /my-votes with filters
- [ ] Matching: GET /matches, GET /matches/{id}
- [ ] Admin: Connector management, manual ingestion triggers

---

### 15. Build React Native Mobile App (Week 9-10)

**New Directory:** `frontend/mobile/`

**Tasks:**
- [ ] Set up React Native with Expo
- [ ] Implement screens:
  - [ ] Onboarding (address input)
  - [ ] Swipe feed (with card stack)
  - [ ] Measure detail
  - [ ] My Votes
  - [ ] Officials vs Me
  - [ ] Profile/Settings
- [ ] Implement swipe gestures
- [ ] Add API client
- [ ] Handle authentication flow
- [ ] Add offline support (optional)

**Libraries:**
- React Native (with Expo)
- React Navigation
- React Native Gesture Handler (for swipes)
- Axios or Fetch (API client)

---

### 16. Testing & QA (Week 11-12)

**Tasks:**
- [ ] Write unit tests for services
- [ ] Write integration tests for endpoints
- [ ] Test data ingestion pipelines
- [ ] Test match computation accuracy
- [ ] Test mobile app on iOS and Android
- [ ] Load testing for API
- [ ] Security audit

---

## 🔧 Development Tools

### Useful Commands

```bash
# Run database migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Run Celery worker
celery -A app.tasks.celery worker --loglevel=info

# Run Celery beat
celery -A app.tasks.celery beat --loglevel=info

# Run tests
pytest

# Format code
black app/
ruff app/

# Type checking
mypy app/
```

### Debugging

- Use VS Code debugger with FastAPI
- Add breakpoints in API endpoints
- Use PostgreSQL query logs for debugging SQL
- Use Redis CLI to inspect background jobs

---

## 📦 Data Population

### Initial Data Setup

1. **Load Phoenix Divisions:**
   ```sql
   -- Insert Phoenix city division
   INSERT INTO divisions (division_type, ocd_id, name, level)
   VALUES ('city', 'ocd-division/country:us/state:az/place:phoenix', 'Phoenix', 'city');
   
   -- Insert Phoenix council districts 1-8
   -- ... (repeat for each district)
   ```

2. **Load Current Officials:**
   - Federal: Use API to fetch AZ representatives
   - State: Use Open States to fetch AZ legislators
   - City: Manually add Phoenix council members

3. **Initial Ingestion:**
   - Run federal connector to populate recent bills
   - Run Arizona connector for state bills
   - Run Phoenix connector for recent meetings

---

## 🐛 Common Issues & Solutions

### Issue: Geocoding Fails
**Solution:** Implement fallback to Google Maps API or manual coordinate entry

### Issue: No Roll Call Data
**Solution:** Show outcome only (passed/failed) without per-official votes

### Issue: Address Privacy Concerns
**Solution:** Ensure encryption is working, never log addresses, minimize storage

### Issue: Rate Limiting from APIs
**Solution:** Implement caching, respect rate limits, use bulk endpoints where available

---

## 📈 Success Metrics

Track these during development:

- ✅ Database schema created
- ✅ API can authenticate users
- ✅ Address geocoding works
- ✅ Federal connector populates measures
- ✅ Arizona connector populates measures
- ✅ Phoenix connector populates measures
- ✅ Feed shows relevant items
- ✅ Swipes record correctly
- ✅ Match engine computes accurately
- ✅ Mobile app can swipe through feed

---

## 🎓 Learning Resources

### FastAPI
- Official docs: https://fastapi.tiangolo.com/
- SQLAlchemy async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html

### APIs
- Congress.gov: https://api.congress.gov/
- Open States: https://docs.openstates.org/
- Census Geocoder: https://geocoding.geo.census.gov/geocoder/

### React Native
- Expo docs: https://docs.expo.dev/
- React Navigation: https://reactnavigation.org/

---

## 🤝 Need Help?

- Review `docs/PRD.md` for product context
- Review `docs/api-spec.yaml` for API contracts
- Review `database/001_initial_schema.sql` for schema
- Check GitHub Issues for known problems
- Refer to ChatGPT output for original design decisions

---

**Ready to code? Start with Task #1: Complete Authentication!** 🚀
