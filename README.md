# Gmail Reply Agent

An AI email-reply assistant that drafts replies **in your voice** and gets better
every time you send. Sign in with Google → open an email → the agent drafts a
reply using your persona, your rules, and your past emails → you edit → you send →
it learns from the edit.

It is built as **three cleanly separated subsystems** so each can be taught, run,
and tested on its own:

| Subsystem | Package | One-line job | What you need to run it |
|---|---|---|---|
| **MCP** | `backend/app/mcp/` | Gmail exposed as MCP *tools* over the real protocol | A Google Cloud OAuth client with the Gmail API enabled |
| **RAG** | `backend/app/rag/` | The agent's memory: embed → store → retrieve → learn | A Supabase project with pgvector (+ a 420 MB local embedding model) |
| **Agent** | `backend/app/agent/` | Six small blocks + an orchestrator that turn an email into a draft | An LLM: Ollama locally (default) or a Groq key |

Shared plumbing lives in `backend/app/core/` (database client, crypto, OAuth/JWT,
LLM provider chain). Dependencies point one way and a test enforces it:

```
core  ◀── mcp, rag, agent      core knows nothing about the three subsystems
mcp   ◀── agent, routers       mcp never imports rag or agent
rag   ◀── agent, routers       rag never imports mcp or agent
agent ◀── routers              agent is the ONLY place mcp + rag + llm meet
```

---

## 1. MCP — Gmail as tools (`app/mcp/`)

**Idea.** The agent never calls the Gmail SDK. Gmail is a set of four tools on an
MCP server (`gmail_list_inbox`, `gmail_get_message`, `gmail_get_thread`,
`gmail_send_reply`). The agent and the HTTP routers talk to those tools through
an MCP client, over the real protocol (JSON-RPC over streamable HTTP), even when
client and server run in the same process.

MCP names a handful of roles. The package has **one file per role, read in
order**:

| # | Role | File | What it does |
|---|---|---|---|
| 1 | **Capability** | `gmail.py` | The thing being exposed: a plain Gmail SDK wrapper. Every function takes the caller's OAuth token. No MCP in it. **Imported by `server.py` only.** (`email_parser.py` is its MIME helper.) |
| 2 | **Server** | `server.py` | A `FastMCP` server that owns the four tools. Each tool reads the caller's token from the `X-Gmail-Access-Token` header and delegates to `gmail.py`. Stateless: no stored credentials. |
| 3 | **Transport** | `transport.py` | How the JSON-RPC messages move. Default: **in-process** ASGI transport (no sockets, one deployment). Set `MCP_SERVER_URL` for a remote server. Attaches the per-user token header. |
| 4 | **Client** | `client.py` | `GmailMCPClient(token)`: an `async with` handle holding one session; typed methods call tools and return plain dicts. The only Gmail surface the rest of the app sees. |
| 5 | **Host** | `host.py` | The application that embeds the server: `mcp_lifespan` starts the server's session manager for the app's lifetime, `mount_mcp_server` exposes it at `/mcp-server` for external clients. `main.py` uses both. |

```
agent.tools / routers ──GmailMCPClient(token)──▶ transport ──JSON-RPC──▶ server ──▶ gmail.py ──▶ Gmail API
                                                 host (main.py) keeps the server's session manager running
```

