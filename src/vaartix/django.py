"""Django email backend: Django's emails (send_mail, password resets...) go through Vaartix.

    # settings.py (Django 6.1+)
    MAILERS = {"default": {"BACKEND": "vaartix.django.EmailBackend"}}
    # settings.py (Django 4.2 to 6.0)
    EMAIL_BACKEND = "vaartix.django.EmailBackend"

    VAARTIX_API_KEY = os.environ["VAARTIX_API_KEY"]  # or just set that environment variable

Needs Django 4.2 or newer: ``pip install "vaartix[django]"``.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from email.message import Message
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail.backends.base import BaseEmailBackend

from ._client import Vaartix
from ._errors import VaartixError

# Headers Vaartix sets from the message itself; passing them again would conflict.
_RESERVED_HEADERS = {
    "from",
    "to",
    "cc",
    "bcc",
    "reply-to",
    "subject",
    "content-type",
    "mime-version",
}


class EmailBackend(BaseEmailBackend):
    """Sends each Django email with the Vaartix API.

    After sending, each message has a ``vaartix_id`` attribute with its Vaartix email ID.
    Set ``message.tags = [{"name": "type", "value": "password_reset"}]`` to tag an email.
    """

    def __init__(
        self,
        fail_silently: bool = False,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        # Django passes `alias` (and MAILERS OPTIONS such as api_key) as keyword arguments.
        super().__init__(**kwargs)
        self.fail_silently = fail_silently
        self.client = Vaartix(
            api_key or getattr(settings, "VAARTIX_API_KEY", None),
            base_url=base_url or getattr(settings, "VAARTIX_BASE_URL", None),
        )

    def send_messages(self, email_messages: Sequence[EmailMessage]) -> int:
        sent = 0
        for message in email_messages:
            if not message.recipients():
                continue
            try:
                result = self.client.emails.send(_to_params(message))
            except VaartixError:
                if not self.fail_silently:
                    raise
                continue
            message.vaartix_id = result["id"]  # type: ignore[attr-defined]
            sent += 1
        return sent


def _to_params(message: EmailMessage) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
        "to": list(message.to),
        "subject": message.subject,
    }
    if message.cc:
        params["cc"] = list(message.cc)
    if message.bcc:
        params["bcc"] = list(message.bcc)
    if message.reply_to:
        params["reply_to"] = list(message.reply_to)

    body = message.body or ""
    if message.content_subtype == "html":
        params["html"] = body
    elif body:
        params["text"] = body
    for alternative in getattr(message, "alternatives", None) or []:
        content, mimetype = alternative[0], alternative[1]
        if mimetype == "text/html" and "html" not in params:
            params["html"] = content if isinstance(content, str) else content.decode()

    headers = {
        str(k): str(v)
        for k, v in (message.extra_headers or {}).items()
        if str(k).lower() not in _RESERVED_HEADERS
    }
    if headers:
        params["headers"] = headers

    attachments = [_attachment(a) for a in message.attachments]
    if attachments:
        params["attachments"] = attachments

    tags = getattr(message, "tags", None)
    if tags:
        params["tags"] = list(tags)
    return params


def _attachment(attachment: Any) -> Dict[str, Any]:
    if isinstance(attachment, Message):  # MIMEBase, or MIMEPart on Django 6.1+
        filename = attachment.get_filename() or "attachment"
        content = attachment.get_payload(decode=True) or b""
        mimetype = attachment.get_content_type()
        content_id = attachment.get("Content-ID")
    else:
        # A (filename, content, mimetype) tuple, or Django 5.2's EmailAttachment.
        filename, content, mimetype = attachment[0], attachment[1], attachment[2]
        content_id = None
    if isinstance(content, str):
        content = content.encode()
    if isinstance(content, EmailMessage):  # an attached email (message/rfc822)
        content = content.message().as_bytes()
    out: Dict[str, Any] = {
        "filename": filename or "attachment",
        "content": base64.b64encode(bytes(content)).decode("ascii"),
    }
    if mimetype:
        out["content_type"] = mimetype
    if content_id:
        out["content_id"] = str(content_id).strip("<>")
    return out


__all__: List[str] = ["EmailBackend"]
