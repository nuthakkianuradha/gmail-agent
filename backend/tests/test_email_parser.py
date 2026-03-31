import base64
from app.utils.email_parser import (
    decode_base64,
    get_header,
    extract_body,
    strip_html,
    parse_gmail_message,
)


def test_decode_base64():
    encoded = base64.urlsafe_b64encode(b"Hello World").decode()
    assert decode_base64(encoded) == "Hello World"


def test_decode_base64_with_padding():
    encoded = base64.urlsafe_b64encode(b"Test").decode().rstrip("=")
    assert decode_base64(encoded) == "Test"


def test_get_header():
    headers = [
        {"name": "From", "value": "alice@example.com"},
        {"name": "Subject", "value": "Hello"},
    ]
    assert get_header(headers, "From") == "alice@example.com"
    assert get_header(headers, "subject") == "Hello"  # case-insensitive
    assert get_header(headers, "Missing") == ""


def test_extract_body_plain_text():
    payload = {
        "mimeType": "text/plain",
        "body": {"data": base64.urlsafe_b64encode(b"Plain body").decode()},
    }
    text, html = extract_body(payload)
    assert text == "Plain body"
    assert html is None


def test_extract_body_html():
    payload = {
        "mimeType": "text/html",
        "body": {"data": base64.urlsafe_b64encode(b"<p>HTML body</p>").decode()},
    }
    text, html = extract_body(payload)
    assert html == "<p>HTML body</p>"


def test_extract_body_multipart():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": base64.urlsafe_b64encode(b"Plain part").decode()},
            },
            {
                "mimeType": "text/html",
                "body": {"data": base64.urlsafe_b64encode(b"<b>HTML part</b>").decode()},
            },
        ],
    }
    text, html = extract_body(payload)
    assert text == "Plain part"
    assert html == "<b>HTML part</b>"


def test_strip_html():
    html = "<p>Hello</p><br/><b>World</b>&amp;More"
    result = strip_html(html)
    assert "Hello" in result
    assert "World" in result
    assert "&More" in result
    assert "<p>" not in result


def test_parse_gmail_message():
    msg = {
        "id": "msg-abc",
        "threadId": "thread-xyz",
        "snippet": "Test snippet",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "Bob <bob@example.com>"},
                {"name": "To", "value": "alice@example.com"},
                {"name": "Subject", "value": "Test Subject"},
                {"name": "Date", "value": "Mon, 31 Mar 2026 10:00:00 +0000"},
                {"name": "Message-ID", "value": "<msg123@mail.gmail.com>"},
            ],
            "body": {"data": base64.urlsafe_b64encode(b"Email body here").decode()},
        },
    }
    parsed = parse_gmail_message(msg)
    assert parsed["gmail_message_id"] == "msg-abc"
    assert parsed["gmail_thread_id"] == "thread-xyz"
    assert parsed["from_address"] == "bob@example.com"
    assert parsed["to_address"] == "alice@example.com"
    assert parsed["subject"] == "Test Subject"
    assert parsed["body_text"] == "Email body here"
    assert parsed["snippet"] == "Test snippet"
    assert parsed["message_id_header"] == "<msg123@mail.gmail.com>"


def test_parse_gmail_message_no_body():
    msg = {
        "id": "msg-empty",
        "threadId": "thread-1",
        "snippet": "",
        "labelIds": [],
        "payload": {
            "mimeType": "text/plain",
            "headers": [],
            "body": {"data": ""},
        },
    }
    parsed = parse_gmail_message(msg)
    assert parsed["body_text"] == ""
    assert parsed["from_address"] == ""
