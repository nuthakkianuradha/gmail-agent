"""PRE-WORK · run this BEFORE Week 5 Day 1.

    cd backend
    uv run python check_setup.py

It checks every credential and every service the app needs, prints one PASS or
FAIL line per item, and tells you exactly what to fix. Nothing is changed.

It also DOWNLOADS THE EMBEDDING MODEL (~420 MB) the first time. That download
is the single most common way a class loses twenty minutes, so get it out of
the way at home, on your own wifi.

Run it until every line says PASS. If something fails, the line underneath
tells you where to go and what to paste.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# ── tiny reporter ────────────────────────────────────────────────────────
PASS, FAIL, WARN = "PASS", "FAIL", "WARN"
_results: list[tuple[str, str]] = []


def say(status: str, label: str, detail: str = "") -> None:
    mark = {"PASS": "  ok  ", "FAIL": " FAIL ", "WARN": " warn "}[status]
    print(f"[{mark}] {label}")
    if detail:
        for line in detail.splitlines():
            print(f"          {line}")
    _results.append((status, label))


def section(title: str) -> None:
    print(f"\n{'─' * 68}\n{title}\n{'─' * 68}")


# ══════════════════════════════════════════════════════════════════════
section("1 · PYTHON AND THE PROJECT")
# ══════════════════════════════════════════════════════════════════════

v = sys.version_info
if v >= (3, 10):
    say(PASS, f"Python {v.major}.{v.minor}.{v.micro}")
else:
    say(FAIL, f"Python {v.major}.{v.minor}", "Need 3.10 or newer.")

HERE = Path(__file__).resolve().parent
if (HERE / "app").is_dir() and (HERE / "pyproject.toml").is_file():
    say(PASS, "running from backend/")
else:
    say(FAIL, "wrong folder",
        "Run this from the backend/ folder:\n  cd backend && uv run python check_setup.py")
    raise SystemExit(1)

ENV = HERE / ".env"
if ENV.is_file():
    say(PASS, ".env exists")
else:
    say(FAIL, ".env missing", "cp .env.example .env   then fill it in")
    raise SystemExit(1)


# ══════════════════════════════════════════════════════════════════════
section("2 · EVERY VARIABLE IS SET")
# ══════════════════════════════════════════════════════════════════════

try:
    from dotenv import load_dotenv
    load_dotenv(ENV)
except ImportError:
    say(WARN, "python-dotenv not installed", "Run  uv sync  first.")

REQUIRED = {
    "GOOGLE_CLIENT_ID":     "console.cloud.google.com -> APIs & Services -> Credentials",
    "GOOGLE_CLIENT_SECRET": "same place as the client id",
    "GOOGLE_REDIRECT_URI":  "must EXACTLY match the redirect URI registered in Google Cloud",
    "SUPABASE_URL":         "supabase.com -> your project -> Settings -> API -> Project URL",
    "SUPABASE_SERVICE_KEY": "same page -> service_role key (NOT the anon key)",
    "JWT_SECRET":           'python -c "import secrets; print(secrets.token_urlsafe(32))"',
    "ENCRYPTION_KEY":       'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"',
    "FRONTEND_URL":         "where the Vite dev server runs, e.g. http://localhost:5175",
    "BACKEND_URL":          "where uvicorn runs, e.g. http://localhost:8001",
}

PROVIDER = os.getenv("LLM_PROVIDER", "local").strip().lower()
if PROVIDER == "groq":
    REQUIRED["GROQ_API_KEY"] = "console.groq.com/keys  (LLM_PROVIDER=groq)"
say(PASS if PROVIDER in ("local", "groq") else FAIL, f"LLM_PROVIDER={PROVIDER}",
    "" if PROVIDER in ("local", "groq") else "must be 'local' or 'groq'")

PLACEHOLDERS = ("your_", "_here", "changeme", "xxx")
missing = []
for var, where in REQUIRED.items():
    val = os.getenv(var, "")
    if not val:
        say(FAIL, var, f"not set. {where}")
        missing.append(var)
    elif any(p in val.lower() for p in PLACEHOLDERS):
        say(FAIL, var, f"still the placeholder from .env.example. {where}")
        missing.append(var)
    else:
        say(PASS, var)


# ══════════════════════════════════════════════════════════════════════
section("3 · THE PORTS AGREE  (the #1 cause of 'login loops')")
# ══════════════════════════════════════════════════════════════════════

redirect = os.getenv("GOOGLE_REDIRECT_URI", "")
backend = os.getenv("BACKEND_URL", "")
frontend = os.getenv("FRONTEND_URL", "")

r_port = urlparse(redirect).port
b_port = urlparse(backend).port
f_port = urlparse(frontend).port

if r_port and b_port and r_port == b_port:
    say(PASS, f"redirect URI port matches BACKEND_URL  (:{b_port})")
else:
    say(FAIL, "redirect URI port != BACKEND_URL port",
        f"GOOGLE_REDIRECT_URI = {redirect}  (port {r_port})\n"
        f"BACKEND_URL         = {backend}  (port {b_port})\n"
        "Google redirects to the URI it was registered with. If nothing is\n"
        "listening there, login silently loops. Make these agree, and make\n"
        "them agree with the port you launch uvicorn on.")

if redirect.endswith("/auth/callback"):
    say(PASS, "redirect URI ends with /auth/callback")
else:
    say(FAIL, "redirect URI path is wrong",
        f"Got: {redirect}\nIt must end with /auth/callback")

if f_port and b_port and f_port != b_port:
    say(PASS, f"frontend :{f_port} and backend :{b_port} are different ports")
elif f_port:
    say(FAIL, "frontend and backend are on the SAME port", "They cannot both bind it.")

print(f"\n          Launch the backend on port {b_port or '?'}:")
print(f"            uv run uvicorn app.main:app --reload --port {b_port or 8000}")
print(f"          (or just  uv run python -m app.main  — it now reads BACKEND_URL)")


# ══════════════════════════════════════════════════════════════════════
section("4 · THE LLM ACTUALLY ANSWERS")
# ══════════════════════════════════════════════════════════════════════

CONFIGURED_MODEL = "openai/gpt-oss-120b"   # Groq default; keep in sync with app/agent/config.py

try:
    import httpx
except ImportError:
    say(FAIL, "httpx not installed", "Run  uv sync  first.")
    httpx = None

LOCAL_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
LOCAL_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama3.1:8b")

if PROVIDER == "local" and httpx:
    try:
        r = httpx.get(f"{LOCAL_URL}/models", timeout=10)
        if r.status_code != 200:
            say(FAIL, f"local LLM server returned {r.status_code}", r.text[:200])
        else:
            ids = sorted(m["id"] for m in r.json().get("data", []))
            say(PASS, f"local LLM server reachable at {LOCAL_URL} — {len(ids)} models")
            if LOCAL_MODEL in ids or f"{LOCAL_MODEL}:latest" in ids:
                say(PASS, f"configured local model '{LOCAL_MODEL}' is pulled")
                try:
                    r = httpx.post(f"{LOCAL_URL}/chat/completions", timeout=180, json={
                        "model": LOCAL_MODEL, "max_tokens": 8,
                        "messages": [{"role": "user", "content": "Say OK."}]})
                    r.raise_for_status()
                    txt = r.json()["choices"][0]["message"]["content"].strip()
                    say(PASS, f"local model answered: {txt[:40]!r}")
                except Exception as e:
                    say(FAIL, "local model did not answer", f"{type(e).__name__}: {e}")
            else:
                say(FAIL, f"configured local model '{LOCAL_MODEL}' is NOT pulled",
                    f"Run:  ollama pull {LOCAL_MODEL}\nor set LOCAL_LLM_MODEL to one of:\n  "
                    + "\n  ".join(ids[:12]))
    except Exception as e:
        say(FAIL, f"could not reach local LLM at {LOCAL_URL}",
            f"{type(e).__name__}: {e}\nStart it:  ollama serve   (or open the Ollama app)")

if not os.getenv("GROQ_API_KEY"):
    say(WARN if PROVIDER == "local" else FAIL,
        "Groq check skipped — GROQ_API_KEY not set"
        + ("  (fine in local mode: no cloud fallback)" if PROVIDER == "local" else ""))
elif httpx:
    try:
        r = httpx.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"},
            timeout=20,
        )
        if r.status_code == 200:
            ids = sorted(m["id"] for m in r.json().get("data", []))
            say(PASS, f"Groq key works — {len(ids)} models available"
                + ("  (fallback only in local mode)" if PROVIDER == "local" else ""))
            if CONFIGURED_MODEL in ids:
                say(PASS, f"Groq model '{CONFIGURED_MODEL}' is available")
            else:
                chat = [i for i in ids if not any(
                    w in i.lower() for w in ("whisper", "tts", "guard", "embed"))]
                say(WARN if PROVIDER == "local" else FAIL,
                    f"Groq model '{CONFIGURED_MODEL}' is NOT on your key",
                    "Groq retires models faster than its docs update. Pick one of:\n  "
                    + "\n  ".join(chat[:12])
                    + "\nthen set it in app/agent/config.py AND app/core/llm.py")
        elif r.status_code == 401:
            say(FAIL, "Groq key rejected (401)", "Make a new one at console.groq.com/keys")
        else:
            say(FAIL, f"Groq returned {r.status_code}", r.text[:200])
    except Exception as e:
        say(FAIL, "could not reach Groq", f"{type(e).__name__}: {e}")

if httpx and os.getenv("OPENROUTER_API_KEY"):  # fallback only — a warn, never fatal
    try:
        r = httpx.get(
            "https://openrouter.ai/api/v1/key",
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            timeout=20,
        )
        if r.status_code == 200:
            say(PASS, "OpenRouter key works (the fallback model)")
        elif r.status_code == 401:
            say(FAIL, "OpenRouter key rejected (401)", "New key at openrouter.ai/keys")
        else:
            say(WARN, f"OpenRouter returned {r.status_code}",
                "The fallback may not fire. Not fatal for Day 1 or Day 2.")
    except Exception as e:
        say(WARN, "could not reach OpenRouter", f"{type(e).__name__}: {e}")


# ══════════════════════════════════════════════════════════════════════
section("5 · FERNET AND JWT ARE VALID")
# ══════════════════════════════════════════════════════════════════════

key = os.getenv("ENCRYPTION_KEY", "")
if key:
    try:
        from cryptography.fernet import Fernet
        f = Fernet(key.encode())
        token = f.encrypt(b"hello")
        assert f.decrypt(token) == b"hello"
        say(PASS, "ENCRYPTION_KEY is a valid Fernet key (encrypt/decrypt round-trip)")
    except Exception as e:
        say(FAIL, "ENCRYPTION_KEY is not a valid Fernet key",
            f"{type(e).__name__}. Generate one:\n"
            '  python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"')

secret = os.getenv("JWT_SECRET", "")
if secret and len(secret) >= 32:
    say(PASS, f"JWT_SECRET is {len(secret)} characters")
elif secret:
    say(WARN, f"JWT_SECRET is only {len(secret)} characters", "32+ recommended.")


# ══════════════════════════════════════════════════════════════════════
section("6 · SUPABASE — TABLES, pgvector, AND THE SEARCH FUNCTION")
# ══════════════════════════════════════════════════════════════════════

url, svc = os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SERVICE_KEY", "")
if not httpx:
    say(WARN, "skipped — httpx not installed", "Run  uv sync  and try again.")
elif not (url and svc):
    say(WARN, "skipped — SUPABASE_URL / SUPABASE_SERVICE_KEY not set")
else:
    hdrs = {"apikey": svc, "Authorization": f"Bearer {svc}"}
    try:
        ok_tables, bad_tables = [], []
        for t in ("users", "personas", "rules", "emails", "modifications", "embeddings"):
            r = httpx.get(f"{url}/rest/v1/{t}?select=*&limit=1", headers=hdrs, timeout=20)
            (ok_tables if r.status_code == 200 else bad_tables).append(t)
        if not bad_tables:
            say(PASS, f"all 6 tables exist ({', '.join(ok_tables)})")
        else:
            say(FAIL, f"missing tables: {', '.join(bad_tables)}",
                "Supabase -> SQL Editor -> run both migrations:\n"
                "  supabase/migrations/001_users.sql\n"
                "  supabase/migrations/002_full_schema.sql")

        # match_embeddings: call it with a zero vector. A 404 means it is absent;
        # anything else means the function is there and reachable.
        r = httpx.post(
            f"{url}/rest/v1/rpc/match_embeddings",
            headers={**hdrs, "Content-Type": "application/json"},
            json={"query_embedding": [0.0] * 768,
                  "query_user_id": "00000000-0000-0000-0000-000000000000",
                  "match_threshold": 0.4, "match_count": 1},
            timeout=20,
        )
        if r.status_code == 404:
            say(FAIL, "match_embeddings() function not found",
                "Run 002_full_schema.sql — it creates pgvector, the HNSW index,\n"
                "and this function. Without it, retrieval does nothing.")
        else:
            say(PASS, "match_embeddings() exists and is callable")
    except Exception as e:
        say(FAIL, "could not reach Supabase",
            f"{type(e).__name__}: {e}\n"
            "Free projects PAUSE after inactivity — open the dashboard and resume it.")


# ══════════════════════════════════════════════════════════════════════
section("7 · THE EMBEDDING MODEL  (~420 MB on first run — be patient)")
# ══════════════════════════════════════════════════════════════════════

try:
    from sentence_transformers import SentenceTransformer
    print("          downloading / loading all-mpnet-base-v2 ...")
    m = SentenceTransformer("all-mpnet-base-v2")
    vec = m.encode("hello world", normalize_embeddings=True)
    if len(vec) == 768:
        say(PASS, f"embedding model ready — 768 dimensions, cached on disk")
    else:
        say(FAIL, f"model returned {len(vec)} dims, expected 768",
            "The DB column is vector(768). These must match.")
except ImportError:
    say(FAIL, "sentence-transformers not installed", "Run  uv sync  first.")
except Exception as e:
    say(FAIL, "could not load the embedding model",
        f"{type(e).__name__}: {e}\nUsually a network problem — try again on better wifi.")


# ══════════════════════════════════════════════════════════════════════
# verdict
# ══════════════════════════════════════════════════════════════════════
n_fail = sum(1 for s, _ in _results if s == FAIL)
n_warn = sum(1 for s, _ in _results if s == WARN)
n_pass = sum(1 for s, _ in _results if s == PASS)

print(f"\n{'═' * 68}")
if n_fail == 0:
    print(f"READY.  {n_pass} passed, {n_warn} warnings, 0 failures.")
    print("Nothing to do before class. See you Day 1.")
else:
    print(f"NOT READY.  {n_pass} passed, {n_warn} warnings, {n_fail} FAILURES.")
    print("Fix the FAIL lines above and run this again:")
    for s, label in _results:
        if s == FAIL:
            print(f"    - {label}")
print("═" * 68)

sys.exit(1 if n_fail else 0)
