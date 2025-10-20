import os
from typing import Dict, Any, List, Optional, Tuple
import re
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64

from app.tools.base import BaseTool
from app.services.auth_service import AuthService


class GmailTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="gmail",
            description="Read and send emails using Gmail",
            schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "read",
                            "send",
                            "list",
                            "search",
                            "get_message",
                            "get_thread",
                            "send_message",
                            "create_draft",
                            "get"
                        ],
                        "description": "Action to perform (optional; inferred from other fields when omitted)."
                    },
                    "email_id": {
                        "type": "string",
                        "description": "Email ID for reading (required for read action)"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Alias for email_id when reading a message"
                    },
                    "to": {
                        "type": "string",
                        "description": "Recipient email (required for send action)"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject (required for send action)"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body (required for send action)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Alias for email body used by LangChain GmailSendMessage"
                    },
                    "is_html": {
                        "type": "boolean",
                        "description": "When true, treat message body as HTML"
                    },
                    "cc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional CC recipients for send/create_draft actions"
                    },
                    "bcc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional BCC recipients for send/create_draft actions"
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of emails to list"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query for listing emails"
                    },
                    "mark_as_read": {
                        "type": "boolean",
                        "default": False,
                        "description": "When reading, remove the UNREAD label from returned messages"
                    },
                    "label_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Label filters for listing/searching emails"
                    },
                    "thread_id": {
                        "type": "string",
                        "description": "Thread ID for thread retrieval"
                    },
                    "format": {
                        "type": "string",
                        "description": "Message format when retrieving a single email (minimal|full|raw|metadata)",
                        "default": "full"
                    }
                },
                "required": []
            }
        )

    def get_credentials(self, user_id: str, auth_service: AuthService) -> Credentials:
        auth_token = auth_service.get_user_auth_tokens(user_id)
        google_token = next((token for token in auth_token if token.service == "google"), None)

        if not google_token:
            raise ValueError("Google authentication token not found")

        return Credentials(
            token=google_token.access_token,
            refresh_token=google_token.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=auth_service.settings.GOOGLE_CLIENT_ID,
            client_secret=auth_service.settings.GOOGLE_CLIENT_SECRET,
            scopes=google_token.scope
        )

    def execute(self, parameters: Dict[str, Any], user_id: str, auth_service: AuthService) -> Dict[str, Any]:
        from app.core.logging import logger

        parameters = dict(parameters or {})

        # Apply parameter name mapping FIRST (before any validation)
        if parameters.get("labelIds") and not parameters.get("label_ids"):
            parameters["label_ids"] = parameters["labelIds"]
        if parameters.get("maxResults") and not parameters.get("max_results"):
            parameters["max_results"] = parameters["maxResults"]
        if parameters.get("messageId") and not parameters.get("message_id"):
            parameters["message_id"] = parameters["messageId"]

        if parameters.get("message") and not parameters.get("body"):
            parameters["body"] = parameters["message"]
        if parameters.get("body") and not parameters.get("message"):
            parameters["message"] = parameters["body"]

        normalized_label_ids = self._normalize_label_ids(
            parameters.get("label_ids") or parameters.get("labelIds")
        )
        if normalized_label_ids is not None:
            parameters["label_ids"] = normalized_label_ids

        if "max_results" in parameters and parameters["max_results"] is not None:
            try:
                parameters["max_results"] = int(parameters["max_results"])
            except (TypeError, ValueError):
                raise ValueError("Gmail max_results must be an integer value.")

        raw_action = parameters.get("action")
        inferred_action = self._infer_action(parameters)
        action_key = (raw_action or inferred_action or "read").strip().lower()

        action_aliases = {
            "read": "read",
            "get_message": "get_message",
            "open": "read",
            "search": "search",
            "list": "search",
            "find": "search",
            "send": "send",
            "send_message": "send",
            "send_email": "send",
            "create_draft": "create_draft",
            "draft": "create_draft",
            "save_draft": "create_draft",
            "get_thread": "get_thread",
            "thread": "get_thread",
            "get": "get_message",
            "message": "get_message",
            "getmessage": "get_message",
        }
        action = action_aliases.get(action_key)
        if not action:
            raise ValueError(
                "Missing required parameter 'action'. Provide 'send', 'read', 'search', 'create_draft', or 'get_thread', "
                "or include fields (e.g. 'to/subject/body', 'query', 'email_id')."
            )

        parameters["action"] = action

        logger.debug(
            "Gmail tool parameters",
            action=action,
            action_raw=raw_action,
            inferred_action=inferred_action,
            parameters=parameters,
        )

        credentials = self.get_credentials(user_id, auth_service)

        if action in {"send", "create_draft"}:
            self._assert_send_scope(credentials)

        service = build('gmail', 'v1', credentials=credentials, cache_discovery=False)

        last_error: Optional[HttpError] = None
        for attempt in range(2):
            try:
                return self._dispatch_action(service, action, parameters)
            except HttpError as http_error:
                last_error = http_error
                status_code = getattr(http_error, "resp", None)
                status_code = getattr(status_code, "status", None)

                if status_code == 401 and attempt == 0:
                    logger.info(
                        "Refreshing Google credentials after Gmail API 401",
                        attempt=attempt + 1,
                        action=action,
                    )
                    refreshed = auth_service.refresh_google_token(user_id)
                    if not refreshed:
                        raise Exception(
                            "Google authentication expired. Reconnect your Google account to restore Gmail access."
                        )
                    credentials = self.get_credentials(user_id, auth_service)
                    if action in {"send", "create_draft"}:
                        self._assert_send_scope(credentials)
                    service = build('gmail', 'v1', credentials=credentials, cache_discovery=False)
                    continue

                if status_code == 403 and "insufficientPermissions" in str(http_error):
                    raise Exception(
                        "Google account lacks Gmail send permission. Reconnect via OAuth and grant Gmail send/compose scopes."
                    )

                raise Exception(f"Gmail API error: {http_error}")

        if last_error:
            raise Exception(f"Gmail API error: {last_error}")

        raise Exception("Gmail tool execution failed unexpectedly.")

    def _dispatch_action(self, service, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if action == "send":
            missing_fields = []
            if not parameters.get("to"):
                resolved_to = self._resolve_recipients(parameters)
                if resolved_to:
                    parameters["to"] = ", ".join(resolved_to)
            if not parameters.get("to"):
                missing_fields.append("to")
            if not parameters.get("subject"):
                resolved_subject = self._resolve_subject(parameters)
                if resolved_subject:
                    parameters["subject"] = resolved_subject
            if not parameters.get("subject"):
                missing_fields.append("subject")
            message_text = self._resolve_message(parameters)
            if not message_text or not str(message_text).strip():
                missing_fields.append("message")
            else:
                parameters["message"] = str(message_text)
            if missing_fields:
                raise ValueError(
                    "Gmail send action requires fields: 'to', 'subject', and 'message'. Missing: "
                    + ", ".join(missing_fields)
                )
            return self._send_email(service, parameters)

        if action == "read":
            return self._read_messages(service, parameters)

        if action == "search":
            if not parameters.get("query") and not parameters.get("label_ids"):
                parameters.setdefault("max_results", 5)
            return self._search_emails(service, parameters)

        if action == "create_draft":
            # Normalise action indicator so downstream helpers can see the draft intent
            parameters["action"] = "create_draft"
            message_candidate = self._resolve_message(parameters)
            if message_candidate is None or not str(message_candidate).strip():
                fallback_body = self._generate_fallback_body(parameters)
                if fallback_body:
                    message_candidate = fallback_body
                else:
                    provided_keys = ", ".join(sorted(key for key, value in parameters.items() if value not in (None, "", [])))
                    raise ValueError(
                        "Gmail create_draft action requires a non-empty email body. "
                        "Set the 'message' field (or 'body') to the textual content you want in the draft. "
                        f"Provided keys: {provided_keys or 'none'}."
                    )
            subject_candidate = self._resolve_subject(parameters)
            if subject_candidate is None or not str(subject_candidate).strip():
                subject_candidate = self._generate_fallback_subject(parameters, fallback_body=message_candidate)
            if subject_candidate and str(subject_candidate).strip():
                parameters["subject"] = str(subject_candidate).strip()
            parameters["message"] = str(message_candidate)
            return self._create_draft(service, parameters)

        if action == "get_thread":
            thread_id = parameters.get("thread_id") or parameters.get("id")
            if not thread_id:
                raise ValueError("Gmail get_thread action requires 'thread_id'.")
            parameters["thread_id"] = thread_id
            return self._get_thread(service, parameters)

        if action == "get_message":
            message_id = (
                parameters.get("message_id")
                or parameters.get("email_id")
                or parameters.get("id")
            )
            if not message_id:
                raise ValueError("Gmail get_message action requires 'message_id'.")
            message_format = (parameters.get("format") or "full").lower()
            return self._get_single_message(service, message_id, message_format)

        raise ValueError(
            "Unknown Gmail action. Supported actions are 'read', 'search', 'send', 'create_draft', 'get_thread', and 'get_message'."
        )

    def _infer_action(self, parameters: Dict[str, Any]) -> Optional[str]:
        if parameters.get("thread_id"):
            return "get_thread"

        if parameters.get("message_id"):
            return "get_message"

        # Check for send indicators so partially filled drafts still validate downstream
        send_indicators = ("to", "subject", "body", "message", "cc", "bcc")
        if any(parameters.get(field) for field in send_indicators):
            return "send"

        if any(parameters.get(field) for field in ("email_id", "id")):
            return "read"

        search_indicators = ("max_results", "query", "label_ids", "labelIds")
        if any(parameters.get(field) is not None or field in parameters for field in search_indicators):
            return "search"

        return None

    def _read_messages(self, service, parameters: Dict[str, Any]) -> Dict[str, Any]:
        label_ids = self._normalize_label_ids(
            parameters.get("label_ids") or parameters.get("labelIds")
        )

        email_id = (
            parameters.get("email_id")
            or parameters.get("message_id")
            or parameters.get("id")
        )

        message_ids: List[str]
        max_results = int(parameters.get("max_results", 5) or 5)
        if email_id:
            message_ids = [email_id]
        else:
            query = parameters.get("query") or "is:unread"
            message_ids = self._list_message_ids(
                service,
                query=query,
                max_results=max_results,
                label_ids=label_ids,
            )
        if not message_ids:
            return {"messages": [], "count": 0}

        mark_as_read = self._coerce_bool(parameters.get("mark_as_read"))
        messages: List[Dict[str, Any]] = []
        for mid in message_ids[:max_results]:
            message = self._get_single_message(
                service,
                message_id=mid,
                message_format=(parameters.get("format") or "full").lower(),
            )
            messages.append(message)
            if mark_as_read:
                try:
                    service.users().messages().modify(
                        userId='me',
                        id=mid,
                        body={"removeLabelIds": ["UNREAD"]},
                    ).execute()
                except HttpError:
                    # Ignore failures to mark as read so read result still returns
                    pass

        return {"messages": messages, "count": len(messages)}

    def _send_email(self, service, parameters: Dict[str, Any]) -> Dict[str, Any]:
        raw_message, to_recipients, cc_recipients, bcc_recipients, subject = self._build_email_message(parameters)

        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

        return {
            "id": sent_message['id'],
            "status": "sent",
            "to": to_recipients,
            "cc": cc_recipients,
            "bcc": bcc_recipients,
            "subject": subject
        }

    def _list_message_ids(
        self,
        service,
        query: Optional[str],
        max_results: int,
        label_ids: Optional[List[str]] = None,
    ) -> List[str]:
        list_params = {
            'userId': 'me',
            'maxResults': max_results,
        }

        if query:
            list_params['q'] = query

        if label_ids:
            list_params['labelIds'] = label_ids

        results = service.users().messages().list(**list_params).execute()
        messages = results.get('messages', []) or []
        return [msg['id'] for msg in messages if msg.get('id')]

    def _search_emails(self, service, parameters: Dict[str, Any]) -> Dict[str, Any]:
        max_results = int(parameters.get("max_results", 10) or 10)
        label_ids = self._normalize_label_ids(
            parameters.get("label_ids") or parameters.get("labelIds")
        )

        message_ids = self._list_message_ids(
            service,
            query=parameters.get("query"),
            max_results=max_results,
            label_ids=label_ids,
        )

        summaries: List[Dict[str, Any]] = []
        for mid in message_ids[:max_results]:
            message = service.users().messages().get(
                userId='me',
                id=mid,
                format='metadata',
                metadataHeaders=['Subject', 'From', 'Date', 'To'],
            ).execute()
            headers = self._headers_to_dict(message.get('payload', {}).get('headers', []))
            summaries.append({
                "id": mid,
                "subject": headers.get('subject', ''),
                "from": headers.get('from', ''),
                "to": headers.get('to', ''),
                "date": headers.get('date', ''),
                "snippet": message.get('snippet', ''),
                "label_ids": message.get('labelIds', []),
            })

        return {"emails": summaries, "count": len(summaries)}

    def _create_draft(self, service, parameters: Dict[str, Any]) -> Dict[str, Any]:
        raw_message, to_recipients, cc_recipients, bcc_recipients, subject = self._build_email_message(
            parameters,
            allow_empty_recipients=True,
            allow_empty_message=False,
        )

        draft = service.users().drafts().create(
            userId='me',
            body={'message': {'raw': raw_message}}
        ).execute()

        return {
            "id": draft['id'],
            "status": "draft_created",
            "to": to_recipients,
            "cc": cc_recipients,
            "bcc": bcc_recipients,
            "subject": subject
        }

    def _get_thread(self, service, parameters: Dict[str, Any]) -> Dict[str, Any]:
        thread_id = parameters["thread_id"]
        thread = service.users().threads().get(userId='me', id=thread_id).execute()

        messages = []
        for message in thread.get('messages', []):
            parsed = self._parse_message(message)
            parsed["id"] = message.get('id')
            parsed["thread_id"] = thread_id
            messages.append(parsed)

        return {
            "thread_id": thread_id,
            "messages": messages,
            "message_count": len(messages)
        }

    def _get_single_message(
        self,
        service,
        message_id: str,
        message_format: str = "full",
    ) -> Dict[str, Any]:
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format=message_format,
        ).execute()

        if message_format == "full":
            parsed = self._parse_message(message)
            parsed.update(
                {
                    "id": message_id,
                    "thread_id": message.get('threadId'),
                    "label_ids": message.get('labelIds', []),
                }
            )
            return parsed

        response: Dict[str, Any] = {
            "id": message_id,
            "thread_id": message.get('threadId'),
            "label_ids": message.get('labelIds', []),
            "snippet": message.get('snippet'),
        }

        if message_format == "raw":
            response["raw"] = message.get('raw')
        else:
            response["payload"] = message.get('payload')

        return response

    def _resolve_message(self, parameters: Dict[str, Any]) -> Optional[Any]:
        preferred_keys = [
            "message",
            "body",
            "email_body",
            "draft_body",
            "message_body",
            "content",
            "text",
            "body_text",
            "template",
            "email_content",
            "emailText",
            "email_text",
            "bodyContent",
            "body_content",
            "draft_content",
            "prompt",
            "instructions",
            "instruction",
            "summary",
            "context",
            "description",
        ]

        normalized_params = {
            str(key).lower(): value for key, value in parameters.items() if isinstance(key, str)
        }

        for key in preferred_keys:
            candidate = normalized_params.get(key)
            if candidate is None:
                continue
            extracted = self._extract_message_content(candidate)
            if extracted is not None:
                return extracted

        # Fall back to scanning non-string values for nested message content
        for value in parameters.values():
            if isinstance(value, str):
                continue
            extracted = self._extract_message_content(value)
            if extracted:
                return extracted
        return None

    def _resolve_subject(self, parameters: Dict[str, Any]) -> Optional[str]:
        normalized = {
            str(key).lower(): value for key, value in parameters.items() if isinstance(key, str)
        }

        subject_keys = [
            "subject",
            "title",
            "topic",
            "agenda",
            "headline",
            "summary",
            "judul",
        ]

        for key in subject_keys:
            if key in normalized:
                extracted = self._extract_message_content(normalized[key])
                if extracted:
                    cleaned = str(extracted).strip()
                    if cleaned:
                        return cleaned

        # Look for nested structures that may include a subject-like field
        for value in parameters.values():
            if isinstance(value, dict):
                for nested_key in subject_keys:
                    if nested_key in value:
                        extracted = self._extract_message_content(value[nested_key])
                        if extracted:
                            cleaned = str(extracted).strip()
                            if cleaned:
                                return cleaned
        return None

    def _extract_message_content(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for possible_key in (
                "text",
                "content",
                "message",
                "body",
                "value",
                "prompt",
                "summary",
                "instructions",
                "instruction",
                "template",
                "email",
                "email_text",
                "email_body",
            ):
                nested = value.get(possible_key)
                if nested:
                    extracted = self._extract_message_content(nested)
                    if extracted is not None:
                        return extracted
            # Handle lists embedded in "parts", "items", etc.
            for list_key in ("parts", "items", "sections", "messages", "content"):
                if list_key in value and isinstance(value[list_key], (list, tuple, set)):
                    extracted = self._extract_message_content(list(value[list_key]))
                    if extracted:
                        return extracted
            return None
        if isinstance(value, (list, tuple, set)):
            parts = [
                part for part in (self._extract_message_content(item) for item in value)
                if part
            ]
            if parts:
                return "\n".join(parts)
            return None
        return str(value)

    def _generate_fallback_body(self, parameters: Dict[str, Any]) -> Optional[str]:
        """Generate a simple fallback body when the agent omits one."""
        normalized = {
            str(key).lower(): value for key, value in parameters.items() if isinstance(key, str)
        }

        context_keys = [
            "instructions",
            "instruction",
            "prompt",
            "summary",
            "context",
            "description",
            "notes",
            "request",
            "goal",
        ]

        context_snippets: List[str] = []
        for key in context_keys:
            value = parameters.get(key)
            if not value:
                continue
            extracted = self._extract_message_content(value)
            if extracted:
                cleaned = str(extracted).strip()
                if cleaned:
                    context_snippets.append(cleaned)

        def _pick(keys: List[str]) -> Optional[str]:
            for key in keys:
                lower_key = key.lower()
                if lower_key in normalized:
                    candidate = self._extract_message_content(normalized[lower_key])
                    if candidate:
                        return str(candidate).strip()
            return None

        subject = _pick(["subject", "title"])
        to = _pick(["to", "recipient", "recipient_email", "to_email", "email"])
        date = _pick(["date", "tanggal", "day"])
        time = _pick(["time", "waktu"])
        location = _pick(["location", "lokasi", "place", "venue"])
        agenda = _pick(["agenda", "topic", "purpose"])

        if not context_snippets and not subject and not agenda:
            return None

        lines: List[str] = []
        greeting = "Hello everyone,"
        if to:
            greeting = f"Hello {to},"
        lines.append(greeting)

        if subject:
            lines.append("")
            lines.append(f"This is an invitation to our {subject}.")
        else:
            lines.append("")
            lines.append("This is an invitation to our upcoming meeting.")

        if date or time:
            schedule_sentence = "It will take place"
            if date:
                schedule_sentence += f" on {date}"
            if time:
                schedule_sentence += f" at {time}"
            schedule_sentence += "."
            lines.append(schedule_sentence)

        if location:
            lines.append(f"The meeting location is {location}.")

        if agenda:
            lines.append(f"Agenda: {agenda}.")

        if context_snippets:
            lines.append("")
            lines.append(context_snippets[0])

        lines.append("")
        lines.append("Please let me know if you need any adjustments or have additional topics to discuss.")
        lines.append("")
        lines.append("Best regards,")
        lines.append("[Your Name]")

        body = "\n".join(line for line in lines if line is not None).strip()
        return body or None

    def _generate_fallback_subject(
        self,
        parameters: Dict[str, Any],
        *,
        fallback_body: Optional[str] = None,
    ) -> Optional[str]:
        normalized = {
            str(key).lower(): value for key, value in parameters.items() if isinstance(key, str)
        }

        # Try to infer from provided fields
        candidates = [
            "subject",
            "title",
            "topic",
            "agenda",
            "summary",
            "judul",
        ]

        for key in candidates:
            if key in normalized:
                extracted = self._extract_message_content(normalized[key])
                if extracted:
                    cleaned = str(extracted).strip()
                    if cleaned:
                        return cleaned

        # Use date/time hint if available
        date = self._extract_message_content(normalized.get("date") or normalized.get("tanggal"))
        time = self._extract_message_content(normalized.get("time") or normalized.get("waktu"))
        if date or time:
            schedule = " ".join(part for part in [date, time] if part).strip()
            if schedule:
                return f"Meeting on {schedule}"

        # Use fallback body snippet
        if fallback_body:
            first_line = str(fallback_body).strip().splitlines()[0]
            if first_line:
                return first_line[:120]

        return "Draft Email"

    def _build_email_message(
        self,
        parameters: Dict[str, Any],
        allow_empty_recipients: bool = False,
        allow_empty_message: bool = False,
    ) -> Tuple[str, List[str], List[str], List[str], Optional[str]]:
        from email.mime.text import MIMEText

        message_text = self._resolve_message(parameters)
        if (message_text is None or not str(message_text).strip()) and not allow_empty_message:
            raise ValueError("Gmail send/create_draft actions require a 'message' field.")

        body = str(message_text or "")
        to_recipients = self._resolve_recipients(parameters)
        if to_recipients:
            parameters["to"] = ", ".join(to_recipients)

        if not to_recipients and not allow_empty_recipients:
            raise ValueError("Gmail send action requires at least one 'to' recipient.")

        is_html = self._coerce_bool(parameters.get("is_html"))
        subtype = 'html' if is_html else 'plain'
        message = MIMEText(body, subtype, 'utf-8')
        if to_recipients:
            message['to'] = ", ".join(to_recipients)

        subject = parameters.get("subject")
        if subject:
            message['subject'] = str(subject)

        cc_recipients = self._normalise_recipients(parameters.get("cc"))
        if cc_recipients:
            message['cc'] = ", ".join(cc_recipients)

        bcc_recipients = self._normalise_recipients(parameters.get("bcc"))
        if bcc_recipients:
            message['bcc'] = ", ".join(bcc_recipients)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return raw_message, to_recipients, cc_recipients, bcc_recipients, subject

    def _resolve_recipients(self, parameters: Dict[str, Any]) -> List[str]:
        """Resolve recipient email addresses from various possible fields."""
        recipients = self._normalise_recipients(parameters.get("to"))
        if recipients:
            return recipients

        normalized = {
            str(key).lower(): value for key, value in parameters.items() if isinstance(key, str)
        }

        candidate_keys = [
            "recipient",
            "recipient_email",
            "to_email",
            "email",
            "email_address",
            "destination",
            "destination_email",
            "send_to",
            "target_email",
            "contact",
        ]

        for key in candidate_keys:
            if key in normalized:
                possible = self._normalise_recipients(normalized[key])
                if possible:
                    return possible

        # Inspect nested structures for email-like strings
        nested_candidates: List[str] = []
        for value in parameters.values():
            extracted = self._extract_message_content(value)
            if extracted and "@" in extracted:
                nested_candidates.extend(self._normalise_recipients(extracted))

        deduped: List[str] = []
        for email in nested_candidates:
            if email not in deduped:
                deduped.append(email)
        return deduped

    def _normalize_label_ids(self, value: Any) -> Optional[List[str]]:
        """Normalize label identifiers into a list of strings for the Gmail API."""
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return None
            if "," in cleaned:
                parts = [part.strip() for part in cleaned.split(",") if part.strip()]
                return parts or None
            return [cleaned]
        if isinstance(value, (list, tuple, set)):
            normalized: List[str] = []
            for item in value:
                if item is None:
                    continue
                cleaned = str(item).strip()
                if cleaned:
                    normalized.append(cleaned)
            return normalized or None
        # Fallback: cast single value to string
        cleaned = str(value).strip()
        return [cleaned] if cleaned else None

    def _normalise_recipients(self, value) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            parts = [part.strip() for part in value.split(',')]
            return [part for part in parts if part]
        if isinstance(value, (list, tuple, set)):
            recipients: List[str] = []
            for entry in value:
                if not entry:
                    continue
                entry_str = entry if isinstance(entry, str) else str(entry)
                recipients.extend(self._normalise_recipients(entry_str))
            return recipients
        raise ValueError("Recipient fields must be a string or a list of strings.")

    def _coerce_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "y", "on"}
        if value is None:
            return False
        return bool(value)

    def _assert_send_scope(self, credentials: Credentials) -> None:
        required_send_scopes = {
            "https://mail.google.com/",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.compose",
        }

        scopes = set(credentials.scopes or [])
        if not scopes:
            # Some credentials objects do not expose scopes until refreshed; defer to Gmail API
            return

        if scopes.intersection(required_send_scopes):
            return

        raise Exception(
            "Google account lacks Gmail send permission. Reconnect via OAuth and grant Gmail send/compose scopes."
        )

    def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get('payload', {})
        headers_dict = self._headers_to_dict(payload.get('headers', []))

        body_text, body_html = self._extract_message_body(payload)

        max_chars = int(os.getenv("GMAIL_MAX_BODY_CHARS", "5000") or 5000)
        if body_text and len(body_text) > max_chars:
            body_text = body_text[:max_chars] + "... [truncated]"
        if body_html and len(body_html) > max_chars:
            body_html = body_html[:max_chars] + "... [truncated]"

        return {
            "subject": headers_dict.get('subject', ''),
            "from": headers_dict.get('from', ''),
            "to": headers_dict.get('to', ''),
            "cc": headers_dict.get('cc', ''),
            "bcc": headers_dict.get('bcc', ''),
            "reply_to": headers_dict.get('reply-to', ''),
            "date": headers_dict.get('date', ''),
            "snippet": message.get('snippet'),
            "body_text": body_text,
            "body_html": body_html,
        }

    def _headers_to_dict(self, headers: Optional[List[Dict[str, Any]]]) -> Dict[str, str]:
        mapped: Dict[str, str] = {}
        for header in headers or []:
            name = header.get('name')
            value = header.get('value')
            if not name:
                continue
            mapped[name.lower()] = value or ''
        return mapped

    def _extract_message_body(self, payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        mime_type = payload.get('mimeType', '')
        body = payload.get('body', {}) or {}
        data = body.get('data')

        text_plain: Optional[str] = None
        text_html: Optional[str] = None

        if mime_type == 'text/plain' and data:
            text_plain = self._decode_base64(data)
        elif mime_type == 'text/html' and data:
            text_html = self._decode_base64(data)

        for part in payload.get('parts', []) or []:
            plain, html = self._extract_message_body(part)
            text_plain = text_plain or plain
            text_html = text_html or html
            if text_plain and text_html:
                break

        return text_plain, text_html

    def _decode_base64(self, data: str) -> str:
        try:
            padded = data + '=' * (-len(data) % 4)
            return base64.urlsafe_b64decode(padded.encode('utf-8')).decode('utf-8', errors='ignore')
        except Exception:
            return ''


class GoogleSheetsTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="google_sheets",
            description="Read and write data from Google Sheets",
            schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["read", "write", "create"],
                        "description": "Action to perform (optional; inferred from other fields when omitted)"
                    },
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "Spreadsheet ID (required for read/write)"
                    },
                    "range": {
                        "type": "string",
                        "description": "Sheet range (e.g., 'Sheet1!A1:D10')"
                    },
                    "values": {
                        "type": "array",
                        "description": "Values to write (required for write action)"
                    },
                    "title": {
                        "type": "string",
                        "description": "Sheet title (required for create action)"
                    }
                },
                "required": []
            }
        )

    def execute(self, parameters: Dict[str, Any], user_id: str, auth_service: AuthService) -> Dict[str, Any]:
        from app.tools.google_tools import GmailTool

        gmail_tool = GmailTool()
        credentials = gmail_tool.get_credentials(user_id, auth_service)
        service = build('sheets', 'v4', credentials=credentials)
        parameters = dict(parameters)
        if parameters.get("spreadsheetId") and not parameters.get("spreadsheet_id"):
            parameters["spreadsheet_id"] = parameters["spreadsheetId"]
        if parameters.get("rangeName") and not parameters.get("range"):
            parameters["range"] = parameters["rangeName"]

        action_raw = parameters.get("action")
        inferred_action = self._infer_action(parameters)
        action = (action_raw or inferred_action or "").strip().lower()

        # If we have an explicit action, use it even if we can't infer from other parameters
        if action_raw and action_raw.strip():
            action = action_raw.strip().lower()
            parameters["action"] = action
        elif inferred_action:
            action = inferred_action
            parameters["action"] = action
        elif not action:
            raise ValueError(
                "Missing required parameter 'action'. Provide 'read', 'write', or 'create', or include fields such as "
                "'title' for creating a sheet, 'values' for writing, or 'spreadsheet_id' for reading."
            )

        try:
            if action == "read":
                if not parameters.get("spreadsheet_id"):
                    raise ValueError("Google Sheets read action requires 'spreadsheet_id'.")
                return self._read_sheet(service, parameters)
            elif action == "write":
                if not parameters.get("spreadsheet_id"):
                    raise ValueError("Google Sheets write action requires 'spreadsheet_id'.")
                if parameters.get("values") is None:
                    raise ValueError("Google Sheets write action requires 'values'.")
                if not parameters.get("range"):
                    raise ValueError("Google Sheets write action requires 'range'.")
                return self._write_sheet(service, parameters)
            elif action == "create":
                if not parameters.get("title"):
                    raise ValueError("Google Sheets create action requires 'title'.")
                return self._create_sheet(service, parameters)
            else:
                raise ValueError(
                    "Unknown Google Sheets action. Supported actions are 'read', 'write', and 'create'."
                )

        except Exception as e:
            raise Exception(f"Google Sheets API error: {e}")

    def _infer_action(self, parameters: Dict[str, Any]) -> Optional[str]:
        if parameters.get("title"):
            return "create"

        if parameters.get("values") is not None:
            return "write"

        if parameters.get("spreadsheet_id") or parameters.get("spreadsheetId"):
            return "read"

        return None

    def _read_sheet(self, service, parameters: Dict[str, Any]) -> Dict[str, Any]:
        spreadsheet_id = parameters["spreadsheet_id"]
        range_name = parameters.get("range", "Sheet1!A1:Z")

        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()

        values = result.get('values', [])
        return {
            "spreadsheet_id": spreadsheet_id,
            "range": range_name,
            "values": values,
            "row_count": len(values)
        }

    def _write_sheet(self, service, parameters: Dict[str, Any]) -> Dict[str, Any]:
        spreadsheet_id = parameters["spreadsheet_id"]
        range_name = parameters["range"]
        values = parameters["values"]

        body = {
            "values": values
        }

        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body=body
        ).execute()

        return {
            "spreadsheet_id": spreadsheet_id,
            "range": range_name,
            "updated_cells": result.get("updatedCells", 0)
        }

    def _create_sheet(self, service, parameters: Dict[str, Any]) -> Dict[str, Any]:
        title = parameters["title"]

        spreadsheet = {
            "properties": {
                "title": title
            }
        }

        result = service.spreadsheets().create(body=spreadsheet).execute()

        return {
            "spreadsheet_id": result["spreadsheetId"],
            "title": title,
            "url": result["spreadsheetUrl"]
        }


class GoogleCalendarTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="google_calendar",
            description="List and create Google Calendar events",
            schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list_events", "create_event", "get_event"],
                        "description": "Calendar action to perform (optional; inferred from other fields)"
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID (defaults to 'primary')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of events to list",
                        "default": 10
                    },
                    "time_min": {
                        "type": "string",
                        "description": "RFC3339 start window for listing events"
                    },
                    "time_max": {
                        "type": "string",
                        "description": "RFC3339 end window for listing events"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Event title (create_event)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description"
                    },
                    "location": {
                        "type": "string",
                        "description": "Event location"
                    },
                    "start": {
                        "type": "string",
                        "description": "Event start in RFC3339 or YYYY-MM-DD format"
                    },
                    "end": {
                        "type": "string",
                        "description": "Event end in RFC3339 or YYYY-MM-DD format"
                    },
                    "time_zone": {
                        "type": "string",
                        "description": "Time zone for start/end when using dateTime values"
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of attendee email addresses"
                    },
                    "event_id": {
                        "type": "string",
                        "description": "Event ID for get_event"
                    }
                },
                "required": []
            }
        )

    def execute(self, parameters: Dict[str, Any], user_id: str, auth_service: AuthService) -> Dict[str, Any]:
        from app.tools.google_tools import GmailTool

        parameters = dict(parameters or {})

        calendar_id = parameters.get("calendar_id") or "primary"
        if parameters.get("start_time") and not parameters.get("start"):
            parameters["start"] = parameters["start_time"]
        if parameters.get("end_time") and not parameters.get("end"):
            parameters["end"] = parameters["end_time"]

        action_raw = parameters.get("action")
        inferred_action = self._infer_action(parameters)
        action = (action_raw or inferred_action or "").strip().lower()
        if not action:
            raise ValueError(
                "Missing required parameter 'action'. Use 'list_events', 'create_event', or 'get_event', or provide fields such as 'summary/start/end'."
            )

        gmail_tool = GmailTool()
        credentials = gmail_tool.get_credentials(user_id, auth_service)
        service = build('calendar', 'v3', credentials=credentials)

        try:
            if action == "list_events":
                return self._list_events(service, calendar_id, parameters)
            if action == "create_event":
                return self._create_event(service, calendar_id, parameters)
            if action == "get_event":
                event_id = parameters.get("event_id")
                if not event_id:
                    raise ValueError("Google Calendar get_event action requires 'event_id'.")
                return self._get_event(service, calendar_id, event_id)
        except HttpError as exc:
            raise Exception(f"Google Calendar API error: {exc}")

        raise ValueError("Unknown Google Calendar action. Supported actions are 'list_events', 'create_event', and 'get_event'.")

    def _infer_action(self, parameters: Dict[str, Any]) -> Optional[str]:
        if parameters.get("event_id"):
            return "get_event"
        if parameters.get("summary") or parameters.get("start") or parameters.get("end"):
            return "create_event"
        return "list_events"

    def _list_events(self, service, calendar_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        max_results = int(parameters.get("max_results") or 10)
        query_params: Dict[str, Any] = {
            "calendarId": calendar_id,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if parameters.get("time_min"):
            query_params["timeMin"] = parameters["time_min"]
        if parameters.get("time_max"):
            query_params["timeMax"] = parameters["time_max"]

        events_result = service.events().list(**query_params).execute()
        events = events_result.get('items', [])

        simplified = []
        for event in events:
            start = event.get('start', {})
            end = event.get('end', {})
            simplified.append({
                "id": event.get('id'),
                "summary": event.get('summary'),
                "start": start.get('dateTime') or start.get('date'),
                "end": end.get('dateTime') or end.get('date'),
                "time_zone": start.get('timeZone') or end.get('timeZone'),
                "attendees": [a.get('email') for a in event.get('attendees', []) if a.get('email')],
                "html_link": event.get('htmlLink'),
                "location": event.get('location'),
            })

        return {"events": simplified, "count": len(simplified)}

    def _create_event(self, service, calendar_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        summary = parameters.get("summary") or "Untitled Event"
        start_value = parameters.get("start")
        end_value = parameters.get("end")
        if not start_value or not end_value:
            raise ValueError("Google Calendar create_event action requires 'start' and 'end' fields (RFC3339 or YYYY-MM-DD).")

        timezone = parameters.get("time_zone") or parameters.get("timezone")
        start_payload = self._build_event_time(start_value, timezone)
        end_payload = self._build_event_time(end_value, timezone)

        event_body: Dict[str, Any] = {
            "summary": summary,
            "start": start_payload,
            "end": end_payload,
        }

        if parameters.get("description"):
            event_body["description"] = parameters["description"]
        if parameters.get("location"):
            event_body["location"] = parameters["location"]

        attendees = self._normalise_recipients(parameters.get("attendees"))
        if attendees:
            invalid_attendees = [email for email in attendees if not self._is_valid_email(email)]
            if invalid_attendees:
                raise ValueError(
                    "Google Calendar attendees must be valid email addresses. Invalid entries: "
                    + ", ".join(invalid_attendees)
                )
            event_body["attendees"] = [{"email": email} for email in attendees]

        created = service.events().insert(calendarId=calendar_id, body=event_body).execute()

        return {
            "id": created.get('id'),
            "status": created.get('status'),
            "summary": created.get('summary'),
            "start": created.get('start'),
            "end": created.get('end'),
            "html_link": created.get('htmlLink'),
        }

    def _get_event(self, service, calendar_id: str, event_id: str) -> Dict[str, Any]:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        return event

    def _build_event_time(self, value: str, timezone: Optional[str]) -> Dict[str, Any]:
        if isinstance(value, dict):
            cleaned: Dict[str, Any] = {}
            if value.get("dateTime"):
                cleaned["dateTime"] = value["dateTime"]
                cleaned["timeZone"] = value.get("timeZone") or timezone
            elif value.get("date"):
                cleaned["date"] = value["date"]
                if value.get("timeZone") or timezone:
                    cleaned["timeZone"] = value.get("timeZone") or timezone
            return cleaned

        value = str(value).strip()
        if "T" in value:
            payload = {"dateTime": value}
            if timezone:
                payload["timeZone"] = timezone
            return payload
        return {"date": value}

    def _normalise_recipients(self, value) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            parts = [part.strip() for part in value.split(',')]
            return [part for part in parts if part]
        if isinstance(value, (list, tuple, set)):
            recipients: List[str] = []
            for entry in value:
                if not entry:
                    continue
                entry_str = entry if isinstance(entry, str) else str(entry)
                recipients.extend(self._normalise_recipients(entry_str))
            return recipients
        raise ValueError("Attendees must be provided as a string or list of strings.")

    def _is_valid_email(self, value: str) -> bool:
        return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value))


class GmailActionTool(BaseTool):
    """Shared wrapper for Gmail sub-tools leveraging the unified GmailTool implementation."""

    REQUIRED_SCOPES: List[str] = []

    def __init__(
        self,
        *,
        name: str,
        description: str,
        schema: Dict[str, Any],
        action: Optional[str] = None,
    ):
        super().__init__(name=name, description=description, schema=schema)
        self._action = action
        self._gmail_delegate = GmailTool()

    def execute(
        self,
        parameters: Dict[str, Any],
        user_id: str,
        auth_service: AuthService
    ) -> Dict[str, Any]:
        payload = dict(parameters or {})
        if self._action:
            payload.setdefault("action", self._action)
        return self._gmail_delegate.execute(payload, user_id, auth_service)


class GmailGetMessageTool(GmailActionTool):
    REQUIRED_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(self) -> None:
        super().__init__(
            name="gmail_get_message",
            description="Retrieve a Gmail message by ID with optional format selection.",
            action="get_message",
            schema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "Message ID to retrieve."
                    },
                    "email_id": {
                        "type": "string",
                        "description": "Alias for message_id to support legacy flows."
                    },
                    "format": {
                        "type": "string",
                        "enum": ["full", "metadata", "minimal", "raw"],
                        "default": "full",
                        "description": "Level of detail to return."
                    }
                },
                "required": []
            },
        )


