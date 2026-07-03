"""Tests for the agent blocks (config, input, output).

These cover the pure blocks that need no DB, network, or LLM. The ``state`` and
``agent`` orchestration blocks are covered indirectly via the MCP roundtrip
tests and require live Supabase/LLM, so they are not unit-tested here.
"""

from types import SimpleNamespace

from app.agent.config import AgentConfig
from app.agent.input import build_input
from app.agent.output import parse_output


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


if __name__ == "__main__":
    test_config_defaults()
    test_output_strips_whitespace_and_tracks_context()
    test_output_unwraps_code_fence_and_quotes()
    test_build_input_includes_email_persona_and_rules()
    test_build_input_formats_retrieved_context()
    print("Agent block tests OK")
