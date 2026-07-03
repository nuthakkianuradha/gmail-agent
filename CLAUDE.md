# Gmail Reply Agent

> AI email-reply assistant. Sign in with Google → browse your Primary inbox →
> click an email → the agent drafts a reply in *your* voice using RAG over your
> history → review/edit in a markdown editor → send. Every send teaches it more.

This file is the architectural source of truth. It explains **what each part is
for, how the pieces connect, and how the agent is organized into 5 blocks with
Gmail exposed over MCP.**

---

## 1. Problem statement — what this solves

Writing email replies is repetitive and voice-sensitive. A generic LLM draft
sounds nothing like you and ignores your context. This app solves that by
grounding every draft in three sources of truth and improving from feedback:

| Problem | How it's solved |
|---|---|
| Drafts don't sound like the user | **Persona** (tone/style/signature) + **rules**, injected into every prompt |
| Drafts ignore prior context/relationships | **RAG** over the user's past emails (vector search) |
| The model repeats mistakes the user keeps fixing | **Learning loop**: every user edit is diffed, summarized, embedded, and retrieved next time |
| Secrets/PII must not leak to the browser | Frontend never sees Gmail API or OAuth tokens; backend holds them, **encrypted at rest** |
| Gmail access should be a clean, swappable capability | Gmail is exposed as **MCP tools**, not called ad hoc |

**Scope (current):** Primary inbox only, one Gmail account per user, reply drafting
(not full autonomous send). English-first but persona has a `language` field.

---

## 2. Tech stack & infrastructure

| Layer | Choice | Why / notes |
|---|---|---|
| Frontend | React + Vite + TypeScript | SPA; deploy on **Vercel** |
| Backend | Python + FastAPI (ASGI/uvicorn) | async; deploy on **Railway** |
| DB | Supabase = Postgres + **pgvector** | relational data **and** vector store in one place |
| Vector index | HNSW, cosine (`vector_cosine_ops`) | fast ANN over 768-dim embeddings |
| LLM (primary) | **Groq** `llama-3.3-70b-versatile` | fast; OpenAI-compatible API |
| LLM (fallback) | **OpenRouter** `google/gemini-2.0-flash-001` | used only if Groq call throws |
| Diff summarizer | Groq `llama-3.1-8b-instant` | cheap model for "what did the user change?" |
| Embeddings | `all-mpnet-base-v2`, 768-dim, **local** | via `sentence-transformers`, normalized; no embedding API cost/latency |
| Tool protocol | **MCP** (`mcp` SDK / FastMCP), streamable HTTP | Gmail exposed as tools over the real protocol |
| Auth | Google OAuth 2.0 (**PKCE**) → JWT | Gmail scopes; JWT (HS256, 1h) for the SPA session |
| Token security | **Fernet** symmetric encryption | OAuth access+refresh tokens encrypted before DB write |
| Package mgr (backend) | **uv** | use `uv` (not pip/venv) for installs/sync |

**Runtime processes in dev:** one FastAPI process (serves REST **and** hosts the
MCP server in-process) + one Vite dev server. Ports are configurable via env —
code defaults are backend `8000` / frontend `5173`, but this project's `.env`
uses backend `8001` / frontend `5175` (must match `GOOGLE_REDIRECT_URI`,
`FRONTEND_URL`, and `VITE_API_URL`).

---

## 3. Repository layout