class GmailReadMessagesTool(GmailActionTool):
    REQUIRED_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(self) -> None:
        super().__init__(
            name="gmail_read_messages",
            description="Read one or more Gmail messages, optionally marking them as read.",
            action="read",
            schema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "Specific message ID to read."
                    },
                    "email_id": {
                        "type": "string",
                        "description": "Alias for message_id."
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 5,
                        "description": "Maximum number of unread messages to fetch when no ID is supplied."
                    },
                    "label_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter unread retrieval by label."
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional Gmail search query used when no message_id is provided."
                    },
                    "mark_as_read": {
                        "type": "boolean",
                        "description": "Whether to remove the UNREAD label from returned messages."
                    },
                    "format": {
                        "type": "string",
                        "enum": ["full", "metadata", "minimal", "raw"],
                        "default": "full",
                        "description": "Level of detail to return."
                    }
                },
                "required": []
            },
        )


class GmailListMessagesTool(GmailActionTool):
    REQUIRED_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(self) -> None:
        super().__init__(
            name="gmail_list_messages",
            description="List Gmail messages using query parameters without retrieving full bodies.",
            action="search",
            schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query (e.g. 'from:example@domain.com')."
                    },
                    "label_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional label filters."
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of messages to return."
                    }
                },
                "required": []
            },
        )


