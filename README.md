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
│   │   ├── main.py              # FastAPI app entry + MCP server mount/lifespan
│   │   ├── config.py            # Environment config
│   │   ├── dependencies.py      # Auth guards
│   │   ├── agent/               # ★ The reply agent, as 5 composable blocks
│   │   │   ├── config.py            # AgentConfig — models, sampling, retrieval knobs
│   │   │   ├── system_prompt.py     # The agent's standing instructions
│   │   │   ├── state.py             # AgentState — persona, rules, RAG memory
│   │   │   ├── input.py             # Renders state + email → user prompt
│   │   │   ├── output.py            # Parses model text → structured draft
│   │   │   └── agent.py             # ReplyAgent orchestrator (ties the 5 blocks)
│   │   ├── mcp/                 # ★ Gmail tools over the MCP protocol
│   │   │   ├── server.py            # FastMCP server hosting the Gmail tools
│   │   │   ├── connection.py        # Transport + session wiring, token propagation
│   │   │   └── client.py            # GmailMCPClient — typed handle the agent uses
│   │   ├── routers/             # Thin HTTP adapters
│   │   │   ├── auth.py          # Google OAuth login/callback
│   │   │   ├── emails.py        # Inbox/thread/message (via MCP client)
│   │   │   ├── drafts.py        # Draft generate + send (via ReplyAgent)
│   │   │   └── settings.py      # Persona & rules CRUD
│   │   ├── services/           # Reusable internals (not called by routers directly)
│   │   │   ├── gmail_service.py      # Gmail API wrapper (called by MCP tools)
│   │   │   ├── auth_service.py       # OAuth + JWT
│   │   │   ├── llm_service.py        # Groq + OpenRouter (config-driven)
│   │   │   ├── rag_service.py        # Vector search + persona/rules reads
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

## Architecture

The backend is organized around two ideas: the **agent** is decomposed into five
small blocks, and every Gmail side-effect goes through **MCP tools**. Routers are
thin — they translate HTTP to an agent/MCP call and nothing more.

### The agent, in 5 blocks (`app/agent/`)

Each LLM agent is broken into the same five independently-testable blocks:

| Block | File | Responsibility |
|-------|------|----------------|
| **config** | `config.py` | `AgentConfig` — which models, sampling params, how much memory to retrieve. Per-run, not env. |
| **system prompt** | `system_prompt.py` | The agent's standing instructions / role and constraints. |
| **state** | `state.py` | `AgentState` — everything loaded from memory: persona, active rules, and RAG-retrieved similar emails + past edits. |
| **input** | `input.py` | Renders `state` + the incoming email into the model's user prompt. |
| **output** | `output.py` | Parses the raw model text into a clean, structured `ReplyAgentOutput`. |

`agent.py` holds the `ReplyAgent` orchestrator that wires them together:

```
generate_reply(message_id):
  config ─▶ [fetch email via MCP] ─▶ state ─▶ (system_prompt + input) ─▶ LLM ─▶ output
```

### MCP tools: client / server / connection (`app/mcp/`)

The agent never touches the Gmail API directly. Gmail is exposed as **MCP tools**
over the real MCP protocol (JSON-RPC over streamable HTTP), split into three
concerns:

| Concern | File | Responsibility |
|---------|------|----------------|
| **server** | `server.py` | A `FastMCP` server hosting the Gmail tools (`gmail_list_inbox`, `gmail_get_message`, `gmail_get_thread`, `gmail_send_reply`). Each tool reads the caller's OAuth token from the request header and delegates to `gmail_service`. |
| **connection** | `connection.py` | The transport + session wiring. Default transport is **in-process** (an ASGI transport pointed at the mounted server app — no sockets, single deployment) with a **remote** URL mode for a separately-deployed server. Propagates the per-user token as the `X-Gmail-Access-Token` header. |
| **client** | `client.py` | `GmailMCPClient` — a typed `async with` handle the agent/routers use. It wraps an MCP `ClientSession` and turns tool results back into plain dicts. |

```
ReplyAgent / routers
      │  (GmailMCPClient, per-user token)
      ▼
  connection  ──MCP protocol (in-process ASGI or remote HTTP)──▶  server (FastMCP)
                                                                     │
                                                                     ▼
                                                               gmail_service ─▶ Gmail API
```

**Per-user tokens:** the MCP server is stateless and multi-tenant — it carries no
credentials. The client attaches the caller's Gmail OAuth token as a request
header on every call; the server reads it back out per request. The server's
streamable-HTTP session manager is started once in the FastAPI `lifespan`
(required for the in-process client to work) and the same app is also mounted at
`/mcp-server` for external MCP clients.

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

# Optional — MCP tool server. Leave unset to run the Gmail MCP server
# in-process (default). Set to a base URL to reach a remotely-deployed server.
# MCP_SERVER_URL=https://your-backend.example.com
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
| `GET` | `/health` | Health check (also lists exposed MCP tools) |
| `*` | `/mcp-server` | Mounted Gmail **MCP server** (streamable HTTP) for external MCP clients |

---

## How a Reply Is Generated (agent + RAG + MCP)

```
User clicks "Generate Reply"  →  POST /drafts/generate  →  ReplyAgent.generate_reply()
        │
        ▼
  [MCP] GmailMCPClient.get_message()  ── over MCP ──▶  gmail_get_message tool  ──▶  Gmail API
        │            (block: input source; per-user token in X-Gmail-Access-Token header)
        ▼
  STATE: embed the email (all-mpnet-base-v2) → vector search Supabase for similar
         emails + past edits; load persona + active rules
        │
        ▼
  SYSTEM PROMPT + INPUT: assemble the model turns from state + email
        │
        ▼
  MODEL (governed by CONFIG): Groq generates the draft (OpenRouter fallback)
        │
        ▼
  OUTPUT: parse/clean into a structured draft  →  returned to the editor
        │
        ▼
  User reviews/edits in markdown editor  →  POST /drafts/send  →  ReplyAgent.send_reply()
        │
        ▼
  [MCP] gmail_send_reply tool sends in-thread; then archive the sent email and,
        if the user edited the draft, store the before/after diff — both embedded
        so future retrievals reflect the user's preferences (the agent learns).
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

Most modules have a `__main__` self-check. Useful ones:

```bash
cd backend

# Core infra
uv run python -m app.config              # Check env loads
uv run python -m app.utils.crypto        # Test encrypt/decrypt
uv run python -m app.utils.email_parser  # Test email parsing
uv run python -m app.services.embedding_service  # Test embeddings
uv run python -m app.services.llm_service        # Check LLM config
uv run python -m app.db.supabase_client          # Test DB connection

# MCP layer (real protocol, no external calls)
uv run python -m app.mcp.server          # List exposed Gmail tools
uv run python -m app.mcp.connection      # Live in-process MCP roundtrip (lists tools)

# Agent blocks
uv run python -m app.agent.config
uv run python -m app.agent.system_prompt
uv run python -m app.agent.input
uv run python -m app.agent.output
uv run python -m app.agent.agent

# Full test suite (41 tests: infra + MCP roundtrip + agent blocks)
uv run pytest -q
```
