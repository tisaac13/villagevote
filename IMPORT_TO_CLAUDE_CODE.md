# 🚀 RepCheck - Import to Claude Code

## Quick Start (2 minutes)

### 1. Extract Project
```bash
tar -xzf civicswipe-claude-code-ready.tar.gz
cd civicswipe
```

### 2. Run Automated Setup
```bash
chmod +x setup.sh
./setup.sh
```

The setup script will:
- ✅ Create Python virtual environment
- ✅ Install all dependencies (FastAPI, SQLAlchemy, etc.)
- ✅ Start Docker services (PostgreSQL, Redis)
- ✅ Initialize database with schema
- ✅ Create .env configuration file

### 3. Add API Keys

Edit `backend/.env` and add:
```bash
CONGRESS_API_KEY=your_key_here          # Get from https://api.congress.gov/sign-up/
OPENSTATES_API_KEY=your_key_here        # Get from https://openstates.org/accounts/profile/
GOOGLE_MAPS_API_KEY=your_key_here       # Get from Google Cloud Console
OPENAI_API_KEY=your_key_here            # Get from https://platform.openai.com/api-keys
```

### 4. Start Development

```bash
cd backend
source venv/bin/activate
python main.py
```

Visit: **http://localhost:8000/docs**

---

## 📁 What's Included

### ✅ Ready to Run
- Complete FastAPI backend (70% complete)
- Full PostgreSQL schema (15 tables)
- All SQLAlchemy models (13 classes)
- All API endpoints (15 routes)
- Core services (geocoding, division resolver, match engine)
- Security layer (JWT, encryption, hashing)
- Docker Compose setup

### 📚 Documentation
- `CLAUDE_CODE_README.md` - Quick reference guide
- `docs/PRD.md` - Product requirements
- `docs/api-spec.yaml` - OpenAPI specification
- `docs/IMPLEMENTATION_GUIDE.md` - 16 prioritized development tasks
- `.clinerules` - AI assistant guidelines

### 🛠️ Development Tools
- `setup.sh` - Automated setup script
- `civicswipe.code-workspace` - VS Code workspace settings
- `.gitignore` - Git ignore rules
- `docker-compose.yml` - Local services

---

## 🎯 Your First Tasks in Claude Code

### Task 1: Complete JWT Authentication (2 hours)
**File:** `backend/app/api/v1/endpoints/profile.py`

**Current code:**
```python
async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    """Dependency to get current user - TODO: implement JWT validation"""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)
```

**What to implement:**
1. Extract JWT token from Authorization header
2. Verify token signature using SECRET_KEY
3. Get user_id from token payload
4. Query database for user
5. Return user object or raise 401

**Example implementation:**
```python
from fastapi import Header
from app.core.security import verify_token

async def get_current_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token, token_type="access")
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    user = await db.get(User, user_id)
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user
```

### Task 2: Build Federal Connector (2-3 days)
**New file:** `backend/app/connectors/federal.py`

See `docs/IMPLEMENTATION_GUIDE.md` Section 6 for detailed specifications.

---

## 🧪 Test Your Setup

### 1. Check Services
```bash
# Verify PostgreSQL is running
docker-compose ps

# Check database
psql -d civicswipe -c "SELECT COUNT(*) FROM users;"
```

### 2. Test API
```bash
# Start server
cd backend
source venv/bin/activate
python main.py

# In another terminal, test health check
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development"
}
```

### 3. View API Docs
Open browser to: http://localhost:8000/docs

You should see interactive API documentation with all 15 endpoints.

---

## 📊 Project Status

| Component | Status | Completion |
|-----------|--------|------------|
| Database Schema | ✅ Complete | 100% |
| SQLAlchemy Models | ✅ Complete | 100% |
| API Endpoints | ✅ Complete | 100% |
| Core Services | ✅ Complete | 100% |
| JWT Auth | ⚠️ Needs Implementation | 90% |
| External Connectors | ⏳ Not Started | 0% |
| Background Jobs | ⏳ Not Started | 0% |
| Frontend | ⏳ Not Started | 0% |
| **Backend Overall** | 🚧 In Progress | **70%** |
| **Full Project** | 🚧 In Progress | **40%** |

---

## 🔧 Claude Code Features

### Use AI Assistant
The `.clinerules` file configures Claude Code to understand:
- Project architecture and patterns
- Coding standards and conventions
- Common issues and solutions
- Priority task ordering

### VS Code Integration
Open the workspace file for optimal settings:
```bash
code civicswipe.code-workspace
```

Includes:
- Python environment configuration
- Debugger launch configurations
- Automated tasks (format, test, run)
- Recommended extensions

### Tasks Available
Press `Cmd/Ctrl + Shift + P` → "Tasks: Run Task":
- Run FastAPI Server
- Run Tests
- Format Code
- Type Check
- Start Docker Services
- Stop Docker Services
- View Docker Logs

---

## 📖 Key Documentation

### Start Here
1. **CLAUDE_CODE_README.md** - This file (overview)
2. **docs/IMPLEMENTATION_GUIDE.md** - Task-by-task development plan
3. **docs/api-spec.yaml** - API contracts

### Reference
- **docs/PRD.md** - Product requirements and architecture
- **README.md** - Full project documentation
- **database/001_initial_schema.sql** - Database schema

### Development
- **.clinerules** - AI assistant guidelines
- **backend/app/** - Source code
- **tests/** - Test files (to be created)

---

## 🐛 Common Issues

### "ModuleNotFoundError: No module named 'fastapi'"
```bash
# Activate virtual environment
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### "Connection refused" to PostgreSQL
```bash
# Start Docker services
docker-compose up -d

# Wait for PostgreSQL to initialize
sleep 5

# Check status
docker-compose ps
```

### "Database 'civicswipe' does not exist"
```bash
createdb civicswipe
psql -d civicswipe -f database/001_initial_schema.sql
```

---

## 🚀 Next Steps After Import

1. ✅ Run `./setup.sh`
2. ✅ Add API keys to `backend/.env`
3. ✅ Start server: `python main.py`
4. ✅ Test at http://localhost:8000/docs
5. 📝 Open `docs/IMPLEMENTATION_GUIDE.md`
6. 💻 Start with Task #1: JWT Authentication
7. 🔄 Build connectors (Tasks #6-8)
8. 🎯 Implement background jobs (Task #13)

---

## 📧 Support Resources

- **Implementation Guide:** `docs/IMPLEMENTATION_GUIDE.md`
- **API Reference:** http://localhost:8000/docs (when running)
- **Development Status:** `DEVELOPMENT_STATUS.md`

---

**Ready to code!** Import the project and run `./setup.sh` to get started. 🎉
