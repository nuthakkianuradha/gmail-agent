# Gmail Reply Agent

AI-powered email reply assistant that learns your writing style over time.

---

## What It Does

1. **Sign in** with your Google account
2. **Browse** your Gmail inbox
3. **Click** an email → AI generates a reply draft using RAG
4. **Review/edit** the draft in a markdown editor
5. **Send** — the agent learns from your edits for future replies

The agent builds a knowledge base from:

- Your past emails (style & context)
- Persona rules you define (tone, signature, instructions)
- Your edit history (learns preferences over time)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + Vite + TypeScript |
| Backend | Python + FastAPI |
| Database | Supabase (PostgreSQL + pgvector) |
| LLM (primary) | Groq (`llama-3.3-70b-versatile`) |
| LLM (fallback) | OpenRouter (`gemini-2.0-flash`) |
| Embeddings | `all-mpnet-base-v2` (local, 768-dim) |
| Auth | Google OAuth 2.0 → JWT sessions |

---

## Project Structure

```
gmail-agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry
│   │   ├── config.py            # Environment config
│   │   ├── dependencies.py      # Auth guards
│   │   ├── routers/
│   │   │   ├── auth.py          # Google OAuth login/callback
│   │   │   ├── emails.py        # Inbox, thread, message
│   │   │   ├── drafts.py        # AI draft generation + send
│   │   │   └── settings.py      # Persona & rules CRUD
│   │   ├── services/
│   │   │   ├── gmail_service.py      # Gmail API wrapper
│   │   │   ├── auth_service.py       # OAuth + JWT
│   │   │   ├── llm_service.py        # Groq + OpenRouter
│   │   │   ├── rag_service.py        # Vector search + prompt assembly
│   │   │   ├── embedding_service.py  # Sentence-transformers
│   │   │   ├── modification_service.py
│   │   │   └── archive_service.py
│   │   ├── models/              # Pydantic schemas
│   │   ├── db/                  # Supabase client
│   │   └── utils/               # Crypto, email parser, prompts
│   ├── Dockerfile
│   └── railway.toml
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Router setup
│   │   ├── pages/               # Login, Inbox, EmailThread, Settings
│   │   ├── components/          # EmailList, EmailThread, DraftEditor
│   │   ├── api/                 # API client + endpoint wrappers
│   │   ├── store/               # Zustand state management
│   │   └── types/               # TypeScript interfaces
│   └── vercel.json
└── supabase/
    └── migrations/              # SQL schema files
```

---

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Supabase project
- Google Cloud project with OAuth 2.0 credentials
- Groq API key
- OpenRouter API key

### 1. Clone & Install

```bash
# Backend
cd backend
uv venv && uv pip install -e .

# Frontend
cd frontend
npm install
```

### 2. Configure Environment

**backend/.env**

```env
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key

GROQ_API_KEY=gsk_...
OPENROUTER_API_KEY=sk-or-v1-...

JWT_SECRET=your_random_secret
ENCRYPTION_KEY=your_fernet_key

FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
```

> Generate `ENCRYPTION_KEY`:
> ```bash
> python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
> ```

**frontend/.env**

```env
VITE_API_URL=http://localhost:8000
```

### 3. Google Cloud Setup

1. Create an **OAuth 2.0 Client ID** (Web application)
2. Add redirect URI: `http://localhost:8000/auth/callback`
3. Enable the **Gmail API**
4. Go to **OAuth consent screen** → add your email as a **test user**

### 4. Supabase Setup

Run these SQL files in order in your Supabase **SQL Editor**:

1. `supabase/migrations/001_users.sql`
2. `supabase/migrations/002_full_schema.sql`

### 5. Run

```bash
# Terminal 1 — Backend
cd backend
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

Open **http://localhost:5173**

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/auth/login` | Redirect to Google OAuth |
| `GET` | `/auth/callback` | Handle OAuth callback |
| `GET` | `/auth/me` | Current user profile |
| `GET` | `/emails/inbox` | List inbox (paginated) |
| `GET` | `/emails/{id}` | Get full email |
| `GET` | `/emails/thread/{id}` | Get email thread |
| `POST` | `/drafts/generate` | Generate AI reply draft |
| `POST` | `/drafts/send` | Send reply (archives + learns) |
| `GET` | `/settings/persona` | Get persona |
| `PUT` | `/settings/persona` | Update persona |
| `GET` | `/settings/rules` | List rules |
| `POST` | `/settings/rules` | Create rule |
| `DELETE` | `/settings/rules/{id}` | Delete rule |
| `GET` | `/health` | Health check |

---

## How the RAG Pipeline Works

```
User clicks "Generate Reply"
        │
        ▼
  Embed incoming email (all-mpnet-base-v2)
        │
        ▼
  Vector search Supabase (similar emails + past modifications)
        │
        ▼
  Fetch persona + active rules
        │
        ▼
  Assemble prompt with all context
        │
        ▼
  Groq LLM generates draft (OpenRouter fallback)
        │
        ▼
  User reviews/edits in markdown editor
        │
        ▼
  On send: archive email, store edit diff, embed for future use
```

---

## Deployment

| Service | Platform | Config |
|---------|----------|--------|
| Backend | Railway | `Dockerfile` + `railway.toml` |
| Frontend | Vercel | `vercel.json` |
| Database | Supabase | Hosted PostgreSQL + pgvector |

Update `FRONTEND_URL`, `BACKEND_URL`, and `GOOGLE_REDIRECT_URI` for production domains.

---

## Verify Installation

```bash
cd backend
uv run python -m app.config              # Check env loads
uv run python -m app.utils.crypto        # Test encrypt/decrypt
uv run python -m app.utils.email_parser  # Test email parsing
uv run python -m app.services.embedding_service  # Test embeddings
uv run python -m app.services.llm_service        # Check LLM config
uv run python -m app.db.supabase_client          # Test DB connection
```