class GmailSendMessageTool(GmailActionTool):
    REQUIRED_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

    def __init__(self) -> None:
        super().__init__(
            name="gmail_send_message",
            description="Send an email via Gmail on behalf of the authenticated user.",
            action="send",
            schema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Primary recipient email address."
                    },
                    "cc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional CC recipients."
                    },
                    "bcc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional BCC recipients."
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line."
                    },
                    "body": {
                        "type": "string",
                        "description": "Plain-text or HTML email body."
                    },
                    "message": {
                        "type": "string",
                        "description": "Alias for body to ease LangChain integrations."
                    },
                    "is_html": {
                        "type": "boolean",
                        "description": "Treat the body/message as HTML content when true."
                    }
                },
                "required": ["to", "subject"]
            },
        )


class GmailCreateDraftTool(GmailActionTool):
    REQUIRED_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

    def __init__(self) -> None:
        super().__init__(
            name="gmail_create_draft",
            description="Create a Gmail draft message.",
            action="create_draft",
            schema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Primary recipient for the draft."
                    },
                    "cc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional CC recipients."
                    },
                    "bcc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional BCC recipients."
                    },
                    "subject": {
                        "type": "string",
                        "description": "Draft subject."
                    },
                    "body": {
                        "type": "string",
                        "description": "Draft body content."
                    },
                    "message": {
                        "type": "string",
                        "description": "Alias for body content."
                    },
                    "is_html": {
                        "type": "boolean",
                        "description": "Treat body/message as HTML when true."
                    }
                },
                "anyOf": [
                    {"required": ["message"]},
                    {"required": ["body"]}
                ]
            },
        )


