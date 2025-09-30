"""
Gmail tools for LangChain agents - FIXED VERSION

- Prefer official LangChain Gmail tools (langchain_google_community) when available.
- Gracefully degrade to direct REST calls if discovery/build fails.
- Clear separation between read/search/send operations.
"""

from __future__ import annotations

import json
import os
from typing import Optional, Literal, Any, Dict, List, Tuple
from urllib.parse import urlencode

from utils.google_oauth import ensure_agent_token_file

# Import LangChain tool types
try:
    from langchain_core.tools import Tool as CoreTool, StructuredTool
except Exception:
    from langchain.agents import Tool as CoreTool
    StructuredTool = None

# Pydantic imports
try:
    from pydantic import BaseModel, Field
except Exception:
    from pydantic.v1 import BaseModel, Field


# -----------------------------
# Configuration
# -----------------------------
def _default_gmail_dir() -> str:
    """Get default directory for Gmail credentials."""
    base_dir = os.getenv("GMAIL_CREDENTIALS_DIR") or os.getenv("CREDENTIALS_DIR")
    if base_dir:
        if base_dir == os.getenv("CREDENTIALS_DIR"):
            return os.path.join(base_dir, "gmail")
        return base_dir
    return os.path.join(os.getcwd(), ".credentials", "gmail")


CREDS_DIR = _default_gmail_dir()

# Token path resolution
# Tokens are sourced from the database (list_account) via ensure_agent_token_file.
# Retain the variables for backward compatibility but do not resolve local paths.
TOKEN_PATH = None
DEFAULT_TOKEN_PATH = None

# Client secrets path resolution
_candidate_secrets = [
    os.getenv("GMAIL_CLIENT_SECRETS_PATH"),
    os.path.join(CREDS_DIR, "credentials.json"),
    os.path.join(os.getcwd(), "credentials.json"),
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
]
CLIENT_SECRETS_PATH = next(
    (p for p in _candidate_secrets if p and os.path.exists(p)),
    _candidate_secrets[1],
)

# Gmail API scopes
SCOPES = [
    s.strip()
    for s in os.getenv(
        "GMAIL_SCOPES",
        "https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/gmail.send",
    ).split(",")
    if s.strip()
]


def _resolve_token_for_agent(agent_id: Optional[str]) -> Tuple[Optional[str], bool]:
    """Return the hydrated token path for an agent (never falls back to project files)."""

    return ensure_agent_token_file(agent_id, None)


# -----------------------------
# -----------------------------
# Pydantic Models for Tool Arguments
# -----------------------------
class GmailSearchArgs(BaseModel):
    """Arguments for Gmail search."""
    query: str = Field(
        ..., 
        description="Gmail search query (e.g., 'from:sender@email.com', 'subject:Invoice', 'is:unread')"
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of emails to return (1-50)"
    )


class GmailReadArgs(BaseModel):
    """Arguments for reading Gmail messages."""
    query: Optional[str] = Field(
        default="is:unread",
        description="Gmail search query. Default: 'is:unread'. Examples: 'from:john@example.com', 'subject:Report'"
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of messages to read (1-50)"
    )
    mark_as_read: bool = Field(
        default=False,
        description="If True, mark messages as read after retrieving them"
    )


class GmailSendArgs(BaseModel):
    """Arguments for sending Gmail messages."""
    to: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject line")
    message: str = Field(..., description="Email body content (plain text or HTML)")
    is_html: bool = Field(default=False, description="If True, send as HTML email")


class GmailGetMessageArgs(BaseModel):
    """Arguments for getting a specific Gmail message."""
    message_id: str = Field(..., description="Gmail message ID")
    format: str = Field(
        default="full",
        description="Format: 'minimal', 'full', 'raw', or 'metadata'"
    )


