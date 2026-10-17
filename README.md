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
| **Agent** | `backend/app/agent/` | Five small blocks + an orchestrator that turn an email into a draft | An LLM: Ollama locally (default) or a Groq key |

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

| File | Role |
|---|---|
| `gmail.py` | The raw Google SDK wrapper. Every function takes the caller's OAuth token explicitly. **Imported by `server.py` only.** |
| `email_parser.py` | MIME/payload parsing used by `gmail.py`. |
| `server.py` | `FastMCP` server defining the four tools. Each tool reads the caller's token from the `X-Gmail-Access-Token` header and delegates to `gmail.py`. Stateless: no stored credentials. |
| `connection.py` | Transport + session wiring. Default: **in-process** ASGI transport (no sockets, one deployment). Set `MCP_SERVER_URL` for a remote server. Attaches the per-user token header. |
| `client.py` | `GmailMCPClient(token)`: an `async with` handle whose methods call tools and return plain dicts. The only Gmail surface the rest of the app sees. |

**What you need.**

1. A Google Cloud project with an **OAuth 2.0 Client ID** (type: Web application).
2. Authorized redirect URI: `http://localhost:8001/auth/callback`.
3. **Gmail API enabled** in the project.
4. On the **OAuth consent screen**: add scopes `gmail.readonly`, `gmail.send`,
   `gmail.modify`, and add your Google account as a **Test user**.
5. `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` in `backend/.env`.

**Verify it alone.**

```bash
cd backend
uv run python -m app.mcp            # real MCP session in-process; lists the 4 tools
uv run pytest -q tests/test_mcp.py  # protocol round-trip with the Gmail SDK faked
```

**Teach from.** `server.py` (what a tool is), `connection.py` (one protocol, two
transports), `client.py` (why the agent sees dicts, not Google objects). The
critical wiring: the server's session manager is started in the FastAPI
`lifespan` in `main.py`. Without it, in-process tool calls fail with
"Task group is not initialized".

---

## 2. RAG — the agent's memory (`app/rag/`)

**Idea.** One Postgres table, `embeddings`, holds every indexable thing as a
768-dim vector with a `source_type` discriminator (`email`, `rule`,
`modification`, `persona`). Retrieval is a cosine nearest-neighbour search over
that table, scoped to the user. The memory grows after every send.

| File | Role |
|---|---|
| `embeddings.py` | `encode(text)` with `all-mpnet-base-v2`, **locally** via sentence-transformers. No API, no cost. |
| `indexing.py` | **Write side.** `index_email`, `index_rule`, `index_persona`, `index_modification`: text → vector → upsert. |
| `retrieval.py` | **Read side.** `retrieve_context` calls the `match_embeddings` SQL function (pgvector, HNSW cosine index). Plus `get_persona`, `get_active_rules`. |
| `learning.py` | **Feedback loop.** After a send: `archive_sent_email` (store + index the outbound mail) and `store_modification` (store the user's edit with a cheap-LLM "what changed?" summary, then index it). |

**What you need.**

1. A **Supabase** project. Copy the Project URL and the **service_role** key to
   `SUPABASE_URL` / `SUPABASE_SERVICE_KEY`.
2. Run both migrations in the Supabase **SQL Editor**, in order:
   `supabase/migrations/001_users.sql`, then `002_full_schema.sql` (enables
   pgvector, creates the tables, the HNSW index, and `match_embeddings()`).
3. Disk + one-time download: the embedding model (~420 MB) is fetched on first use.

**Verify it alone.**

```bash
cd backend
uv run python -m app.rag.embeddings   # downloads/loads the model, prints 768 dims
uv run python -m app.rag              # model + Supabase reachability + a vector search
```

**Teach from.** `indexing.py` next to `retrieval.py` (write vs read of the same
table), then `learning.py` (why every send makes the next draft better). The SQL
function and index live in `002_full_schema.sql`.

---

## 3. Agent — five blocks + orchestrator (`app/agent/`)

**Idea.** Every LLM agent here has the same five small, independently testable
blocks. The orchestrator wires them, and is the only place where MCP, RAG, and
the LLM meet.

| # | Block | File | In → Out |
|---|---|---|---|
| 1 | **config** | `config.py` | `AgentConfig`: models, temperature, retrieval knobs. `default()` picks the model for the active `LLM_PROVIDER`. |
| 2 | **system prompt** | `system_prompt.py` | The standing instructions. The only home of the reply system prompt. |
| 3 | **state** | `state.py` | `AgentState.load(user, email)`: persona + rules + RAG neighbours, via `app.rag.retrieval`. |
| 4 | **input** | `input.py` | Renders state + the incoming email into the user prompt. |
| 5 | **output** | `output.py` | Cleans the raw model text into `ReplyAgentOutput{draft, context_used}`. |
| — | **orchestrator** | `agent.py` | `ReplyAgent.generate_reply()` and `send_reply()`. Gmail via `app.mcp`, memory via `app.rag`, model via `app.core.llm.chat()`. |

```
generate_reply(message_id):
  config → [MCP: get_message] → state (RAG) → system_prompt + input → core.llm.chat → output

send_reply(...):
  [MCP: send_reply] → rag.learning.archive_sent_email → rag.learning.store_modification (if edited)
```

**What you need.** An LLM, through `app/core/llm.py`'s provider chain
(local → Groq → OpenRouter; cloud providers only if their keys are set).

- **Local (default).** Install [Ollama](https://ollama.com), then
  `ollama pull llama3.1:8b`. In `.env`: `LLM_PROVIDER=local`,
  `LOCAL_LLM_MODEL=llama3.1:8b`. No keys needed. Any model Ollama serves works;
  `qwen2.5:7b-instruct` and `gpt-oss:20b` are good alternatives.
- **Cloud.** `LLM_PROVIDER=groq` + `GROQ_API_KEY`. `OPENROUTER_API_KEY` is an
  optional last-resort fallback in either mode.

**Verify it alone.**

```bash
cd backend
uv run python -m app.agent                 # the 5 blocks, no network
uv run python -m app.core.llm              # prints the provider chain
uv run pytest -q tests/test_agent.py tests/test_agent_prompts.py tests/test_core_llm.py
```

**Teach from.** Read the blocks in numeric order, then `agent.py`. Swap the
prompt without touching retrieval; test `output.py` with no LLM; change the model
in `config.py` without touching anything else.

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

Generate the two secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"                               # JWT_SECRET
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # ENCRYPTION_KEY
```

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
| `test_agent.py`, `test_agent_prompts.py` | The five blocks and their prompts, no network. |
| `test_core_llm.py`, `test_core_auth.py`, `test_core_crypto.py` | Provider chain order and fallthrough; JWT; Fernet. |
| `test_models.py` | Pydantic schemas. |

---

## HTTP API

| Method | Path | Backed by |
|---|---|---|
| `GET` | `/auth/login`, `/auth/callback`, `/auth/me` | `core.auth` |
| `GET` | `/emails/inbox`, `/emails/{id}`, `/emails/thread/{id}` | `mcp` client |
| `POST` | `/drafts/generate`, `/drafts/send` | `agent` |
| `GET/PUT` | `/settings/persona` · `GET/POST/DELETE` `/settings/rules` | `rag.indexing` |
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