class GmailGetThreadTool(GmailActionTool):
    REQUIRED_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(self) -> None:
        super().__init__(
            name="gmail_get_thread",
            description="Retrieve a Gmail conversation thread by ID.",
            action="get_thread",
            schema={
                "type": "object",
                "properties": {
                    "thread_id": {
                        "type": "string",
                        "description": "Thread identifier to fetch."
                    }
                },
                "required": ["thread_id"]
            },
        )


class GoogleSheetsActionTool(BaseTool):
    """Wrapper for Sheets sub-tools to reuse GoogleSheetsTool logic."""

    REQUIRED_SCOPES: List[str] = []

    def __init__(
        self,
        *,
        name: str,
        description: str,
        schema: Dict[str, Any],
        action: str,
    ):
        super().__init__(name=name, description=description, schema=schema)
        self._action = action
        self._delegate = GoogleSheetsTool()

    def execute(
        self,
        parameters: Dict[str, Any],
        user_id: str,
        auth_service: AuthService
    ) -> Dict[str, Any]:
        payload = dict(parameters or {})
        payload.setdefault("action", self._action)
        return self._delegate.execute(payload, user_id, auth_service)


class GoogleSheetsReadTool(GoogleSheetsActionTool):
    REQUIRED_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    def __init__(self) -> None:
        super().__init__(
            name="google_sheets_get_values",
            description="Read values from a Google Sheet range.",
            action="read",
            schema={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "Target spreadsheet ID."
                    },
                    "range": {
                        "type": "string",
                        "description": "A1-style range to read (defaults to Sheet1!A1:Z)."
                    }
                },
                "required": ["spreadsheet_id"]
            },
        )


