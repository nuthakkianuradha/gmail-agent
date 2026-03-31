from app.utils.prompt_templates import DRAFT_SYSTEM_PROMPT, DRAFT_PROMPT, DIFF_SUMMARY_PROMPT


def test_draft_system_prompt_exists():
    assert "email reply assistant" in DRAFT_SYSTEM_PROMPT
    assert "reply body" in DRAFT_SYSTEM_PROMPT


def test_draft_prompt_has_all_placeholders():
    prompt = DRAFT_PROMPT.format(
        display_name="John",
        tone="professional",
        style_notes="Be concise",
        signature="Best, John",
        custom_instructions="No emojis",
        rules_text="- Rule 1\n- Rule 2",
        past_emails_text="Past email content",
        modifications_text="Modification content",
        from_address="sender@example.com",
        subject="Test",
        body_text="Hello there",
    )
    assert "John" in prompt
    assert "professional" in prompt
    assert "Be concise" in prompt
    assert "Best, John" in prompt
    assert "No emojis" in prompt
    assert "Rule 1" in prompt
    assert "sender@example.com" in prompt
    assert "Hello there" in prompt


def test_diff_summary_prompt_has_placeholders():
    prompt = DIFF_SUMMARY_PROMPT.format(
        draft_before="Original draft",
        draft_after="Edited draft",
    )
    assert "Original draft" in prompt
    assert "Edited draft" in prompt


def test_draft_prompt_missing_placeholder_raises():
    """Ensure all placeholders are required."""
    try:
        DRAFT_PROMPT.format(display_name="John")
        assert False, "Should have raised KeyError"
    except KeyError:
        pass
