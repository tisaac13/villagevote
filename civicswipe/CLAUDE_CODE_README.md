# CivicSwipe - Claude Code Import Guide

## 🎯 Quick Start in Claude Code

This project is ready to import into Claude Code. Follow these steps:

### 1. Extract and Open Project

```bash
# Extract the archive
tar -xzf civicswipe.tar.gz

# Open in Claude Code
claude-code civicswipe/
```

### 2. Run Automated Setup

```bash
# Run the setup script (handles everything automatically)
chmod +x setup.sh
./setup.sh
```

This will:
- ✅ Create Python virtual environment
- ✅ Install all dependencies
- ✅ Start Docker services (PostgreSQL, Redis)
- ✅ Create database and run migrations
- ✅ Create .env file from template

### 3. Configure API Keys

Edit `backend/.env` and add your keys:

```bash
# Required for data ingestion
CONGRESS_API_KEY=your_key_here
OPENSTATES_API_KEY=your_key_here

# Required for geocoding
GOOGLE_MAPS_API_KEY=your_key_here

# Required for AI summarization (choose one)
OPENAI_API_KEY=your_key_here
# OR
ANTHROPIC_API_KEY=your_key_here

# Generate secure keys
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### 4. Start Development Server

```bash
cd backend
source venv/bin/activate
python main.py
```

Visit: http://localhost:8000/docs

---

## 🏗️ Project Structure

```
civicswipe/
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── api/v1/       # API endpoints
│   │   ├── core/         # Config, database, security
│   │   ├── models/       # SQLAlchemy models
│   │   ├── services/     # Business logic
│   │   └── schemas.py    # Pydantic models
│   ├── main.py           # Application entry
│   └── requirements.txt  # Dependencies
│
├── database/
│   └── 001_initial_schema.sql
│
├── docs/
│   ├── PRD.md                    # Product requirements
│   ├── api-spec.yaml             # OpenAPI spec
│   └── IMPLEMENTATION_GUIDE.md   # Development roadmap
│
├── docker-compose.yml
└── setup.sh              # Automated setup
```

---

## 🔧 Claude Code Workflow

### Recommended Development Order

1. **Complete JWT Authentication** (2 hours)
   ```
   File: backend/app/api/v1/endpoints/profile.py
   Task: Implement get_current_user() dependency
   ```

2. **Build Federal Connector** (2-3 days)
   ```
   New file: backend/app/connectors/federal.py
   Task: Integrate Congress.gov API
   ```

3. **Build Arizona Connector** (2-3 days)
   ```
   New file: backend/app/connectors/arizona.py
   Task: Integrate Open States API
   ```

4. **Build Phoenix Legistar Connector** (3-4 days)
   ```
   New file: backend/app/connectors/phoenix_legistar.py
   Task: Parse Legistar calendar and meetings
   ```

5. **Implement Background Jobs** (3-4 days)
   ```
   New files: backend/app/tasks/*.py
   Task: Set up Celery for scheduled ingestion
   ```

See `docs/IMPLEMENTATION_GUIDE.md` for detailed task breakdowns.

---

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

---

## 📊 Current Status

- ✅ Database schema (100%)
- ✅ SQLAlchemy models (100%)
- ✅ API endpoints (100%)
- ✅ Core services (100%)
- ⏳ External API connectors (0%)
- ⏳ Background jobs (0%)
- ⏳ Frontend (0%)

**Overall: 70% backend complete, 40% project complete**

---

## 🐛 Troubleshooting

### Database connection issues
```bash
# Check PostgreSQL is running
docker-compose ps

# View logs
docker-compose logs postgres

# Restart services
docker-compose restart
```

### Import errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Port already in use
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or change port in main.py
uvicorn.run("main:app", host="0.0.0.0", port=8001)
```

---

## 📚 Key Files for Claude Code

### Start Here
1. `docs/IMPLEMENTATION_GUIDE.md` - What to build next
2. `docs/api-spec.yaml` - API contracts
3. `backend/main.py` - Application entry point

### Frequently Modified
- `backend/app/api/v1/endpoints/*.py` - API endpoints
- `backend/app/services/*.py` - Business logic
- `backend/app/models/*.py` - Database models

### Reference
- `docs/PRD.md` - Product requirements
- `database/001_initial_schema.sql` - Schema reference
- `README.md` - Full project documentation

---

## 🔑 Environment Variables Reference

### Required
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT signing key
- `ENCRYPTION_KEY` - Address encryption key

### Optional (for full functionality)
- `CONGRESS_API_KEY` - Federal data
- `OPENSTATES_API_KEY` - State data
- `GOOGLE_MAPS_API_KEY` - Geocoding
- `OPENAI_API_KEY` - AI summarization
- `ANTHROPIC_API_KEY` - AI summarization (alternative)

### Generated
The setup script generates secure keys automatically. You can also generate manually:

```python
# SECRET_KEY
import secrets
print(secrets.token_urlsafe(32))

# ENCRYPTION_KEY
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

---

## 🚀 Deployment Checklist

Before deploying to production:

- [ ] Change SECRET_KEY and ENCRYPTION_KEY
- [ ] Set ENVIRONMENT=production
- [ ] Configure production DATABASE_URL
- [ ] Set up SSL/TLS certificates
- [ ] Configure CORS_ORIGINS for your domains
- [ ] Set up proper logging
- [ ] Enable rate limiting
- [ ] Configure backups
- [ ] Set up monitoring (Sentry, DataDog, etc.)
- [ ] Review and update security settings

---

## 📧 Support

- **Documentation:** See `docs/` folder
- **Issues:** Check `docs/IMPLEMENTATION_GUIDE.md` for known issues
- **Architecture:** See `docs/PRD.md` for design decisions

---

**Ready to code!** 🎉

Start with `./setup.sh` then open `docs/IMPLEMENTATION_GUIDE.md` for your first task.
