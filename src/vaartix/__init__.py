"""Official Python SDK for Vaartix, the email API for Indian developers."""

from ._client import Vaartix
from ._errors import VaartixError, WebhookVerificationError
from ._types import (
    BounceEventDetails,
    ClickedEventDetails,
    DelayedEventDetails,
    OpenedEventDetails,
    WebhookEventData,
    WebhookEventType,
    WebhookPayload,
)
from ._verify import verify_webhook
from ._version import __version__

__all__ = [
    "BounceEventDetails",
    "ClickedEventDetails",
    "DelayedEventDetails",
    "OpenedEventDetails",
    "Vaartix",
    "VaartixError",
    "WebhookEventData",
    "WebhookEventType",
    "WebhookPayload",
    "WebhookVerificationError",
    "__version__",
    "verify_webhook",
]
