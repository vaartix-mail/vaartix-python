"""Shapes of the data the API accepts and returns. Responses are the API's JSON, unchanged."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

Addresses = Union[str, List[str]]


class Tag(TypedDict):
    name: str
    value: str


class _AttachmentRequired(TypedDict):
    filename: str
    content: str
    """Base64-encoded file content."""


class Attachment(_AttachmentRequired, total=False):
    content_type: str
    content_id: str
    """For inline images: reference it in your HTML as ``cid:<content_id>``."""


# "from" is a Python keyword, so emails are passed as plain dicts:
#   {"from": "...", "to": "...", "subject": "...", "html": "..."}
# Keys can be snake_case (reply_to, scheduled_at) or the API's camelCase (replyTo, scheduledAt).
SendEmailParams = Dict[str, Any]

EmailStatus = Literal[
    "queued",
    "scheduled",
    "sending",
    "sent",
    "delivered",
    "delivery_delayed",
    "bounced",
    "complained",
    "suppressed",
    "failed",
    "canceled",
]

WebhookEventType = Literal[
    "email.sent",
    "email.delivered",
    "email.delivery_delayed",
    "email.bounced",
    "email.complained",
    "email.rejected",
    "email.rendering_failure",
    "email.suppressed",
]


class SendEmailResponse(TypedDict):
    id: str


class EmailSummary(TypedDict):
    id: str
    status: EmailStatus
    subject: str
    to: List[str]
    createdAt: str
    sentAt: Optional[str]
    scheduledAt: Optional[str]
    error: Optional[str]


class Webhook(TypedDict):
    id: str
    url: str
    events: List[WebhookEventType]
    status: Literal["enabled", "disabled"]
    createdAt: str


class WebhookWithSecret(Webhook):
    secret: str
    """The signing secret (``whsec_...``). Only returned when created or rotated."""