**Keys you need and how to get them.** Everything here comes from one Google
Cloud project ([console.cloud.google.com](https://console.cloud.google.com)).

| Env var | Where it comes from |
|---|---|
| `GOOGLE_CLIENT_ID` | APIs & Services → Credentials → **Create credentials → OAuth client ID** → type *Web application*. Add authorized redirect URI `http://localhost:8001/auth/callback`. Copy the Client ID. |
| `GOOGLE_CLIENT_SECRET` | Same screen, the Client secret. |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8001/auth/callback`, exactly as registered above. |

Before creating the client, do these three one-time steps in the same project,
or sign-in will fail with the errors listed under Gotchas:

1. **Enable the Gmail API**: APIs & Services → Library → search "Gmail API" → Enable.
2. **OAuth consent screen**: User type *External*, publishing status *Testing*.
   Under **Scopes**, add `.../auth/gmail.readonly`, `.../auth/gmail.send`,
   `.../auth/gmail.modify` (plus `openid`, `userinfo.email`, `userinfo.profile`).
3. **Test users**: add every Google account that will sign in. In Testing mode,
   anyone else gets "Access blocked", and refresh tokens expire after 7 days.

No key is needed for the MCP protocol itself: the server is in-process and
stateless, and each request carries the signed-in user's OAuth token.

**Verify it alone.**

```bash
cd backend
uv run python -m app.mcp.server     # 2: lists the tools the server owns
uv run python -m app.mcp.transport  # 3: opens a real session in-process, lists tools over the wire
uv run python -m app.mcp.host       # 5: what main.py wires
uv run python -m app.mcp            # walks all five roles
uv run pytest -q tests/test_mcp.py  # protocol round-trip with the Gmail SDK faked
```

**Teach from.** Run the roles' `__main__` in order 1 → 5. The one line that
bites everyone is the host's lifespan: without the session manager running,
in-process tool calls fail with "Task group is not initialized".

---

## 2. RAG — the agent's memory (`app/rag/`)

**Idea.** One Postgres table, `embeddings`, holds every indexable thing as
768-dim vectors with a `source_type` discriminator (`email`, `rule`,
`modification`, `persona`). Retrieval is a cosine nearest-neighbour search over
that table, scoped to the user. The memory grows after every send.

The package is written as the classic pipeline, **one stage per file, read in
order**:

| # | Stage | File | What it does |
|---|---|---|---|
| 1 | **Load** | `load.py` | A DB record → `Document(source_type, source_id, text, metadata)`. One loader per source type. The only place that knows the records' shape. |
| 2 | **Chunk** | `chunk.py` | Long text → overlapping pieces (≤1200 chars, 150 overlap) that fit the embedding model. Rules, personas and most emails are a single chunk. |
| 3 | **Embed** | `embed.py` | Text → normalized 768-dim vector with `all-mpnet-base-v2`, **locally**. No API, no cost. |
| 4 | **Store** | `store.py` | Chunks + vectors → rows in `embeddings`. Delete-then-insert per source, so re-indexing never leaves stale rows. |
| 5 | **Index** | `index.py` | The glue: `index(user_id, doc)` = load → chunk → embed → store. `index_email`, `index_rule`, `index_persona`, `index_modification` are what the app calls. |
| 6 | **Retrieve** | `retrieve.py` | Query text → embed → `match_embeddings()` (pgvector, HNSW cosine) → best chunk per source. Plus `get_persona`, `get_active_rules`. |
| 7 | **Learn** | `learn.py` | After a send: `archive_sent_email` (store + index the outbound mail) and `store_modification` (store the user's edit with a cheap-LLM "what changed?" summary, then index it). |

**Keys you need and how to get them.** One Supabase project
([supabase.com](https://supabase.com), free tier is enough).

| Env var | Where it comes from |
|---|---|
| `SUPABASE_URL` | Project → Settings → **API** → *Project URL* (`https://<ref>.supabase.co`). |
| `SUPABASE_SERVICE_KEY` | Same page → *Project API keys* → **`service_role`** (not `anon`). It bypasses row-level security, so it lives only in `backend/.env`, never in the frontend. |

Then create the schema: Project → **SQL Editor** → paste and run
`supabase/migrations/001_users.sql`, then `002_full_schema.sql`. The second one
enables the `vector` extension, creates the six tables, the HNSW index, and the
`match_embeddings()` function. `uv run python check_setup.py` confirms all of it.

The embedding model needs no key. It is downloaded once (~420 MB) from Hugging
Face on first use and cached locally.

**Verify it alone.**

```bash
cd backend
uv run python -m app.rag.chunk        # pure: shows a long email splitting into chunks
uv run python -m app.rag.embed        # downloads/loads the model, prints 768 dims
uv run python -m app.rag              # walks load → chunk → embed → (store) → retrieve against the live DB
uv run pytest -q tests/test_rag.py    # load, chunk, index (embed/store faked), retrieve dedupe
```

**Teach from.** Run the stages' `__main__` in order 1 → 7, then open
`index.py` to see them composed, then `retrieve.py` for the read side and the
SQL in `002_full_schema.sql` for the index and the search function.

---

## 3. Agent — six blocks + orchestrator (`app/agent/`)

**Idea.** Every LLM agent here has the same six small, independently testable
blocks: what it is told (system prompt), how it is tuned (config), what it knows
(state), what it is asked (input), what it returns (output), and what it can do
(tools). The orchestrator wires them and is the only place where MCP, RAG, and
the LLM meet.

| # | Block | File | In → Out |
|---|---|---|---|
| 1 | **config** | `config.py` | `AgentConfig`: models, temperature, retrieval knobs. `default()` picks the model for the active `LLM_PROVIDER`. |
| 2 | **system prompt** | `system_prompt.py` | The standing instructions. The only home of the reply system prompt. |
| 3 | **state** | `state.py` | `AgentState.load(user, email)`: persona + rules + RAG neighbours, via `app.rag.retrieval`. |
| 4 | **input** | `input.py` | Renders state + the incoming email into the user prompt. |
| 5 | **output** | `output.py` | Cleans the raw model text into `ReplyAgentOutput{draft, context_used}`. |
| 6 | **tools** | `tools.py` | `AgentTools`: what the agent can *do*. `get_email`, `send_reply` (Gmail over `app.mcp`); `remember_sent_email`, `remember_edit` (memory writes via `app.rag.learning`). `TOOLS` lists them. |
| — | **orchestrator** | `agent.py` | `ReplyAgent.generate_reply()` and `send_reply()`. Every side effect goes through `tools`; the model through `app.core.llm.chat()`. |

```
generate_reply(message_id):
  config → tools.get_email → state (RAG) → system_prompt + input → core.llm.chat → output

send_reply(...):
  tools.get_email → tools.send_reply → tools.remember_sent_email → tools.remember_edit (if edited)
```

**Keys you need and how to get them.** The agent needs one LLM. It reaches it
through `app/core/llm.py`'s provider chain: local → Groq → OpenRouter, trying
cloud providers only if their keys are set.

| Env var | Where it comes from |
|---|---|
| `LLM_PROVIDER` | `local` (default) or `groq`. |
| `LOCAL_LLM_BASE_URL` | Ollama's OpenAI-compatible endpoint, `http://localhost:11434/v1`. |
| `LOCAL_LLM_MODEL` | A model you have pulled, e.g. `llama3.1:8b`. |
| `GROQ_API_KEY` | [console.groq.com/keys](https://console.groq.com/keys) → Create API key. Free tier. **Required** only when `LLM_PROVIDER=groq`; otherwise an optional fallback. |
| `OPENROUTER_API_KEY` | [openrouter.ai/keys](https://openrouter.ai/keys) → Create key. Optional last-resort fallback. |

- **Local (default, no keys).** Install [Ollama](https://ollama.com/download),
  then `ollama pull llama3.1:8b`. Any model Ollama serves works;
  `qwen2.5:7b-instruct` and `gpt-oss:20b` are good alternatives. The first call
  after idle is slow while the model loads into memory.
- **Cloud.** Set `LLM_PROVIDER=groq` and `GROQ_API_KEY`. This is what a Railway
  deployment uses, since there is no Ollama in the cloud.

**Verify it alone.**

```bash
cd backend
uv run python -m app.agent                 # the 6 blocks, no network
uv run python -m app.core.llm              # prints the provider chain
uv run pytest -q tests/test_agent.py tests/test_agent_prompts.py tests/test_core_llm.py
```

**Teach from.** Read the blocks in numeric order, then `agent.py`. Swap the
prompt without touching retrieval; test `output.py` with no LLM; test `tools.py`
with MCP and RAG faked (see `tests/test_agent.py`); change the model in
`config.py` without touching anything else.

---

## Core secrets (shared by all three)

| Env var | How to make it |
|---|---|
| `JWT_SECRET` | `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Signs the 1-hour session token the SPA holds. |
| `ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Fernet key that encrypts Google OAuth tokens before they are written to Supabase. Losing it means every user must sign in again. |

---

## Why these services

- **Supabase** is Postgres with the `pgvector` extension, so the relational
  data (users, personas, rules, emails) and the vector store live in **one**
  database, one connection, one migration file. Its REST API (PostgREST) means
  the backend needs no database driver or ORM, and the HNSW index and the
  `match_embeddings()` function are plain SQL you can read. The free tier is
  enough for a class. The trade-off: free projects pause after a week of
  inactivity, so resume it before class.
- **Ollama** runs the LLM on your laptop for free, with no key and no data
  leaving the machine, which is ideal for teaching. Groq and OpenRouter are the
  cloud options when there is no local GPU/RAM.
- **Vercel** hosts the frontend. The SPA is static files after `vite build`, and
  Vercel serves them from a CDN with a git-push deploy and a free tier. It
  cannot run the backend: Python, a long-lived process, and the in-process MCP
  session manager need a real server.
- **Railway** hosts the backend for that reason: it runs the `Dockerfile` as a
  long-running service, gives it a public URL for `GOOGLE_REDIRECT_URI` and
  `VITE_API_URL`, and holds the secrets as environment variables.

---

## Running the whole app

### Prerequisites

Python 3.12+, Node 18+, [uv](https://github.com/astral-sh/uv), Ollama (or a Groq
key), a Supabase project, a Google Cloud OAuth client. Sections 1 to 3 above say
exactly what to set up for each.

### 1. Install

```bash
cd backend && uv sync
cd ../frontend && npm install
```

### 2. Configure

```bash
cp backend/.env.example backend/.env        # fill in the values
cp frontend/.env.example frontend/.env      # VITE_API_URL=http://localhost:8001
```

Every variable, which subsystem it belongs to, and where to get it:

| Variable | Subsystem | Source |
|---|---|---|
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | MCP (Gmail) | Google Cloud Console, see section 1 |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | RAG (memory) | Supabase project settings, see section 2 |
| `LLM_PROVIDER`, `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL` | Agent (LLM) | Ollama, see section 3 |
| `GROQ_API_KEY`, `OPENROUTER_API_KEY` | Agent (cloud LLM, optional) | console.groq.com/keys, openrouter.ai/keys |
| `JWT_SECRET`, `ENCRYPTION_KEY` | Core (auth) | generate locally, see Core secrets |
| `FRONTEND_URL`, `BACKEND_URL` | Core (ports/CORS) | `http://localhost:5175`, `http://localhost:8001` |
| `VITE_API_URL` (frontend/.env) | Frontend | same as `BACKEND_URL` |

Ports must agree everywhere: backend **8001** (`BACKEND_URL`,
`GOOGLE_REDIRECT_URI`, `VITE_API_URL`, the Google Cloud redirect URI) and frontend
**5175** (`FRONTEND_URL`, `server.port` in `frontend/vite.config.ts`).

### 3. Preflight

```bash
cd backend
uv run python check_setup.py
```

One PASS/FAIL line per thing: every env var, the ports, a live completion from
your LLM, Fernet/JWT validity, all six Supabase tables and `match_embeddings()`,
and the embedding model. Fix until it says READY.

### 4. Run

```bash
# Terminal 1
cd backend && uv run uvicorn app.main:app --reload --port 8001
# Terminal 2
cd frontend && npm run dev
```

Open **http://localhost:5175**, sign in with Google, and on the consent screen
**tick all the Gmail checkboxes**. If you skip them the backend refuses the login
with a 403 that says so.

### 5. Test

```bash
cd backend && uv run pytest -q
```

| Test file | Covers |
|---|---|
| `test_architecture.py` | The package boundaries above. Fails on any cross-subsystem shortcut. |
| `test_mcp.py`, `test_mcp_email_parser.py` | Real MCP round-trip in-process (SDK faked); MIME parsing. |
| `test_agent.py`, `test_agent_prompts.py` | The blocks and their prompts, no network; the tools block with MCP/RAG faked. |
| `test_rag.py` | The pipeline stages with the model and DB faked. |
| `test_core_llm.py`, `test_core_auth.py`, `test_core_crypto.py` | Provider chain order and fallthrough; JWT; Fernet. |
| `test_models.py` | Pydantic schemas. |

---

## HTTP API

| Method | Path | Backed by |
|---|---|---|
| `GET` | `/auth/login`, `/auth/callback`, `/auth/me` | `core.auth` |
| `GET` | `/emails/inbox`, `/emails/{id}`, `/emails/thread/{id}` | `mcp` client |
| `POST` | `/drafts/generate`, `/drafts/send` | `agent` |
| `GET/PUT` | `/settings/persona` · `GET/POST/DELETE` `/settings/rules` | `rag.index` |
| `GET` | `/health` | lists the MCP tools |
| `*` | `/mcp-server` | the Gmail MCP server, for external MCP clients |

Security: the frontend never sees Gmail or OAuth tokens. Tokens are
Fernet-encrypted at rest and decrypted only to be handed to the MCP client.

---

## Gotchas

- **Access blocked / not a test user** → add the Google account as a Test user on the consent screen.
- **"Scope has changed"** (now a 403 from the app) → tick the Gmail checkboxes on consent, or add the Gmail scopes to the consent screen.
- **Google refresh token stopped working** (now a 401) → Testing-mode refresh tokens expire after 7 days; sign in again.
- **`invalid_grant: Missing code verifier`** → the PKCE flow is held in memory; after a backend restart, start login again from the app's button.
- **`.env` changes need a backend restart** (settings are cached).
- **Local model slow on first call** → Ollama loads it into memory; later calls are fast.
- More in `CLAUDE.md` §13.

## Deployment

Backend → Railway (`Dockerfile`, `railway.toml`), frontend → Vercel
(`vercel.json`), database → Supabase. In the cloud there is no Ollama, so set
`LLM_PROVIDER=groq` and a `GROQ_API_KEY`, and update `FRONTEND_URL`,
`BACKEND_URL`, `GOOGLE_REDIRECT_URI`, and `VITE_API_URL` to the public domains.
