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
# Open/click tracking for one email: {"tracking": {"opens": True, "clicks": False}}. Each field
# overrides the sending domain's default; leave a field (or "tracking") out to use the domain's.
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
    "email.opened",
    "email.clicked",
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


class OpenedEventDetails(TypedDict):
    """``details`` of an ``email.opened`` event."""

    machine: bool
    """True when the open was most likely not a person (an image proxy or Apple Mail Privacy
    Protection)."""
    machineReason: Optional[Literal["image_proxy", "apple_mpp", "too_fast"]]
    userAgentFamily: str
    """For example ``Chrome``, ``Apple Mail`` or ``Gmail image proxy``. More may be added."""
    country: Optional[str]
    """Two-letter country code, when known."""
    asn: Optional[int]
    """Network (autonomous system) number, when known."""


class ClickedEventDetails(TypedDict):
    """``details`` of an ``email.clicked`` event."""

    machine: bool
    """True when the click was most likely not a person, such as a link scanner."""
    machineReason: Optional[Literal["scanner", "scanner_network", "too_fast", "burst"]]
    linkIndex: int
    """Position of the link in the email's HTML, starting at 0."""
    link: str
    """The original link URL."""
    userAgentFamily: str
    country: Optional[str]
    asn: Optional[int]


# "from" is a Python keyword, so this TypedDict uses the functional form.
WebhookEventData = TypedDict(
    "WebhookEventData",
    {
        "emailId": str,
        "eventId": str,
        "recipient": Optional[str],  # None when the email had more than one recipient
        "from": str,
        "to": List[str],
        "cc": List[str],
        "bcc": List[str],
        "subject": str,
        "tags": List[Tag],
        "emailCreatedAt": str,
        # OpenedEventDetails or ClickedEventDetails for those events; other events vary.
        "details": Dict[str, Any],
    },
)


class WebhookPayload(TypedDict):
    """The JSON body Vaartix posts to your endpoint, as returned by ``verify_webhook``."""

    type: WebhookEventType
    createdAt: str
    """When the event happened. Deliveries can arrive out of order; sort by this."""
    data: WebhookEventData
