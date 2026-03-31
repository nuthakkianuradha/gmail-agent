import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.utils.email_parser import parse_gmail_message, get_header


def _get_gmail_client(access_token: str):
    creds = Credentials(token=access_token)
    return build("gmail", "v1", credentials=creds)


def list_inbox(
    access_token: str,
    page_token: str | None = None,
    max_results: int = 20,
) -> dict:
    """List Primary inbox messages."""
    service = _get_gmail_client(access_token)
    params = {
        "userId": "me",
        "labelIds": ["INBOX"],
        "maxResults": max_results,
    }
    if page_token:
        params["pageToken"] = page_token

    result = service.users().messages().list(**params).execute()
    messages = result.get("messages", [])

    emails = []
    for msg_ref in messages:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=msg_ref["id"], format="metadata",
                 metadataHeaders=["From", "To", "Subject", "Date"])
            .execute()
        )
        headers = msg.get("payload", {}).get("headers", [])
        from email.utils import parseaddr
        from_raw = ""
        to_raw = ""
        subject = ""
        date = ""
        for h in headers:
            name = h.get("name", "").lower()
            if name == "from":
                from_raw = h.get("value", "")
            elif name == "to":
                to_raw = h.get("value", "")
            elif name == "subject":
                subject = h.get("value", "")
            elif name == "date":
                date = h.get("value", "")

        _, from_addr = parseaddr(from_raw)
        _, to_addr = parseaddr(to_raw)

        emails.append({
            "gmail_message_id": msg["id"],
            "gmail_thread_id": msg["threadId"],
            "from_address": from_addr or from_raw,
            "to_address": to_addr or to_raw,
            "subject": subject,
            "snippet": msg.get("snippet", ""),
            "labels": msg.get("labelIds", []),
            "received_at": date,
            "is_unread": "UNREAD" in msg.get("labelIds", []),
        })

    return {
        "emails": emails,
        "next_page_token": result.get("nextPageToken"),
    }


def get_message(access_token: str, message_id: str) -> dict:
    """Get full email message."""
    service = _get_gmail_client(access_token)
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    return parse_gmail_message(msg)


def get_thread(access_token: str, thread_id: str) -> dict:
    """Get all messages in a thread."""
    service = _get_gmail_client(access_token)
    thread = (
        service.users()
        .threads()
        .get(userId="me", id=thread_id, format="full")
        .execute()
    )
    messages = [parse_gmail_message(msg) for msg in thread.get("messages", [])]
    return {
        "thread_id": thread_id,
        "messages": messages,
    }


def send_reply(
    access_token: str,
    to: str,
    subject: str,
    body: str,
    thread_id: str,
    message_id_header: str,
) -> dict:
    """Send a reply email in the correct thread."""
    service = _get_gmail_client(access_token)

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject if subject.startswith("Re:") else f"Re: {subject}"
    message["In-Reply-To"] = message_id_header
    message["References"] = message_id_header

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = (
        service.users()
        .messages()
        .send(userId="me", body={"raw": raw, "threadId": thread_id})
        .execute()
    )
    return sent


if __name__ == "__main__":
    print("Gmail service functions:")
    print("  list_inbox(access_token, page_token?, max_results?)")
    print("  get_message(access_token, message_id)")
    print("  get_thread(access_token, thread_id)")
    print("  send_reply(access_token, to, subject, body, thread_id, message_id_header)")
    print("Gmail service module OK")
