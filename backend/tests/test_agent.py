"""Tests for the agent blocks (config, input, output, tools).

The pure blocks need no DB, network, or LLM. The ``tools`` block is tested
with its MCP and RAG backends faked, which proves the wiring without Gmail or
Supabase. ``state`` and the orchestrator need live Supabase/LLM and are
exercised end to end instead.
"""

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from app.agent import tools as tools_mod
from app.agent.config import AgentConfig
from app.agent.input import build_input
from app.agent.output import parse_output
from app.agent.tools import TOOLS, AgentTools


def test_config_defaults():
    c = AgentConfig.default()
    assert c.primary_model
    assert c.fallback_model
    assert c.match_count == 8
    assert c.memory_source_types == ("email", "modification")


def test_output_strips_whitespace_and_tracks_context():
    out = parse_output("  Hi Jane,\n\nThanks!  ", context_used=4)
    assert out.draft == "Hi Jane,\n\nThanks!"
    assert out.context_used == 4


def test_output_unwraps_code_fence_and_quotes():
    assert parse_output("```\nHello there\n```", 0).draft == "Hello there"
    assert parse_output('"Just a note."', 0).draft == "Just a note."


def test_build_input_includes_email_persona_and_rules():
    state = SimpleNamespace(
        persona={"display_name": "Jane", "tone": "warm", "signature": "Best, Jane"},
        rules=[{"rule_text": "Be brief"}],
        past_emails=[],
        modifications=[],
    )
    email = {"from_address": "a@b.com", "subject": "Sub", "body_text": "Hi there"}
    prompt = build_input(email, state)

    assert "Jane" in prompt
    assert "warm" in prompt
    assert "Be brief" in prompt
    assert "a@b.com" in prompt
    assert "Hi there" in prompt
    assert "(no similar past emails found)" in prompt
    assert "(no past modifications)" in prompt


def test_build_input_formats_retrieved_context():
    state = SimpleNamespace(
        persona={},
        rules=[],
        past_emails=[{"content_text": "Subject: Prior\nBody", "similarity": 0.87}],
        modifications=[{"content_text": "User made it shorter"}],
    )
    email = {"from_address": "x@y.com", "subject": "S", "body_text": "B"}
    prompt = build_input(email, state)

    assert "similarity: 0.87" in prompt
    assert "Subject: Prior" in prompt
    assert "User made it shorter" in prompt
    assert "(no rules set)" in prompt


def test_tools_registry_names_match_methods():
    for spec in TOOLS:
        assert callable(getattr(AgentTools, spec.name)), spec.name


@pytest.mark.asyncio
async def test_tools_route_gmail_calls_through_mcp_client(monkeypatch):
    calls = []

    class FakeGmail:
        def __init__(self, token):
            calls.append(("token", token))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def get_message(self, mid):
            calls.append(("get_message", mid))
            return {"id": mid, "snippet": "hi"}

        async def send_reply(self, **kw):
            calls.append(("send_reply", kw["thread_id"]))
            return {"id": "sent-1"}

    monkeypatch.setattr(tools_mod, "GmailMCPClient", FakeGmail)
    t = AgentTools(user_id="u1", user_email="me@x.com", access_token="tok")

    assert (await t.get_email("m1"))["id"] == "m1"
    sent = await t.send_reply(to="a@b.com", subject="S", body="B", thread_id="t1", message_id_header="<x>")
    assert sent["id"] == "sent-1"
    assert calls == [("token", "tok"), ("get_message", "m1"), ("token", "tok"), ("send_reply", "t1")]


@pytest.mark.asyncio
async def test_tools_route_memory_writes_through_rag_learning(monkeypatch):
    seen = {}
    monkeypatch.setattr(tools_mod, "archive_sent_email", lambda **kw: seen.setdefault("archive", kw))

    async def fake_store(**kw):
        seen["edit"] = kw
        return {"id": "mod-1"}

    monkeypatch.setattr(tools_mod, "store_modification", fake_store)
    t = AgentTools(user_id="u1", user_email="me@x.com", access_token="tok")

    t.remember_sent_email(gmail_message_id="g1", gmail_thread_id="t1", to="a@b.com", subject="S", body="B")
    assert seen["archive"]["user_id"] == "u1"
    assert seen["archive"]["from_address"] == "me@x.com"

    out = await t.remember_edit(subject="S", snippet="sn", draft_before="a", draft_after="b")
    assert out["id"] == "mod-1"
    assert seen["edit"]["draft_before"] == "a" and seen["edit"]["user_id"] == "u1"


if __name__ == "__main__":
    test_config_defaults()
    test_output_strips_whitespace_and_tracks_context()
    test_output_unwraps_code_fence_and_quotes()
    test_build_input_includes_email_persona_and_rules()
    test_build_input_formats_retrieved_context()
    print("Agent block tests OK")
