import pytest
from pydantic import ValidationError
from app.models.user import UserProfile, UserInDB
from app.models.email import EmailSummary, EmailMessage, InboxResponse
from app.models.draft import DraftGenerateRequest, DraftGenerateResponse, DraftSendRequest
from app.models.persona import PersonaRequest, RuleRequest


def test_user_profile():
    user = UserProfile(id="1", email="a@b.com", name="Test")
    assert user.email == "a@b.com"
    assert user.picture_url is None


def test_user_profile_requires_email():
    with pytest.raises(ValidationError):
        UserProfile(id="1")


def test_email_summary():
    email = EmailSummary(
        gmail_message_id="msg-1",
        gmail_thread_id="thread-1",
        from_address="a@b.com",
        to_address="c@d.com",
        subject="Hi",
        snippet="Hello...",
    )
    assert email.is_unread is False
    assert email.labels == []


def test_inbox_response():
    resp = InboxResponse(emails=[], next_page_token=None)
    assert resp.emails == []


def test_draft_generate_request():
    req = DraftGenerateRequest(gmail_message_id="m1", gmail_thread_id="t1")
    assert req.gmail_message_id == "m1"


def test_draft_send_request_optional_draft_before():
    req = DraftSendRequest(
        gmail_thread_id="t1",
        gmail_message_id="m1",
        to="a@b.com",
        subject="Re: Hi",
        body="Reply body",
    )
    assert req.draft_before is None


def test_draft_send_request_with_draft_before():
    req = DraftSendRequest(
        gmail_thread_id="t1",
        gmail_message_id="m1",
        to="a@b.com",
        subject="Re: Hi",
        body="Edited reply",
        draft_before="Original draft",
    )
    assert req.draft_before == "Original draft"


def test_persona_request_defaults():
    p = PersonaRequest()
    assert p.tone == "professional"
    assert p.language == "en"
    assert p.display_name == ""


def test_rule_request():
    r = RuleRequest(rule_text="Be formal")
    assert r.category == "general"
