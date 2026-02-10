# RepCheck

> Of the People. For the People.

## 🎯 Project Overview

RepCheck is a cross-platform mobile and web application that:

1. **Personalizes legislation feeds** based on user location (address-required for accuracy)
2. **Enables quick voting** via swipe gestures (Yes/No)
3. **Tracks official votes** from federal, state, and local representatives
4. **Shows vote alignment** between users and their elected officials

### Phoenix MVP Scope

The initial release targets **Phoenix, Arizona** with coverage for:
- ✅ **Federal**: U.S. Congress (House + Senate)
- ✅ **State**: Arizona Legislature (House + Senate)
- ✅ **City**: Phoenix City Council
- 🔄 **County**: Maricopa County (Phase 2)

---

## 📁 Project Structure

```
civicswipe/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/v1/   # API endpoints
│   │   ├── core/     # Config, database, security
│   │   ├── models/   # SQLAlchemy models
│   │   ├── services/ # Business logic
│   │   └── schemas.py
│   ├── main.py
│   └── requirements.txt
│
├── frontend/          # React Native + Web
│   ├── mobile/       # iOS & Android (React Native)
│   └── web/          # Web app (Next.js)
│
├── database/
│   └── 001_initial_schema.sql
│
└── docs/
    ├── PRD.md        # Product Requirements Document
    └── api-spec.yaml # OpenAPI specification
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **PostgreSQL 14+**
- **Redis 7+**
- **Node.js 18+** (for frontend)

### Backend Setup

1. **Clone and navigate:**
   ```bash
   cd civicswipe/backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Setup database:**
   ```bash
   # Create database
   createdb civicswipe
   
   # Run migrations
   psql -d civicswipe -f ../database/001_initial_schema.sql
   ```

6. **Run the server:**
   ```bash
   python main.py
   ```

   The API will be available at: http://localhost:8000
   - Swagger docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Environment Variables

Create a `.env` file in `backend/` with:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://civicswipe:password@localhost:5432/civicswipe

# Security
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here

# External APIs
CONGRESS_API_KEY=your-congress-api-key
OPENSTATES_API_KEY=your-openstates-key
GOOGLE_MAPS_API_KEY=your-google-maps-key

# AI Services (for summarization)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Redis
REDIS_URL=redis://localhost:6379/0
```

---

## 📊 Database Schema

The database uses PostgreSQL with the following key tables:

### Core Tables
- `users` - User accounts
- `user_profile` - Address (encrypted) + geolocation
- `user_divisions` - User → jurisdiction mapping
- `officials` - Elected representatives
- `measures` - Bills, ordinances, agenda items
- `vote_events` - Official votes/roll calls
- `user_votes` - User swipes
- `match_results` - Comparison of user vs official votes

See `database/001_initial_schema.sql` for complete schema.

---

## 🔌 API Endpoints

### Authentication
- `POST /v1/auth/signup` - Create account (requires address)
- `POST /v1/auth/login` - Login
- `POST /v1/auth/refresh` - Refresh token

### Profile
- `GET /v1/me` - Get user profile
- `PATCH /v1/me/address` - Update address
- `PATCH /v1/me/preferences` - Update preferences

### Feed
- `GET /v1/feed` - Get personalized swipe feed
- `GET /v1/measures/{id}` - Get measure details

### Voting
- `POST /v1/measures/{id}/swipe` - Record vote (Yes/No)

### My Votes
- `GET /v1/my-votes` - Get user's voting history

### Matching
- `GET /v1/matches` - Get measures with official votes
- `GET /v1/matches/{id}` - Get detailed match breakdown

### Admin
- `GET /v1/admin/connectors` - List data connectors
- `POST /v1/admin/connectors` - Create connector
- `POST /v1/admin/ingest/run` - Trigger ingestion

Full API specification: `docs/api-spec.yaml`

---

## 🤖 Data Sources

### Federal
- **Congress.gov API** - Bills, votes, roll calls
- **govinfo API** - Official bill text and documents

### Arizona State
- **Open States API v3** - State legislature data
- Alternative: **LegiScan API** (commercial)

### Phoenix Local
- **Legistar** - City Council meetings, agendas, outcomes
  - Base URL: https://phoenix.legistar.com
  - Calendar, meeting details, agenda items

### Geocoding
- **Census Geocoder** - Address → coordinates + divisions
- **Google Civic Info API** - Address → representatives

---

## 🏗️ Architecture

### Backend Components

1. **API Layer** (FastAPI)
   - REST endpoints
   - JWT authentication
   - Request validation

2. **Database Layer** (PostgreSQL + SQLAlchemy)
   - User data (encrypted addresses)
   - Measures and votes
   - Match results

3. **Ingestion Pipeline** (Celery + Redis)
   - Federal connector
   - State connector
   - Local connector (Legistar)

4. **AI Processing** (OpenAI/Anthropic)
   - Bill summarization
   - PDF extraction
   - Topic classification

5. **Match Engine**
   - Compare user votes to official roll calls
   - Compute match scores
   - Generate breakdowns

### Frontend (To Be Implemented)

- **Mobile**: React Native (iOS + Android)
- **Web**: Next.js
- **Shared**: Component library, API client

---

## 🔐 Security & Privacy

### Address Encryption
- Addresses encrypted using Fernet (symmetric encryption)
- Only city/state/ZIP exposed in API responses
- Address hash used for deduplication
- Encryption key stored in environment (KMS in production)

### Authentication
- JWT tokens (access + refresh)
- Bcrypt password hashing
- Secure token rotation

### Data Access
- Row-level security planned
- User data isolated by user_id
- Admin endpoints require elevated permissions

---

## 📋 Development Roadmap

### Phase 1: MVP (Current)
- [x] Database schema
- [x] API specification
- [x] Core backend structure
- [ ] Authentication endpoints (in progress)
- [ ] Address validation & geocoding
- [ ] Federal data connector
- [ ] Arizona state connector
- [ ] Phoenix Legistar connector
- [ ] Match engine
- [ ] Mobile app (React Native)

### Phase 2: Expansion
- [ ] All 50 states
- [ ] Additional Arizona cities
- [ ] Maricopa County integration
- [ ] Push notifications
- [ ] Social sharing

### Phase 3: Scale
- [ ] Connector marketplace
- [ ] Community features
- [ ] Impact tracking
- [ ] API for third parties

---

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py
```

---

## 📝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📖 Documentation

- **PRD**: `docs/PRD.md`
- **API Spec**: `docs/api-spec.yaml`
- **Database Schema**: `database/001_initial_schema.sql`

---

## 🎨 Design Philosophy

### Neutrality
- No advocacy or persuasive language
- Factual summaries only
- Source links always provided

### Privacy-First
- Address encryption
- Minimal data retention
- Clear privacy policies

### Accuracy
- Prefer official APIs over scraping
- Maintain data provenance
- Regular data validation

---

## 📧 Contact & Support

- **Email**: support@repcheck.us
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

---

## 📄 License

[License TBD]

---

## 🙏 Acknowledgments

- Open States Project
- Congress.gov
- LegiScan
- Census Bureau Geocoding Services

---

**Built with ❤️ for civic engagement**
