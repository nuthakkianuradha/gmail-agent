# Gmail Reply Agent

## Project Overview
AI-powered Gmail reply agent. Users log in with Google, browse their Primary inbox, click an email to generate an AI draft reply, review/edit it, and send. The agent learns from past emails, user-defined persona/rules, and modification history via RAG.

## Tech Stack
- **Frontend**: React + Vite + TypeScript (deploy: Vercel)
- **Backend**: Python + FastAPI (deploy: Railway)
- **Database**: Supabase (PostgreSQL + pgvector)
- **LLMs**: Groq (primary) + OpenRouter (fallback), both via OpenAI-compatible API
- **Embeddings**: `all-mpnet-base-v2` (local, 768-dim)
- **Auth**: Google OAuth → JWT sessions
- **Draft Editor**: Markdown-based (`@uiw/react-md-editor`)

## Monorepo Structure
```
gmail-agent/
├── frontend/          # React + Vite SPA
│   └── src/
│       ├── api/       # API client, auth, emails, drafts, settings
│       ├── pages/     # LoginPage, InboxPage, EmailThreadPage, SettingsPage
│       ├── components/# EmailList, EmailCard, DraftEditor, PersonaForm, etc.
│       ├── hooks/     # useAuth, useInbox, useThread, useDraft
│       ├── store/     # zustand stores (auth, inbox, settings)
│       └── types/     # TypeScript interfaces
├── backend/           # Python FastAPI
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── dependencies.py
│       ├── routers/   # auth, emails, drafts, settings
│       ├── services/  # gmail, auth, llm, rag, embedding, modification, archive
│       ├── models/    # Pydantic models
│       ├── db/        # Supabase client, queries
│       └── utils/     # crypto, email_parser, prompt_templates
├── supabase/
│   └── migrations/    # SQL migration files
└── idea.md
```

## Key Commands
- **Backend dev**: `cd backend && uvicorn app.main:app --reload`
- **Frontend dev**: `cd frontend && npm run dev`
- **Install backend deps**: `cd backend && pip install -e .`
- **Install frontend deps**: `cd frontend && npm install`

## Architecture Rules
- Frontend NEVER touches Gmail API or OAuth tokens directly — all via backend
- OAuth tokens encrypted at rest with Fernet
- Single unified `embeddings` table with `source_type` discriminator (not separate tables per type)
- Groq is primary LLM (fast), OpenRouter is fallback
- Embeddings run locally on backend server (no external API)
- Primary inbox only, single Gmail account per user (for now)

## Supabase Tables
- `users` — Google ID, encrypted tokens, profile
- `emails` — archived sent + indexed inbox emails
- `personas` — one per user (tone, style, signature, instructions)
- `rules` — multiple per user (individual rules)
- `modifications` — before/after drafts with diff summaries
- `embeddings` — unified vector store with HNSW index

## Environment Variables
### Backend
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- `GROQ_API_KEY`, `OPENROUTER_API_KEY`
- `JWT_SECRET`, `ENCRYPTION_KEY`
- `FRONTEND_URL`, `BACKEND_URL`

### Frontend
- `VITE_API_URL`