class GoogleSheetsWriteTool(GoogleSheetsActionTool):
    REQUIRED_SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
    ]

    def __init__(self) -> None:
        super().__init__(
            name="google_sheets_update_values",
            description="Write values to a Google Sheet range.",
            action="write",
            schema={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "Target spreadsheet ID."
                    },
                    "range": {
                        "type": "string",
                        "description": "A1-style range to write to."
                    },
                    "values": {
                        "type": "array",
                        "description": "2D array of values to write."
                    }
                },
                "required": ["spreadsheet_id", "range", "values"]
            },
        )


class GoogleSheetsCreateSpreadsheetTool(GoogleSheetsActionTool):
    REQUIRED_SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
    ]

    def __init__(self) -> None:
        super().__init__(
            name="google_sheets_create_spreadsheet",
            description="Create a new Google Spreadsheet.",
            action="create",
            schema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title for the new spreadsheet."
                    }
                },
                "required": ["title"]
            },
        )


class GoogleCalendarActionTool(BaseTool):
    """Wrapper for Calendar sub-tools leveraging GoogleCalendarTool implementation."""

    REQUIRED_SCOPES: List[str] = []

    def __init__(
        self,
        *,
        name: str,
        description: str,
        schema: Dict[str, Any],
        action: str,
    ):
        super().__init__(name=name, description=description, schema=schema)
        self._action = action
        self._delegate = GoogleCalendarTool()

    def execute(
        self,
        parameters: Dict[str, Any],
        user_id: str,
        auth_service: AuthService
    ) -> Dict[str, Any]:
        payload = dict(parameters or {})
        payload.setdefault("action", self._action)
        return self._delegate.execute(payload, user_id, auth_service)


