from __future__ import annotations

from typing import Optional


class VaartixError(Exception):
    """Raised when the API returns an error or cannot be reached.

    ``type`` is a stable code such as ``validation_error`` or ``rate_limited`` (see
    https://vaartix.com/docs/concepts/errors/). ``status_code`` is ``None`` for network errors.
    """

    def __init__(self, type: str, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.type = type
        self.message = message
        self.status_code = status_code

    def __repr__(self) -> str:
        return (
            f"VaartixError(type={self.type!r}, message={self.message!r}, "
            f"status_code={self.status_code!r})"
        )


class WebhookVerificationError(Exception):
    """Raised by ``verify_webhook`` when a request's signature or timestamp is not valid."""