```
gmail-agent/
├── backend/                     # FastAPI + agent + MCP
│   └── app/
│       ├── main.py              # ASGI entry: routers + CORS + MCP mount + lifespan
│       ├── config.py            # Pydantic Settings (env), lru_cached
│       ├── dependencies.py      # get_current_user (JWT auth guard)
│       │
│       ├── agent/               # ★ THE AGENT — 5 blocks + orchestrator (see §6)
│       │   ├── config.py            # block: config   (AgentConfig)
│       │   ├── system_prompt.py     # block: system prompt
│       │   ├── state.py             # block: state    (AgentState: memory)
│       │   ├── input.py             # block: input    (prompt assembly)
│       │   ├── output.py            # block: output   (parse/clean result)
│       │   └── agent.py             # ReplyAgent orchestrator (ties the 5 blocks)
│       │
│       ├── mcp/                 # ★ Gmail-as-tools over MCP (see §7)
│       │   ├── server.py            # FastMCP server + Gmail tools
│       │   ├── connection.py        # transport/session wiring + token header
│       │   └── client.py            # GmailMCPClient (typed handle)
│       │
│       ├── routers/             # Thin HTTP adapters (no business logic)
│       │   ├── auth.py          #   /auth   OAuth login/callback, /me
│       │   ├── emails.py        #   /emails inbox/message/thread (via MCP client)
│       │   ├── drafts.py        #   /drafts generate/send (via ReplyAgent)
│       │   └── settings.py      #   /settings persona + rules CRUD
│       │
│       ├── services/            # Reusable internals (not called by routers directly)
│       │   ├── gmail_service.py     # Google Gmail SDK calls (ONLY called by MCP tools)
│       │   ├── auth_service.py      # OAuth flow, JWT, token encrypt/refresh
│       │   ├── llm_service.py       # Groq→OpenRouter chat completions
│       │   ├── rag_service.py       # vector search + persona/rules reads + indexers
│       │   ├── embedding_service.py # local sentence-transformers encode()
│       │   ├── modification_service.py # store + embed user edits (learning)
│       │   └── archive_service.py   # persist + embed sent emails
│       │
│       ├── models/              # Pydantic request/response schemas
│       ├── db/supabase_client.py# lru_cached Supabase client (service key)
│       ├── utils/               # crypto (Fernet), email_parser, prompt_templates
│       └── tests/               # pytest: infra + MCP roundtrip + agent blocks
│
├── frontend/                    # React SPA (see §9)
│   └── src/{api,pages,components,store,types}
│
└── supabase/migrations/         # 001_users.sql, 002_full_schema.sql
```

---

## 4. How a request flows (end-to-end connections)

**Frontend ⇄ Backend:** the SPA uses an axios client (`frontend/src/api/client.ts`)
with `baseURL = VITE_API_URL`. After login the JWT is stored in `localStorage`
and attached as `Authorization: Bearer <jwt>` on every call; a `401` clears it
and redirects to `/login`. The frontend **never** touches Gmail or OAuth tokens.

### 4a. Login (OAuth → JWT)
```
Browser → GET /auth/login
  auth_service.get_authorization_url()  → builds PKCE flow, stores it in-memory
  → 307 redirect to Google consent (Gmail scopes)
Google → GET /auth/callback?code&state
  exchange_code_for_tokens()  → fetch_token (uses stored PKCE verifier)
  get_google_user_info()      → profile
  upsert_user()               → Fernet-encrypt access+refresh tokens → users table
  create_jwt()                → 1h HS256 token
  → redirect to  FRONTEND_URL/auth/callback?token=<jwt>
```
Auth guard: `dependencies.get_current_user` decodes the JWT and loads the user row.

### 4b. Generate a draft (the core path)
```
POST /drafts/generate  → routers/drafts → ReplyAgent(user).generate_reply(msg_id)
  1. CONFIG        AgentConfig.default()
  2. [MCP] fetch   GmailMCPClient.get_message(id) ──MCP──▶ gmail_get_message tool ──▶ Gmail API
  3. STATE         AgentState.load(): embed email → match_embeddings (pgvector)
                   → similar past emails + past edits; + persona + active rules
  4. SYSTEM+INPUT  build_system_prompt() + build_input(email, state)
  5. MODEL         llm_service.generate_draft() Groq→OpenRouter (per config)
  6. OUTPUT        parse_output() → {draft, context_used}
  → DraftGenerateResponse
```

