# Githaf Consulting Chatbot - Backend v2.0 (Agentic)

**Advanced RAG-based customer service chatbot with agentic capabilities**

Built with FastAPI, LangChain, Groq, and powered by Llama 3.1-8b-instant.

---

## What's New in v2.0 (Agentic Upgrade)

Version 2.0 transforms the chatbot from a simple RAG system into a fully **agentic AI assistant** with advanced reasoning, planning, memory, and tool integration capabilities.

### 5-Phase Agentic Architecture

#### Phase 1: Observation Layer (Response Validation)
- **LLM-based quality assessment** for all responses
- **Automatic hallucination detection**
- **Retry logic** with parameter adjustment for failed validations
- Confidence scoring (0.0-1.0) for transparency

#### Phase 2: Planning Layer (Multi-Step Execution)
- **Complex query decomposition** into sequential action plans
- **8 action types**: SEARCH_KNOWLEDGE, GET_CONTACT_INFO, SEND_EMAIL, CHECK_CALENDAR, QUERY_CRM, VALIDATE_DATA, FORMAT_RESPONSE, ASK_CLARIFICATION
- **Parallel execution support** for independent actions
- Context sharing between steps

#### Phase 3: Self-Improvement Loop
- **Weekly automated learning** from user feedback
- **Dynamic parameter optimization** (similarity threshold, top_k, temperature)
- **Knowledge gap identification** for continuous improvement
- **A/B testing framework** for experimental features

#### Phase 4: Advanced Memory
- **Semantic memory extraction** with fact categorization
- **Automatic conversation summarization** (topic, intent, sentiment)
- **Long-term context retention** across sessions
- **Personalized responses** using retrieved memories

#### Phase 5: Tool Ecosystem
- **Email Tool**: SMTP integration for automated emails
- **Calendar Tool**: Appointment scheduling and availability checking
- **CRM Tool**: Contact management and interaction logging
- **Web Search Tool**: Real-time information retrieval (DuckDuckGo/SerpAPI)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   7-Step Agentic Framework                  │
├─────────────────────────────────────────────────────────────┤
│  1. PERCEIVE   → Intent classification + query understanding│
│  2. STORE      → Semantic memory + conversation history     │
│  3. REASON     → RAG pipeline + semantic search             │
│  4. PLAN       → Multi-step decomposition (if needed)       │
│  5. EXECUTE    → Action execution + tool integration        │
│  6. OBSERVE    → Response validation + quality check        │
│  7. SELF-IMPROVE → Weekly learning + parameter tuning       │
└─────────────────────────────────────────────────────────────┘

Core Technologies:
├─ LLM: Groq API (Llama 3.1-8b-instant) - 500 tokens/sec
├─ Embeddings: Sentence Transformers (all-MiniLM-L6-v2, 384-dim)
├─ Vector DB: Supabase PostgreSQL + pgvector (cosine similarity)
├─ Web Framework: FastAPI 0.110.0
├─ Background Jobs: APScheduler 3.10.4
└─ Testing: Pytest 7.4.4 with 60% coverage requirement
```

---

## Quick Start

### 1. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
```bash
cp .env.example .env
# Edit .env with your credentials (see Configuration section below)
```

### 4. Database Setup

**Option A: Supabase (Recommended)**
```bash
# Run SQL migrations in Supabase SQL Editor
psql $DATABASE_URL < scripts/database_schema.sql
psql $DATABASE_URL < scripts/create_memory_tables.sql
psql $DATABASE_URL < scripts/create_tools_tables.sql
psql $DATABASE_URL < scripts/create_settings_table.sql
psql $DATABASE_URL < scripts/vector_search_function.sql

# Create admin user
python scripts/quick_create_admin.py
# Default credentials: admin@githaf.com / admin123 (CHANGE IN PRODUCTION!)
```

**Option B: Self-Hosted PostgreSQL**
```bash
# Install PostgreSQL 14+ with pgvector extension
# Then run the same migrations as above
```

### 5. Run Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Access Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## Configuration

Create a `.env` file in the `backend/` directory:

```bash
# API Configuration
API_V1_STR=/api/v1
PROJECT_NAME="Githaf Consulting Chatbot API"
HOST=0.0.0.0
PORT=8000

# Supabase (Database + Storage)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Groq API (LLM Provider)
GROQ_API_KEY=your-groq-api-key

# Embedding Model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# RAG Configuration
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.5
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# LLM Configuration
LLM_MODEL=llama-3.1-8b-instant
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500