class GmailUnifiedArgs(BaseModel):
    """Unified Gmail tool arguments with action dispatcher."""
    action: Literal["read", "search", "send", "get", "get_message", "message"] = Field(
        ..., description="Gmail action to perform"
    )
    # read/search
    query: Optional[str] = Field(
        default=None,
        description="Gmail query for read/search; defaults to 'is:unread' for read",
    )
    max_results: int = Field(5, ge=1, le=50, description="Max results for read/search")
    mark_as_read: bool = Field(False, description="Mark messages as read when action=read")
    # send
    to: Optional[str] = Field(default=None, description="Recipient email (action=send)")
    subject: Optional[str] = Field(default=None, description="Subject (action=send)")
    message: Optional[str] = Field(default=None, description="Body (action=send)")
    is_html: bool = Field(False, description="Send as HTML (action=send)")
    # get
    message_id: Optional[str] = Field(
        default=None,
        description="Gmail message ID to fetch (action=get)",
    )
    format: Optional[str] = Field(
        default="full",
        description="Gmail format for get: minimal|full|raw|metadata",
    )


# -----------------------------
# Initialize Gmail Service
# -----------------------------
def initialize_gmail_service(agent_id: Optional[str] = None):
    """Initialize Gmail service with proper error handling."""
    service = None
    error_messages = []

    token_path, _ = _resolve_token_for_agent(agent_id)
    if not token_path:
        who = f" for agent {agent_id}" if agent_id else ""
        error_messages.append(
            "Gmail OAuth token not found"
            + who
            + ". Please authorize via the Gmail OAuth flow first."
        )
        return None, error_messages

    try:
        # Try new package first
        try:
            from langchain_google_community.gmail.utils import (  # type: ignore[reportMissingImports]
                get_gmail_credentials,
                build_resource_service,
            )
        except ImportError:
            # Fallback to older package
            from langchain_community.tools.gmail.utils import (  # type: ignore[reportMissingImports]
                get_gmail_credentials,
                build_resource_service,
            )
        
        # Check for required files
        missing_files = []
        if not os.path.exists(CLIENT_SECRETS_PATH):
            missing_files.append(f"Client secrets at {CLIENT_SECRETS_PATH}")
        if not os.path.exists(token_path):
            missing_files.append(f"Token at {token_path}")

        if missing_files:
            raise FileNotFoundError(
                "Missing Gmail OAuth assets: "
                + ", ".join(missing_files)
                + ". Complete the Google OAuth flow so the token is stored in the database and regenerated for the agent."
            )

        # Get credentials
        creds = get_gmail_credentials(
            token_file=token_path,
            client_secrets_file=CLIENT_SECRETS_PATH,
            scopes=SCOPES,
        )
        
        # Build service
        try:
            service = build_resource_service(credentials=creds)
        except Exception as e:
            error_messages.append(f"build_resource_service failed: {e}")
            # Try discovery API fallback
            try:
                from googleapiclient.discovery import build as gbuild
                service = gbuild("gmail", "v1", credentials=creds, cache_discovery=False)
            except Exception as e2:
                error_messages.append(f"Discovery build failed: {e2}")
                
    except Exception as e:
        error_messages.append(f"Service initialization failed: {e}")
    
    return service, error_messages


# -----------------------------
# Helper Functions
# -----------------------------
def decode_base64(data: str) -> str:
    """Decode base64 encoded string."""
    import base64
    try:
        # Add padding if needed
        data = data + "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def extract_message_body(payload: dict) -> tuple[Optional[str], Optional[str]]:
    """Extract plain text and HTML body from message payload."""
    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})
    data = body.get("data")
    
    text_plain = None
    text_html = None
    
    if mime_type == "text/plain" and data:
        text_plain = decode_base64(data)
    elif mime_type == "text/html" and data:
        text_html = decode_base64(data)
    
    # Check parts for multipart messages
    parts = payload.get("parts", [])
    for part in parts:
        tp, th = extract_message_body(part)
        text_plain = text_plain or tp
        text_html = text_html or th
        if text_plain and text_html:
            break
    
    return text_plain, text_html


