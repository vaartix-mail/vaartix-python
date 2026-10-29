"""Official Python SDK for Vaartix, the email API for Indian developers."""

from ._client import Vaartix
from ._errors import VaartixError, WebhookVerificationError
from ._verify import verify_webhook
from ._version import __version__

__all__ = [
    "Vaartix",
    "VaartixError",
    "WebhookVerificationError",
    "__version__",
    "verify_webhook",
]
