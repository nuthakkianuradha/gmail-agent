import base64
import re
from email.utils import parseaddr


def decode_base64(data: str) -> str:
    """Decode base64url-encoded string from Gmail API."""
    padded = data + "=" * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def get_header(headers: list[dict], name: str) -> str:
    """Extract a header value from Gmail message headers."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def extract_body(payload: dict) -> tuple[str, str | None]:
    """Extract plain text and HTML body from Gmail message payload.
    Returns (text_body, html_body).
    """
    text_body = ""
    html_body = None

    mime_type = payload.get("mimeType", "")

    # Simple single-part message
    if mime_type == "text/plain" and "body" in payload:
        data = payload["body"].get("data", "")
        if data:
            text_body = decode_base64(data)
        return text_body, html_body

    if mime_type == "text/html" and "body" in payload:
        data = payload["body"].get("data", "")
        if data:
            html_body = decode_base64(data)
        return text_body, html_body

    # Multipart message — recurse through parts
    parts = payload.get("parts", [])
    for part in parts:
        part_mime = part.get("mimeType", "")
        if part_mime == "text/plain" and not text_body:
            data = part.get("body", {}).get("data", "")
            if data:
                text_body = decode_base64(data)
        elif part_mime == "text/html" and not html_body:
            data = part.get("body", {}).get("data", "")
            if data:
                html_body = decode_base64(data)
        elif part_mime.startswith("multipart/"):
            # Nested multipart
            nested_text, nested_html = extract_body(part)
            if nested_text and not text_body:
                text_body = nested_text
            if nested_html and not html_body:
                html_body = nested_html

    # If we only have HTML, strip tags for text version
    if not text_body and html_body:
        text_body = strip_html(html_body)

    return text_body, html_body


def strip_html(html: str) -> str:
    """Basic HTML tag stripping."""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_gmail_message(msg: dict) -> dict:
    """Parse a Gmail API message response into a clean dict."""
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])

    from_raw = get_header(headers, "From")
    to_raw = get_header(headers, "To")
    subject = get_header(headers, "Subject")
    date = get_header(headers, "Date")
    message_id_header = get_header(headers, "Message-ID")

    _, from_address = parseaddr(from_raw)
    _, to_address = parseaddr(to_raw)

    text_body, html_body = extract_body(payload)

    return {
        "gmail_message_id": msg.get("id", ""),
        "gmail_thread_id": msg.get("threadId", ""),
        "from_address": from_address or from_raw,
        "to_address": to_address or to_raw,
        "subject": subject,
        "body_text": text_body,
        "body_html": html_body,
        "snippet": msg.get("snippet", ""),
        "labels": msg.get("labelIds", []),
        "received_at": date,
        "message_id_header": message_id_header,
    }


if __name__ == "__main__":
    # Test with a mock Gmail API response
    mock_msg = {
        "id": "msg-123",
        "threadId": "thread-456",
        "snippet": "Hey this is a test email",
        "labelIds": ["INBOX", "UNREAD", "CATEGORY_PRIMARY"],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "John Doe <john@example.com>"},
                {"name": "To", "value": "me@gmail.com"},
                {"name": "Subject", "value": "Test Subject"},
                {"name": "Date", "value": "Mon, 30 Mar 2026 10:00:00 +0000"},
                {"name": "Message-ID", "value": "<abc123@mail.gmail.com>"},
            ],
            "body": {
                "data": base64.urlsafe_b64encode(
                    b"Hello, this is the email body!"
                ).decode()
            },
        },
    }
    parsed = parse_gmail_message(mock_msg)
    print("Parsed email:")
    for k, v in parsed.items():
        print(f"  {k}: {v}")
    print("Email parser OK")