# Authentication (CRITICAL - Generate new key!)
SECRET_KEY=generate-with-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Email Tool (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@your-domain.com
FROM_NAME=Githaf Consulting Bot

# Web Search Tool (Optional)
SEARCH_PROVIDER=duckduckgo
SERPAPI_KEY=your-serpapi-key-if-using-serpapi
```

**Generate SECRET_KEY:**
```bash
openssl rand -hex 32
```

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                      # FastAPI application (v2.0, scheduler integration)
│   │
│   ├── core/                        # Core configuration
│   │   ├── config.py               # Settings (Pydantic)
│   │   ├── database.py             # Supabase client
│   │   ├── dependencies.py         # FastAPI dependencies
│   │   └── security.py             # JWT & password hashing
│   │
│   ├── models/                      # Pydantic schemas
│   │   ├── action.py               # [NEW] Action framework (Phase 2)
│   │   ├── conversation.py
│   │   ├── feedback.py
│   │   ├── message.py
│   │   ├── settings.py
│   │   └── user.py
│   │
│   ├── services/                    # Business logic
│   │   ├── rag_service.py          # [UPDATED] RAG orchestrator with planning & validation
│   │   ├── validation_service.py   # [NEW] Response validation (Phase 1)
│   │   ├── planning_service.py     # [NEW] Multi-step planning (Phase 2)
│   │   ├── learning_service.py     # [NEW] Self-improvement (Phase 3)
│   │   ├── scheduler.py            # [NEW] Background jobs (Phase 3)
│   │   ├── ab_testing_service.py   # [NEW] A/B testing (Phase 3)
│   │   ├── memory_service.py       # [NEW] Semantic memory (Phase 4)
│   │   ├── conversation_summary_service.py  # [NEW] Summarization (Phase 4)
│   │   ├── tools/                  # [NEW] Tool ecosystem (Phase 5)
│   │   │   ├── tools_registry.py   # Tool registry (singleton)
│   │   │   ├── email_tool.py       # Email integration
│   │   │   ├── calendar_tool.py    # Calendar operations
│   │   │   ├── crm_tool.py         # CRM management
│   │   │   └── web_search_tool.py  # Web search
│   │   ├── embedding_service.py
│   │   ├── conversation_service.py
│   │   ├── vectorstore_service.py
│   │   ├── llm_service.py
│   │   ├── analytics_service.py
│   │   ├── settings_service.py
│   │   └── storage_service.py
│   │
│   ├── api/
│   │   ├── v1.py                   # API router aggregator
│   │   └── routes/
│   │       ├── chat.py             # Chat endpoint
│   │       ├── documents.py        # Knowledge base CRUD
│   │       ├── conversations.py    # History viewer
│   │       ├── feedback.py         # User ratings
│   │       ├── analytics.py        # Dashboard metrics
│   │       ├── auth.py             # JWT authentication
│   │       ├── settings.py         # System settings
│   │       └── users.py            # User management
│   │
│   ├── utils/
│   │   ├── prompts.py              # [UPDATED] LLM prompts (validation, planning, memory)
│   │   ├── logger.py
│   │   ├── text_processor.py
│   │   ├── file_parser.py
│   │   └── url_scraper.py
│   │
│   └── middleware/
│       ├── cors.py
│       ├── error_handler.py
│       └── rate_limiter.py
│
├── tests/                           # [NEW] Comprehensive test suite (Phase 6)
│   ├── test_validation_service.py  # Phase 1 tests
│   ├── test_planning_service.py    # Phase 2 tests
│   ├── test_learning_service.py    # Phase 3 tests
│   ├── test_memory_service.py      # Phase 4 tests
│   ├── test_tools.py               # Phase 5 tests
│   ├── integration/
│   │   └── test_full_pipeline.py   # End-to-end tests
│   └── benchmarks/
│       └── performance_benchmark.py # Performance SLA validation
│
├── scripts/
│   ├── database_schema.sql         # Core database tables
│   ├── create_memory_tables.sql    # [NEW] Phase 4 memory tables
│   ├── create_tools_tables.sql     # [NEW] Phase 5 tool tables
│   ├── create_settings_table.sql   # System settings table
│   ├── vector_search_function.sql  # pgvector RPC function
│   ├── init_db.py                  # Database initialization
│   ├── seed_knowledge_base.py      # Sample data seeding
│   ├── quick_create_admin.py       # Quick admin user creation
│   └── create_admin.py             # Interactive admin creation
│
├── requirements.txt                # [UPDATED] Python dependencies (apscheduler, pytest)
├── pytest.ini                      # [NEW] Pytest configuration (Phase 6)
├── README.md                       # This file
├── DEPLOYMENT.md                   # [NEW] Comprehensive deployment guide (Phase 6)
├── API_DOCUMENTATION.md            # [NEW] Complete API reference (Phase 6)
└── .env.example                    # Environment variables template
```

---

## API Endpoints

### Public Endpoints (No Authentication)

#### Chat
```http
POST /api/v1/chat/
```
Send message to chatbot. Includes automatic planning, validation, and memory enrichment.

**Rate Limit:** 10 requests/minute per IP

#### Feedback
```http
POST /api/v1/feedback/
```
Submit user feedback (thumbs up/down) on responses.

#### Health Check
```http
GET /health
```
Check API health and database connectivity.

### Protected Endpoints (JWT Required)

#### Authentication
```http
POST /api/v1/auth/login
```
Authenticate admin user and receive JWT token.

#### Documents (Knowledge Base)
```http
GET    /api/v1/documents/               # List all documents
GET    /api/v1/documents/{id}           # Get document details
POST   /api/v1/documents/upload         # Upload file (PDF, DOCX, TXT)
POST   /api/v1/documents/url            # Scrape URL content
DELETE /api/v1/documents/{id}           # Delete document
```

#### Conversations
```http
GET /api/v1/conversations/              # List all conversations
GET /api/v1/conversations/{id}          # Get conversation with messages
```

#### Analytics
```http
GET /api/v1/analytics/                  # Dashboard overview
GET /api/v1/analytics/flagged           # Low-rated responses
GET /api/v1/analytics/daily             # Daily statistics (date range)
GET /api/v1/analytics/countries         # Country statistics (date range)
```

#### Users
```http
GET    /api/v1/users/                   # List all users
POST   /api/v1/users/                   # Create user
DELETE /api/v1/users/{id}               # Delete user
```

#### System Settings
```http
GET  /api/v1/settings/                  # Get settings
PUT  /api/v1/settings/                  # Update settings
POST /api/v1/settings/reset             # Reset to defaults
```

**For detailed API documentation with examples, see [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)**

---

## Testing

### Run All Tests
```bash
pytest
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest -m unit

# Integration tests (requires database)
pytest -m integration

# Performance benchmarks
pytest -m benchmark

# Async tests
pytest -m async
```

### Run with Coverage Report
```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html to view coverage report
```

### Performance Benchmarks

Run performance benchmarks to ensure SLA compliance:

```bash
pytest tests/benchmarks/performance_benchmark.py -v
```

**Performance Targets (SLA):**
- Embedding generation: < 200ms
- Intent classification: < 300ms
- Conversational response: < 100ms
- Simple RAG query: < 3000ms
- Planning generation: < 2000ms
- Response validation: < 1500ms

---

## Database Schema

### Core Tables (v1.0)
- `users` - Admin accounts
- `documents` - Knowledge base metadata
- `embeddings` - Vector embeddings (pgvector)
- `conversations` - Chat sessions
- `messages` - Individual messages
- `feedback` - User ratings
- `system_settings` - Global configuration

### Phase 4: Advanced Memory
- `semantic_memory` - Extracted facts with embeddings
- `conversation_summaries` - Structured conversation summaries
- `user_preferences` - User-specific preferences

### Phase 5: Tool Ecosystem
- `appointments` - Calendar appointments
- `crm_contacts` - Contact records
- `crm_interactions` - Interaction history

**For complete schema, see `scripts/database_schema.sql`**

---

## Key Features

### 1. RAG Pipeline (Enhanced)
- **Semantic search** using pgvector cosine similarity
- **Context-aware responses** with conversation history
- **Source citations** with similarity scores
- **Fallback handling** for low-confidence scenarios

### 2. Multi-Step Planning
- **Automatic query decomposition** for complex requests
- **Sequential execution** with context sharing
- **Tool integration** for email, calendar, CRM, web search
- **Parallel action support** for independent tasks

### 3. Response Validation
- **LLM-based quality checks** for every response
- **Hallucination detection** and prevention
- **Automatic retry** with parameter adjustment
- **Confidence scoring** for transparency

### 4. Semantic Memory
- **Fact extraction** from conversations
- **Long-term storage** with embeddings
- **Context retrieval** for personalized responses
- **Conversation summarization** for quick review

### 5. Self-Improvement
- **Weekly automated learning** from feedback
- **Dynamic parameter tuning** (threshold, top_k, temperature)
- **Knowledge gap identification**
- **A/B testing** for experimental features

### 6. Tool Ecosystem
- **Email integration** (SMTP)
- **Calendar management** (availability, scheduling)
- **CRM operations** (contacts, interactions)
- **Web search** (DuckDuckGo/SerpAPI)

---

## Performance Optimization

### Caching
- **Embedding model caching** (~100MB, loaded once)
- **Session context caching** (in-memory during request)

### Database Indexing
- **Vector indexes** for fast similarity search (IVFFlat)
- **Foreign key indexes** for join optimization
- **Timestamp indexes** for temporal queries

### Async Operations
- **Async database queries** (asyncpg)
- **Parallel tool execution** (asyncio.gather)
- **Background job scheduling** (APScheduler)

### Rate Limiting
- **10 requests/minute** for chat endpoint (per IP)
- Prevents abuse and ensures fair usage

---

## Deployment

**See [DEPLOYMENT.md](./DEPLOYMENT.md) for comprehensive deployment guide**

Quick deployment options:
1. **Railway** - One-click deploy (easiest)
2. **Render** - Auto-deploy from GitHub
3. **AWS EC2** - Full control with systemd service
4. **Docker** - Containerized deployment with docker-compose

---

## Development Workflow

### 1. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
Edit code, add tests, update documentation.

### 3. Run Tests
```bash
pytest
```

### 4. Check Coverage
```bash
pytest --cov=app --cov-report=term-missing
# Ensure coverage >= 60%
```

### 5. Commit Changes
```bash
git add .
git commit -m "feat: Add your feature description"
```

### 6. Run Syntax Checks
```bash
python -m py_compile app/**/*.py
```

---

## Troubleshooting

### Issue: Import Errors
**Solution:** Ensure virtual environment is activated and dependencies are installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: Database Connection Failed
**Solution:** Check `SUPABASE_URL` and `SUPABASE_KEY` in `.env`

### Issue: Groq API Rate Limit
**Solution:** Groq free tier: 14,400 requests/day. Upgrade plan or adjust `RAG_TOP_K` to reduce calls.

### Issue: Email Tool Not Working
**Solution:**
1. Verify SMTP credentials in `.env`
2. For Gmail: Enable 2FA and create App Password
3. Check firewall allows outbound SMTP (port 587)

### Issue: High Memory Usage
**Solution:**
1. Restart server: `pkill -f uvicorn && uvicorn app.main:app --reload`
2. Check embedding model size (all-MiniLM-L6-v2 is ~100MB)
3. Increase server RAM if needed

---

## Monitoring

### Health Endpoint
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "database": "connected"
}
```

### Logs
```bash
tail -f logs/app.log
```

### Weekly Learning Reports
Check background scheduler logs:
```bash
# Scheduler runs every Sunday at 2:00 AM
# View learning job results in logs
grep "weekly_learning" logs/app.log
```

---

## Security

### Authentication
- **JWT tokens** with HS256 algorithm
- **60-minute expiration** for access tokens
- **bcrypt password hashing** with auto-generated salts

### Input Validation
- **Pydantic schemas** for all API inputs
- **SQL injection prevention** via parameterized queries
- **XSS prevention** via React automatic escaping

### Rate Limiting
- **10 requests/minute** for public chat endpoint
- **Per-IP address** tracking

### CORS
- **Restricted origins** (configure in `ALLOWED_ORIGINS`)
- **Credentials support** for authenticated requests

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure test coverage >= 60%
5. Submit pull request with detailed description

---

## License

MIT License - See LICENSE file for details

---

## Support & Resources

- **API Documentation**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **Deployment Guide**: [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Email Support**: support@githafconsulting.com

---

## Version History

### v2.0.0 (January 2025) - Agentic Upgrade
- ✅ Phase 1: Observation Layer (response validation)
- ✅ Phase 2: Planning Layer (multi-step execution)
- ✅ Phase 3: Self-Improvement Loop (automated learning)
- ✅ Phase 4: Advanced Memory (semantic facts + summarization)
- ✅ Phase 5: Tool Ecosystem (email, calendar, CRM, web search)
- ✅ Phase 6: Testing & Polish (comprehensive tests, benchmarks, docs)

### v1.2.0 (October 2024)
- Frontend integration with React dashboard
- Multi-language support (i18n)
- System settings API

### v1.0.0 (September 2024)
- Initial RAG implementation
- FastAPI backend with Groq integration
- Basic admin dashboard

---

**Built with ❤️ for Githaf Consulting**

*For detailed API documentation, see [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)*
*For deployment instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md)*