### 4c. Send (and learn)
```
POST /drafts/send  → ReplyAgent(user).send_reply(...)
  [MCP] get_message (for Message-ID threading header)
  [MCP] gmail_send_reply  ──MCP──▶ Gmail API (in-thread reply)
  archive_service.archive_sent_email()  → emails table (outbound) + embed it
  if user edited draft: modification_service.store_modification()
        → summarize_diff (LLM) → modifications table + embed the before/after
```
Reading inbox/message/thread (`/emails/*`) also goes **through the MCP client** —
routers decrypt the token and hand it to `GmailMCPClient`.

---

## 5. Key invariant: all Gmail access goes through MCP

`gmail_service.py` (the raw Google SDK wrapper) is imported by **exactly one
place — `app/mcp/server.py`**. Nothing else calls Gmail directly. Routers and the
agent use `GmailMCPClient`. Keep it that way: new Gmail capability = a new MCP
tool in `server.py` + a method on `GmailMCPClient`, not a direct SDK call.

---

## 6. The Agent — organized as 5 blocks (`app/agent/`)

Every LLM agent here is decomposed into the same five small, independently
testable blocks, plus an orchestrator. The blocks are pure/leaf where possible so
they can be unit-tested without DB/LLM/network.

| # | Block | File | What it does | In → Out |
|---|---|---|---|---|
| 1 | **config** | `config.py` | `AgentConfig` (frozen dataclass): which models, `temperature`, `max_tokens`, and retrieval knobs (`match_count=8`, `match_threshold=0.4`, `memory_source_types=('email','modification')`). Per-run behavior, **not** env. | — → `AgentConfig` |
| 2 | **system prompt** | `system_prompt.py` | Owns the agent's standing instructions/role/constraints. `build_system_prompt()` returns the system turn. Canonical home of `REPLY_SYSTEM_PROMPT`. | — → `str` |
| 3 | **state** | `state.py` | `AgentState.load(user_id, email, config)` gathers everything from **memory**: persona, active rules, and RAG-retrieved similar emails + past edits (via `rag_service`). `context_count` = items retrieved. | email → `AgentState` |
| 4 | **input** | `input.py` | Renders `state` + the incoming email into the model's **user prompt** (`build_input`). Canonical home of `REPLY_INPUT_TEMPLATE`. Duck-typed on `state` to avoid import cycles. | (email, state) → `str` |
| 5 | **output** | `output.py` | `parse_output(raw, context_used)` cleans the model text (strips fences/quotes/whitespace) into a structured `ReplyAgentOutput{draft, context_used}`. | raw text → `ReplyAgentOutput` |
| — | **orchestrator** | `agent.py` | `ReplyAgent(user, config)` wires the blocks for `generate_reply()` and `send_reply()`. Holds the decrypted token **only** to hand to the MCP client; delegates archiving/learning to services. | — |

**Data flow inside `generate_reply`:**
`config → (MCP fetch email) → state → (system_prompt + input) → LLM → output`.

**Why blocks:** each concern is swappable and testable in isolation (e.g. change
the prompt without touching retrieval; test output parsing with no LLM). To add a
second agent, reuse the same 5-block shape.

> Prompt strings live in the blocks (`system_prompt.py`, `input.py`).
> `utils/prompt_templates.py` **re-exports** them as `DRAFT_SYSTEM_PROMPT` /
> `DRAFT_PROMPT` for backward compatibility (`DIFF_SUMMARY_PROMPT` still lives
> there). Don't eagerly import submodules in `agent/__init__.py` — it would cause
> an import cycle through `prompt_templates`.

---

## 7. The MCP layer — client / server / connection (`app/mcp/`)

Gmail is exposed as **MCP tools** over the real protocol (JSON-RPC over
streamable HTTP). Split into three concerns:

| Concern | File | Responsibility |
|---|---|---|
| **server** | `server.py` | `build_gmail_mcp()` builds a `FastMCP` (stateless HTTP, DNS-rebinding off) hosting tools: `gmail_list_inbox`, `gmail_get_message`, `gmail_get_thread`, `gmail_send_reply`. Each reads the caller's token from the request header and delegates to `gmail_service`. Module singletons `mcp` / `mcp_asgi_app` are used in production; the factory lets tests spin up isolated instances (a session manager runs once per instance). |
| **connection** | `connection.py` | Transport + session wiring. `open_session(access_token)` yields an initialized `ClientSession`. **Default transport = in-process** (`httpx.ASGITransport` at `mcp_asgi_app`, no sockets → single Railway service, testable). **Remote mode** via `MCP_SERVER_URL` (networked streamable HTTP). Propagates the token as the `X-Gmail-Access-Token` header. |
| **client** | `client.py` | `GmailMCPClient(token)` — an `async with` handle wrapping a `ClientSession`; methods (`get_message`, `send_reply`, …) call tools and parse results back to dicts. The only Gmail surface the agent/routers see. |

**Per-user tokens:** the MCP server is stateless and carries no credentials. The
client attaches the user's Gmail OAuth token per request; the server reads it back
per request. **Critical wiring:** the streamable-HTTP session manager is started
in the FastAPI **`lifespan`** (`main.py`) — without it, in-process tool calls fail
with *"Task group is not initialized."* The same app is mounted at `/mcp-server`
for external MCP clients / remote-mode deployments.

```
ReplyAgent / routers ──GmailMCPClient(token)──▶ connection ──MCP protocol──▶ server (FastMCP)
                                                (in-process ASGI or remote HTTP)      │
                                                                            gmail_service ─▶ Gmail API
```

---

## 8. Data model (Supabase)

Migrations: `001_users.sql` (uuid-ossp + `users`), `002_full_schema.sql`
(pgvector + everything else). Idempotent (`create ... if not exists`). Run in the
Supabase **SQL Editor** for the project your `SUPABASE_URL` points at.

| Table | Cardinality | Purpose / key columns |
|---|---|---|
| `users` | 1/user | `google_id`, `email`, profile, `access_token_encrypted`, `refresh_token_encrypted`, `token_expiry` (Fernet-encrypted tokens) |
| `emails` | many/user | archived sent (`outbound`) + indexed inbox (`inbound`); `gmail_message_id/thread_id`, addresses, `subject`, `body_text/html`, `labels` |
| `personas` | **1/user** (unique) | `tone` (default 'professional'), `style_notes`, `signature`, `language`, `custom_instructions` |
| `rules` | many/user | `rule_text`, `category`, `is_active`, `priority` |
| `modifications` | many/user | `draft_before`, `draft_after`, `diff_summary`, original subject/snippet — the learning record |
| `embeddings` | many/user | **unified** vector store: `source_type` ∈ {email, rule, modification, persona}, `source_id`, `content_text`, `embedding vector(768)`, `metadata jsonb` |

**Vector search:** `embeddings` has an HNSW cosine index (`m=16,
ef_construction=64`). The `match_embeddings(query_embedding, query_user_id,
filter_source_types, match_threshold, match_count)` SQL function returns rows with
`similarity = 1 - cosine_distance`, filtered per user + source type + threshold,
ordered by distance. The agent's `state` block calls it via
`rag_service.retrieve_context` (threshold 0.4, count 8, sources email+modification).

**Unified embeddings design:** one table with a `source_type` discriminator (not a
table per type). Every indexable thing — sent emails, rules, modifications,
persona — is embedded into it via the `index_*` functions in `rag_service`, and
kept in sync when settings change (e.g. deleting a rule deletes its embedding).

---

## 9. Frontend (`frontend/src/`)

SPA (React Router). Routes: `/login`, `/auth/callback` (captures `?token`),
protected `/inbox`, `/email/:threadId`, `/settings`. Auth state in a Zustand store
(`store/authStore.ts`); token in `localStorage`. API wrappers in `api/`
(`emails.ts`, `drafts.ts`, `settings.ts`) all go through the shared axios `client`.
Draft editing uses a markdown editor (`@uiw/react-md-editor`). The frontend calls
only the backend REST API — it has no knowledge of Gmail, MCP, or the agent.