class GoogleCalendarListEventsTool(GoogleCalendarActionTool):
    REQUIRED_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    def __init__(self) -> None:
        super().__init__(
            name="google_calendar_list_events",
            description="List upcoming events from a Google Calendar.",
            action="list_events",
            schema={
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID (defaults to 'primary')."
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of events to return."
                    },
                    "time_min": {
                        "type": "string",
                        "description": "RFC3339 start window."
                    },
                    "time_max": {
                        "type": "string",
                        "description": "RFC3339 end window."
                    }
                },
                "required": []
            },
        )


class GoogleCalendarCreateEventTool(GoogleCalendarActionTool):
    REQUIRED_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

    def __init__(self) -> None:
        super().__init__(
            name="google_calendar_create_event",
            description="Create a new Google Calendar event.",
            action="create_event",
            schema={
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID (defaults to 'primary')."
                    },
                    "summary": {
                        "type": "string",
                        "description": "Event title."
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description."
                    },
                    "location": {
                        "type": "string",
                        "description": "Event location."
                    },
                    "start": {
                        "type": "string",
                        "description": "Event start datetime/date."
                    },
                    "end": {
                        "type": "string",
                        "description": "Event end datetime/date."
                    },
                    "time_zone": {
                        "type": "string",
                        "description": "Time zone for start/end."
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of attendee emails."
                    }
                },
                "required": ["start", "end"]
            },
        )