def format_message_data(message_data: dict) -> dict:
    """Format Gmail message data for output."""
    headers = {
        h.get("name", "").lower(): h.get("value", "")
        for h in message_data.get("payload", {}).get("headers", [])
    }
    
    text_plain, text_html = extract_message_body(message_data.get("payload", {}))
    
    # Truncate body if too long
    max_chars = int(os.getenv("GMAIL_MAX_BODY_CHARS", "5000"))
    if text_plain and len(text_plain) > max_chars:
        text_plain = text_plain[:max_chars] + "... [truncated]"
    if text_html and len(text_html) > max_chars:
        text_html = text_html[:max_chars] + "... [truncated]"
    
    return {
        "id": message_data.get("id"),
        "threadId": message_data.get("threadId"),
        "labelIds": message_data.get("labelIds", []),
        "subject": headers.get("subject", ""),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "date": headers.get("date", ""),
        "snippet": message_data.get("snippet", ""),
        "body_text": text_plain,
        "body_html": text_html,
    }


# -----------------------------
# Tool Implementation Functions
# -----------------------------
def gmail_search_messages(
    query: str,
    max_results: int = 10,
    *,
    agent_id: Optional[str] = None,
) -> str:
    """
    Search Gmail messages.
    This function ONLY searches and returns message metadata.
    """
    service, errors = initialize_gmail_service(agent_id=agent_id)
    if not service:
        # Try REST fallback
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import AuthorizedSession, Request as GARequest
        except Exception:
            return f"Gmail tool unavailable: {'; '.join(errors)}"
        try:
            token_path, _ = _resolve_token_for_agent(agent_id)
            if not token_path:
                return (
                    "Gmail tool unavailable: missing OAuth token. "
                    "Please authorize this agent via the Gmail OAuth flow."
                )
            creds = Credentials.from_authorized_user_file(token_path, scopes=SCOPES)
            if not creds.valid and getattr(creds, 'refresh_token', None):
                creds.refresh(GARequest())
            authed = AuthorizedSession(creds)
            timeout = float(os.getenv("GMAIL_HTTP_TIMEOUT", "20"))
            params = {"q": query, "maxResults": max_results}
            resp = authed.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                params=params,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            messages = data.get("messages", []) or []
            output = []
            for m in messages:
                mid = m.get("id")
                if not mid:
                    continue
                det = authed.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}",
                    params={
                        "format": "metadata",
                        "metadataHeaders": ["Subject", "From", "Date", "To"],
                    },
                    timeout=timeout,
                )
                det.raise_for_status()
                md = det.json()
                headers = {
                    h.get("name", "").lower(): h.get("value", "")
                    for h in (md.get("payload", {}) or {}).get("headers", []) or []
                }
                output.append(
                    {
                        "id": mid,
                        "subject": headers.get("subject", ""),
                        "from": headers.get("from", ""),
                        "to": headers.get("to", ""),
                        "date": headers.get("date", ""),
                        "snippet": md.get("snippet", ""),
                    }
                )
            return json.dumps(
                {"status": "success", "query": query, "count": len(output), "messages": output},
                ensure_ascii=False,
                indent=2,
            )
        except Exception as e:
            return f"Gmail tool unavailable: {'; '.join(errors)}"
    
    try:
        # Search messages
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get("messages", [])
        if not messages:
            return f"No messages found for query: {query}"
        
        output = []
        for msg in messages:
            # Get message details
            message_data = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["Subject", "From", "Date", "To"]
            ).execute()
            
            headers = {
                h.get("name", "").lower(): h.get("value", "")
                for h in message_data.get("payload", {}).get("headers", [])
            }
            
            output.append({
                "id": msg["id"],
                "subject": headers.get("subject", ""),
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "date": headers.get("date", ""),
                "snippet": message_data.get("snippet", "")
            })
        
        return json.dumps({
            "status": "success",
            "query": query,
            "count": len(output),
            "messages": output
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"Gmail search failed: {str(e)}"


def gmail_read_messages(
    query: Optional[str] = "is:unread",
    max_results: int = 5,
    mark_as_read: bool = False,
    *,
    agent_id: Optional[str] = None,
) -> str:
    """
    Read Gmail messages with full content.
    This function retrieves full message bodies.
    """
    service, errors = initialize_gmail_service(agent_id=agent_id)
    if not service:
        # REST fallback
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import AuthorizedSession, Request as GARequest
        except Exception:
            return f"Gmail tool unavailable: {'; '.join(errors)}"
        try:
            search_query = query or "is:unread"
            token_path, _ = _resolve_token_for_agent(agent_id)
            if not token_path:
                return (
                    "Gmail tool unavailable: missing OAuth token. "
                    "Please authorize this agent via the Gmail OAuth flow."
                )
            creds = Credentials.from_authorized_user_file(token_path, scopes=SCOPES)
            if not creds.valid and getattr(creds, 'refresh_token', None):
                creds.refresh(GARequest())
            authed = AuthorizedSession(creds)
            timeout = float(os.getenv("GMAIL_HTTP_TIMEOUT", "20"))
            resp = authed.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                params={"q": search_query, "maxResults": max_results},
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            messages = data.get("messages", []) or []
            output = []
            for m in messages:
                mid = m.get("id")
                if not mid:
                    continue
                det = authed.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}",
                    params={"format": "full"},
                    timeout=timeout,
                )
                det.raise_for_status()
                md = det.json()
                formatted = format_message_data(md)
                output.append(formatted)
                if mark_as_read and "UNREAD" in (md.get("labelIds") or []):
                    try:
                        authed.post(
                            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}/modify",
                            json={"removeLabelIds": ["UNREAD"]},
                            timeout=timeout,
                        )
                    except Exception:
                        pass
            return json.dumps(
                {"status": "success", "query": search_query, "count": len(output), "messages": output},
                ensure_ascii=False,
                indent=2,
            )
        except Exception as e:
            return f"Gmail tool unavailable: {'; '.join(errors)}"
    
    try:
        # Use default query if none provided
        search_query = query or "is:unread"
        
        # Search messages
        results = service.users().messages().list(
            userId="me",
            q=search_query,
            maxResults=max_results
        ).execute()
        
        messages = results.get("messages", [])
        if not messages:
            return f"No messages found for query: {search_query}"
        
        output = []
        for msg in messages:
            # Get full message
            message_data = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="full"
            ).execute()
            
            # Format message data
            formatted_msg = format_message_data(message_data)
            output.append(formatted_msg)
            
            # Mark as read if requested
            if mark_as_read and "UNREAD" in message_data.get("labelIds", []):
                try:
                    service.users().messages().modify(
                        userId="me",
                        id=msg["id"],
                        body={"removeLabelIds": ["UNREAD"]}
                    ).execute()
                except Exception:
                    pass  # Don't fail if marking as read fails
        
        return json.dumps({
            "status": "success",
            "query": search_query,
            "count": len(output),
            "messages": output
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"Gmail read failed: {str(e)}"


def gmail_send_message(
    to: str,
    subject: str,
    message: str,
    is_html: bool = False,
    *,
    agent_id: Optional[str] = None,
) -> str:
    """
    Send an email via Gmail.
    This function ONLY sends emails and should not be used for reading.
    """
    # Check if sending is disabled
    if os.getenv("GMAIL_DISABLE_SEND", "false").lower() == "true":
        return "Gmail send is disabled by server policy (GMAIL_DISABLE_SEND=true)"
    
    service, errors = initialize_gmail_service(agent_id=agent_id)
    if not service:
        # REST fallback: construct MIME and POST to Gmail send endpoint
        try:
            import base64
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import AuthorizedSession, Request as GARequest
        except Exception:
            return f"Gmail tool unavailable: {'; '.join(errors)}"
        try:
            # Create message
            if is_html:
                msg = MIMEMultipart("alternative")
                msg["to"] = to
                msg["subject"] = subject
                text_part = MIMEText(message, "plain", "utf-8")
                html_part = MIMEText(message, "html", "utf-8")
                msg.attach(text_part)
                msg.attach(html_part)
            else:
                msg = MIMEText(message, "plain", "utf-8")
                msg["to"] = to
                msg["subject"] = subject

            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

            token_path, _ = _resolve_token_for_agent(agent_id)
            if not token_path:
                return (
                    "Gmail tool unavailable: missing OAuth token. "
                    "Please authorize this agent via the Gmail OAuth flow."
                )
            creds = Credentials.from_authorized_user_file(token_path, scopes=SCOPES)
            if not creds.valid and getattr(creds, 'refresh_token', None):
                creds.refresh(GARequest())
            authed = AuthorizedSession(creds)
            timeout = float(os.getenv("GMAIL_HTTP_TIMEOUT", "20"))
            resp = authed.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                json={"raw": raw_message},
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return json.dumps({
                "status": "success",
                "message": f"Email sent successfully to {to}",
                "id": data.get("id")
            }, ensure_ascii=False, indent=2)
        except Exception:
            return f"Gmail tool unavailable: {'; '.join(errors)}"
    
    try:
        import base64
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Create message
        if is_html:
            msg = MIMEMultipart("alternative")
            msg["to"] = to
            msg["subject"] = subject
            
            # Add plain text version
            text_part = MIMEText(message, "plain", "utf-8")
            html_part = MIMEText(message, "html", "utf-8")
            
            msg.attach(text_part)
            msg.attach(html_part)
        else:
            msg = MIMEText(message, "plain", "utf-8")
            msg["to"] = to
            msg["subject"] = subject
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        
        # Send message
        result = service.users().messages().send(
            userId="me",
            body={"raw": raw_message}
        ).execute()
        
        return json.dumps({
            "status": "success",
            "message": f"Email sent successfully to {to}",
            "message_id": result.get("id", ""),
            "details": {
                "to": to,
                "subject": subject,
                "is_html": is_html
            }
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"Gmail send failed: {str(e)}"


def gmail_get_message(
    message_id: str,
    format: str = "full",
    *,
    agent_id: Optional[str] = None,
) -> str:
    """
    Get a specific Gmail message by ID.
    """
    service, errors = initialize_gmail_service(agent_id=agent_id)
    if not service:
        return f"Gmail tool unavailable: {'; '.join(errors)}"
    
    try:
        # Get message
        message_data = service.users().messages().get(
            userId="me",
            id=message_id,
            format=format
        ).execute()
        
        if format == "full":
            # Format full message
            formatted_msg = format_message_data(message_data)
            return json.dumps({
                "status": "success",
                "message": formatted_msg
            }, ensure_ascii=False, indent=2)
        else:
            # Return raw format
            return json.dumps({
                "status": "success",
                "message": message_data
            }, ensure_ascii=False, indent=2)
            
    except Exception as e:
        return f"Gmail get message failed: {str(e)}"


# -----------------------------
# Create LangChain Tools
# -----------------------------
def gmail_unified(
    action: str,
    query: Optional[str] = None,
    max_results: int = 5,
    mark_as_read: bool = False,
    to: Optional[str] = None,
    subject: Optional[str] = None,
    message: Optional[str] = None,
    is_html: bool = False,
    message_id: Optional[str] = None,
    format: Optional[str] = "full",
    *,
    agent_id: Optional[str] = None,
) -> str:
    """Unified dispatcher that routes to read/search/send/get."""
    a = (action or "").strip().lower()
    if a == "read":
        return gmail_read_messages(
            query=(query or "is:unread"),
            max_results=max_results,
            mark_as_read=mark_as_read,
            agent_id=agent_id,
        )
    if a == "search":
        return gmail_search_messages(query=(query or ""), max_results=max_results, agent_id=agent_id)
    if a == "send":
        if not (to and subject and message):
            return "Gmail send failed: missing 'to', 'subject', or 'message'"
        return gmail_send_message(
            to=to,
            subject=subject,
            message=message,
            is_html=is_html,
            agent_id=agent_id,
        )
    if a in ("get", "get_message", "message"):
        mid = message_id or (query or "").strip()
        if not mid:
            return "Gmail get_message failed: missing message_id"
        return gmail_get_message(message_id=mid, format=(format or "full"), agent_id=agent_id)
    return "Gmail tool failed: unknown action (use read|search|send|get)"


def create_gmail_tools(agent_id: Optional[str] = None):
    """Create and return Gmail tools for LangChain."""
    tools = []

    def _search_impl(query: str, max_results: int = 10, **kwargs) -> str:
        return gmail_search_messages(query=query, max_results=max_results, agent_id=agent_id)

    def _read_impl(
        query: str = "is:unread",
        max_results: int = 5,
        mark_as_read: bool = False,
        **kwargs,
    ) -> str:
        return gmail_read_messages(
            query=query,
            max_results=max_results,
            mark_as_read=mark_as_read,
            agent_id=agent_id,
        )

    def _send_impl(to: str, subject: str, message: str, is_html: bool = False, **kwargs) -> str:
        return gmail_send_message(
            to=to,
            subject=subject,
            message=message,
            is_html=is_html,
            agent_id=agent_id,
        )

    def _get_impl(message_id: str, format: str = "full", **kwargs) -> str:
        return gmail_get_message(message_id=message_id, format=format, agent_id=agent_id)

    def _unified_impl(
        action: str,
        query: Optional[str] = None,
        max_results: int = 5,
        mark_as_read: bool = False,
        to: Optional[str] = None,
        subject: Optional[str] = None,
        message: Optional[str] = None,
        is_html: bool = False,
        message_id: Optional[str] = None,
        format: Optional[str] = "full",
    ) -> str:
        return gmail_unified(
            action=action,
            query=query,
            max_results=max_results,
            mark_as_read=mark_as_read,
            to=to,
            subject=subject,
            message=message,
            is_html=is_html,
            message_id=message_id,
            format=format,
            agent_id=agent_id,
        )

    # Search tool - ONLY for searching emails
    if StructuredTool:
        gmail_search_tool = StructuredTool.from_function(
            name="gmail_search",
            description=(
                "Search for emails in Gmail inbox. "
                "Use this to find specific emails by sender, subject, date, etc. "
                "This tool returns email metadata (subject, from, date, snippet) but NOT full content. "
                "DO NOT use this tool to read email bodies."
            ),
            func=_search_impl,
            args_schema=GmailSearchArgs,
        )
    else:
        gmail_search_tool = CoreTool(
            name="gmail_search",
            description="Search for emails in Gmail. Returns metadata only.",
            func=lambda input_str: gmail_search_messages(query=input_str, agent_id=agent_id),
        )
    tools.append(gmail_search_tool)

    # Read tool - for reading email content
    if StructuredTool:
        gmail_read_tool = StructuredTool.from_function(
            name="gmail_read_messages",
            description=(
                "Read email messages from Gmail with full content. "
                "Use this to read email bodies and get complete email information. "
                "Can filter by query (e.g., 'is:unread', 'from:sender@email.com'). "
                "This is the tool to use when you need to READ or VIEW email content."
            ),
            func=_read_impl,
            args_schema=GmailReadArgs,
        )
    else:
        gmail_read_tool = CoreTool(
            name="gmail_read_messages",
            description="Read email messages with full content from Gmail.",
            func=lambda input_str: gmail_read_messages(agent_id=agent_id),
        )
    tools.append(gmail_read_tool)

    # Send tool - ONLY for sending emails
    if StructuredTool and agent_id is not None:
        gmail_send_tool = StructuredTool.from_function(
            name="gmail_send_message",
            description=(
                "Send an email via Gmail. "
                "ONLY use this tool when explicitly asked to SEND an email. "
                "DO NOT use this for reading, searching, or any other email operations. "
                "This tool is EXCLUSIVELY for sending new emails."
            ),
            func=_send_impl,
            args_schema=GmailSendArgs,
            return_direct=True,  # Return immediately after sending
        )
    else:
        gmail_send_tool = CoreTool(
            name="gmail_send_message",
            description="Send an email via Gmail. ONLY for sending, not reading.",
            return_direct=True,
            func=lambda input_str, **kwargs: _send_impl(
                to=kwargs.get("to"),
                subject=kwargs.get("subject"),
                message=(
                    kwargs.get("message")
                    if kwargs.get("message") is not None
                    else (input_str if isinstance(input_str, str) else "")
                ),
                is_html=bool(kwargs.get("is_html")),
            ),
        )
    tools.append(gmail_send_tool)

    # Get specific message tool
    if StructuredTool:
        gmail_get_tool = StructuredTool.from_function(
            name="gmail_get_message",
            description=(
                "Get a specific email by its message ID. "
                "Use this when you have a specific message ID and need its full details."
            ),
            func=_get_impl,
            args_schema=GmailGetMessageArgs,
        )
    else:
        gmail_get_tool = CoreTool(
            name="gmail_get_message",
            description="Get a specific email by message ID.",
            func=lambda message_id: gmail_get_message(message_id=message_id, agent_id=agent_id),
        )
    tools.append(gmail_get_tool)

    # Unified tool — mirrors n8n-like node with action
    if StructuredTool:
        gmail_unified_tool = StructuredTool.from_function(
            name="gmail",
            description=(
                "Unified Gmail tool. Use read/search for fetching data and summarization; get for a specific email by ID; "
                "send ONLY when the user explicitly asks to send."
            ),
            func=_unified_impl,
            args_schema=GmailUnifiedArgs,
        )
    else:
        gmail_unified_tool = CoreTool(
            name="gmail",
            description="Unified Gmail tool (legacy). Provide JSON with action and fields.",
            func=lambda s: "Provide structured input with action and fields.",
        )
    tools.append(gmail_unified_tool)

    return tools


# -----------------------------
# OAuth Helper Function
# -----------------------------
def build_gmail_oauth_url(state: Optional[str] = None) -> Optional[str]:
    """
    Build OAuth URL for Gmail authentication.
    """
    secrets_candidates = [
        os.getenv("GMAIL_CLIENT_SECRETS_PATH"),
        os.path.join(_default_gmail_dir(), "credentials.json"),
        os.path.join(os.getcwd(), "credentials.json"),
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    ]
    
    secrets_path = next((p for p in secrets_candidates if p and os.path.exists(p)), None)
    # Prefer a universal redirect if configured, else provider-specific
    redirect_uri = (
        os.getenv("GOOGLE_OAUTH_REDIRECT_URI")
        or os.getenv("OAUTH_REDIRECT_URI")
        or os.getenv("GMAIL_REDIRECT_URI")
    )
    
    if not secrets_path or not redirect_uri or not os.path.exists(secrets_path):
        return None
    
    try:
        with open(secrets_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        client_id = (
            data.get("web", {}).get("client_id") or 
            data.get("installed", {}).get("client_id")
        )
        
        if not client_id:
            return None
    except Exception:
        return None
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    
    if state:
        params["state"] = state
    
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


# -----------------------------
# Export Tools
# -----------------------------
# Create the tools
all_tools = create_gmail_tools()

# Export individual tools for backward compatibility
gmail_search_tool = all_tools[0] if len(all_tools) > 0 else None
gmail_read_messages_tool = all_tools[1] if len(all_tools) > 1 else None
gmail_send_message_tool = all_tools[2] if len(all_tools) > 2 else None
gmail_get_message_tool = all_tools[3] if len(all_tools) > 3 else None
# unified tool is appended last
gmail_tool = all_tools[4] if len(all_tools) > 4 else None

# For convenience, also export as a list
gmail_tools = all_tools

__all__ = [
    "gmail_search_tool",
    "gmail_read_messages_tool",
    "gmail_send_message_tool",
    "gmail_get_message_tool",
    "gmail_tool",
    "gmail_tools",
    "build_gmail_oauth_url",
    "create_gmail_tools",
]