---

## 10. Configuration & environment

Backend settings load from `backend/.env` via `config.Settings` (Pydantic,
`lru_cache`d — **a change requires a backend restart** to take effect).

**Backend env:**
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` ·
`SUPABASE_URL`, `SUPABASE_SERVICE_KEY` · `GROQ_API_KEY`, `OPENROUTER_API_KEY` ·
`JWT_SECRET`, `ENCRYPTION_KEY` (Fernet) · `FRONTEND_URL`, `BACKEND_URL` ·
`MCP_SERVER_URL` (optional — unset = in-process MCP; set = remote MCP server).

**Frontend env:** `VITE_API_URL` (must equal the backend URL/port).

Generate `ENCRYPTION_KEY`:
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

---

## 11. Commands

```bash
# Backend (use uv)
cd backend
uv sync                                   # install/sync deps
uv run uvicorn app.main:app --reload      # dev server (respects BACKEND_URL port via --port)
uv run pytest -q                          # full test suite (infra + MCP roundtrip + agent)

# Frontend
cd frontend
npm install
npm run dev                               # Vite dev server

# Module self-checks (most modules have a __main__)
uv run python -m app.mcp.connection       # live in-process MCP roundtrip
uv run python -m app.agent.agent          # agent block wiring
uv run python -m app.db.supabase_client   # DB connectivity
```

**Convention:** every backend module ends with an `if __name__ == "__main__":`
smoke check. Preserve this when adding modules.

---

## 12. Architecture rules (invariants — keep these true)

- Frontend **never** touches Gmail API or OAuth tokens — everything via backend.
- **All Gmail access goes through MCP tools.** `gmail_service` is called only by
  `app/mcp/server.py`. Routers/agent use `GmailMCPClient`.
- OAuth tokens are **Fernet-encrypted** at rest; decrypted only to pass to the MCP
  client (which forwards to the Gmail tools).
- The agent stays in **5 blocks + orchestrator**; keep blocks small and testable.
- Prompt strings live in the agent blocks; `prompt_templates` only re-exports.
- **Single unified `embeddings` table** with a `source_type` discriminator.
- Groq is primary, OpenRouter is fallback; embeddings run **locally** (no API).
- The MCP session manager must be started in the FastAPI `lifespan`.
- Routers are thin adapters — business logic lives in the agent/services.
- Primary inbox only, single Gmail account per user (current scope).

---

## 13. Known gotchas (bit us before — read before debugging login/DB)

- **OAuth "Access blocked / not a test user":** app is in Testing mode; add the
  Google account as a **Test user** on the OAuth consent screen.
- **"Scope has changed …":** Google didn't grant the Gmail scopes — **enable the
  Gmail API** in the Cloud project and add the 3 gmail scopes to the consent
  screen, then re-consent (tick all permission boxes).
- **`[Errno 8] nodename … not known`:** `SUPABASE_URL` host doesn't resolve —
  project paused/deleted or wrong URL. Resume it, or fix `.env` + restart backend.
- **`PGRST205 … table not found`:** migrations not run against the project in
  `SUPABASE_URL`. Run `001` then `002` in that project's SQL Editor.
- **`invalid_grant: Missing code verifier`:** the PKCE flow is stored **in-memory**
  (`auth_service._pending_flows`), so it's lost on backend restart / multiple
  workers. Start login fresh after any restart; don't reuse an old Google tab.
  (Hardening candidate: persist the `code_verifier` keyed by `state`.)
- **`.env` changes need a restart** — settings are `lru_cache`d.
- **Ports must line up:** `GOOGLE_REDIRECT_URI`, `FRONTEND_URL`, `VITE_API_URL`,
  and CORS `allow_origins` all reference the same backend/frontend ports.