class GoogleCalendarGetEventTool(GoogleCalendarActionTool):
    REQUIRED_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    def __init__(self) -> None:
        super().__init__(
            name="google_calendar_get_event",
            description="Retrieve a Google Calendar event by ID.",
            action="get_event",
            schema={
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID (defaults to 'primary')."
                    },
                    "event_id": {
                        "type": "string",
                        "description": "Identifier of the event to fetch."
                    }
                },
                "required": ["event_id"]
            },
        )


GOOGLE_TOOL_SCOPE_MAP: Dict[str, List[str]] = {
    "gmail": [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.labels",
        "https://mail.google.com/",
    ],
    "gmail_get_message": GmailGetMessageTool.REQUIRED_SCOPES,
    "gmail_read_messages": GmailReadMessagesTool.REQUIRED_SCOPES,
    "gmail_list_messages": GmailListMessagesTool.REQUIRED_SCOPES,
    "gmail_send_message": GmailSendMessageTool.REQUIRED_SCOPES,
    "gmail_create_draft": GmailCreateDraftTool.REQUIRED_SCOPES,
    "gmail_get_thread": GmailGetThreadTool.REQUIRED_SCOPES,
    "google_sheets": [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
    ],
    "google_sheets_get_values": GoogleSheetsReadTool.REQUIRED_SCOPES,
    "google_sheets_update_values": GoogleSheetsWriteTool.REQUIRED_SCOPES,
    "google_sheets_create_spreadsheet": GoogleSheetsCreateSpreadsheetTool.REQUIRED_SCOPES,
    "google_calendar": [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar.readonly",
    ],
    "google_calendar_list_events": GoogleCalendarListEventsTool.REQUIRED_SCOPES,
    "google_calendar_create_event": GoogleCalendarCreateEventTool.REQUIRED_SCOPES,
    "google_calendar_get_event": GoogleCalendarGetEventTool.REQUIRED_SCOPES,
}
