# CivicSwipe - Product Requirements Document (PRD)

## Product Name
**CivicSwipe** (working name)

## Problem Statement
Most people don't track legislation and votes across federal/state/local levels. Even fewer can later see whether elected officials voted in line with their preferences.

## Goal
Provide a personalized, swipe-based voting feed of upcoming legislation/votes relevant to a user's location, and later show whether the user's stance matched the recorded votes of their elected officials.

---

## Core User Stories

1. **As a user**, I enter my **address** to sign up and see only relevant items (federal + my state + my county + my city).

2. **As a user**, I swipe right = Yes and left = No on upcoming votes / legislative items.

3. **As a user**, I can open a card to read a neutral summary and source links.

4. **As a user**, I can view a "My Votes" tab with everything I swiped on.

5. **As a user**, I can view an "Officials vs Me" tab that shows pass/fail and whether my vote matched my officials' yea/nay votes.

---

## Non-Goals (MVP)

- ❌ Persuading users how to vote (no advocacy language)
- ❌ "Predicting" outcomes or adding partisan framing
- ❌ Full nationwide local coverage on day 1 (local is connector-by-connector)

---

## Key Product Decisions

### Feed Content
**MVP includes:**
- Items with **scheduled votes** (highest signal)
- Optional expansion: introduced bills, hearings, agenda items

### Location Requirements
- **Address is REQUIRED** at signup
- ZIP code alone is insufficient for accurate district mapping
- Address enables accurate matching to:
  - Congressional district
  - State legislative districts
  - City council district
  - County supervisorial district

### Official Matching Definition
A user's "official set" by jurisdiction level:
- **Federal**: Representative + 2 Senators
- **State**: Upper chamber + lower chamber representatives (requires districting)
- **Local**: City council + county board (often ward-based)

---

## Core Screens / Features

### 1. Onboarding
- Email/phone authentication (or social login)
- **Address required** (street, city, state, ZIP)
- Optional: topic preferences

### 2. Swipe Feed
- Card displays:
  - Title
  - Jurisdiction (Federal / Arizona / Phoenix)
  - Vote/meeting date
  - AI-generated neutral summary (2-4 sentences)
  - Source links (official pages/PDFs)

### 3. Card Detail View
- Full summary
- Key points
- Status timeline
- Official source links

### 4. My Votes Tab
- Filter by jurisdiction/topic
- See current status and outcomes
- View your historical voting record

### 5. Officials vs Me Tab
For each item:
- Your swipe (Yes/No)
- Official roll call results
- Match result with visual indicators

### 6. Notifications (Phase 1 or 2)
- "Vote scheduled soon"
- "Vote happened — outcome posted"
- "Your officials voted — see match"

---

## Success Metrics

| Metric | Target |
|--------|--------|
| **Activation** | % of signups who swipe ≥10 items in first week |
| **Retention** | Weekly active swipers |
| **Data Reliability** | % items with correct status/outcome within X hours |
| **Match Coverage** | % of user-voted items that later have roll call matching |

---

## Phoenix MVP Scope

### Day 1 Coverage
1. **Federal**: U.S. House + Senate votes (roll calls)
2. **Arizona State**: Bills + votes in AZ Legislature
3. **City of Phoenix**: City Council meeting agenda items + outcomes

### Phase 2 (Post-Launch)
4. **Maricopa County**: Board of Supervisors agendas + outcomes

---

## Data Sources

### Federal (Reliable APIs)
- **Congress.gov**: Bill data + status + vote info via API/bulk data
- **govinfo (GPO) API**: Official bill text, status packages

### State (Normalized Layer)
- **Open States API v3**: Widely used civic data layer
- **LegiScan API**: Commercial option with strong coverage

### Local - Phoenix Specific
- **Phoenix Legistar**: Meeting calendar, agenda items, results
  - URL: https://phoenix.legistar.com
  - Has both HTML pages and potential API access

### Location Resolution
- **Census Geocoder**: Address → county/place
- **OCD IDs**: Open Civic Data division identifiers
- **Google Civic Information API**: Address → representatives/districts

---

## Technology Decisions

### Required for Accurate Matching
- Store address securely (encrypted)
- Generate stable address hash for deduplication
- Geocode to lat/lon for district mapping
- Resolve to standardized division identifiers (OCD IDs)

### AI Usage (Appropriate Tasks)
✅ **Good AI Tasks:**
- Summarize bill text into neutral descriptions
- Extract structured data from PDFs/HTML (local agendas)
- Classify topic tags (housing, taxes, schools)
- Deduplicate near-identical items

❌ **Avoid:**
- "Telling people how to vote"
- Overconfident summaries without citations
- Persuasive or advocacy framing

---

## Risks & Constraints

| Risk | Mitigation |
|------|------------|
| Local data fragmentation | Start with structured sources (Legistar), expand carefully |
| District accuracy | Require address, not just ZIP |
| AI summary bias/neutrality | Store raw source + generated summary + citations |
| Scraping compliance | Prefer APIs, respect robots.txt, maintain provenance |

---

## Platform Strategy

### Cross-Platform Approach
- **Mobile**: React Native (iOS + Android)
- **Web**: Next.js (shared component library with React Native)
- **Backend**: Python FastAPI or Node.js NestJS
- **Database**: PostgreSQL (core) + Redis (caching/queues)

---

## MVP Development Timeline

**Estimated: 8-12 weeks (small team)**

### Phase 1: Core Platform (Weeks 1-4)
- Database schema + migrations
- User authentication + address validation
- Division/official resolution pipeline
- Basic swipe feed endpoint

### Phase 2: Data Ingestion (Weeks 5-8)
- Federal connector (Congress.gov)
- Arizona connector (Open States)
- Phoenix Legistar connector
- AI summarization pipeline

### Phase 3: Matching Engine (Weeks 9-10)
- Vote event ingestion
- Match computation logic
- "Officials vs Me" endpoint

### Phase 4: Client Apps (Weeks 11-12)
- React Native mobile app (iOS + Android)
- Web interface
- Testing + refinement

---

## Future Expansion

### Phase 2 Features
- All 50 states coverage
- Expanded local metros (where data is structured)
- Push notifications
- Social sharing

### Phase 3 Vision
- Connector marketplace (easy city/county additions)
- Verified official vote matching with confidence scoring
- Legislative impact tracking
- Community discussions (optional)

---

## Compliance & Legal

### Data Privacy
- Encrypt stored addresses (PGP symmetric encryption)
- Store address hash for deduplication only
- Never expose raw addresses in logs or APIs
- Clear privacy policy disclosure

### Data Access
- Prefer official APIs with explicit data access rights
- Respect robots.txt for web scraping
- Cache and throttle requests appropriately
- Maintain provenance for all data

### Neutrality Requirement
- No advocacy language in summaries
- Always provide source links
- Present factual voting records only
- No predictive or persuasive framing

---

## Open Questions

1. **Authentication**: Start with email/password or prioritize social login (Google/Apple)?
2. **Notifications**: Push or email first? Frequency limits?
3. **Monetization**: Free with ads, freemium, or subscription model?
4. **Content Moderation**: How to handle user-reported inaccuracies?

---

## Next Steps

1. ✅ Database schema implemented
2. ⏳ Backend API development
3. ⏳ Connector implementation (Federal → AZ → Phoenix)
4. ⏳ Mobile app development
5. ⏳ Beta testing in Phoenix metro area
