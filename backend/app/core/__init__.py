"""Shared platform plumbing used by every subsystem — and by nothing in particular.

- ``db``     — the Supabase client (Postgres + pgvector).
- ``crypto`` — Fernet encrypt/decrypt for OAuth tokens at rest.
- ``auth``   — Google OAuth (PKCE), JWT sessions, token refresh.
- ``llm``    — chat completions through a provider chain (local → Groq → OpenRouter).

Rule: ``core`` knows nothing about the agent, RAG, or MCP. Those three import
from ``core``; ``core`` never imports from them.
"""
