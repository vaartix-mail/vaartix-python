from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Mapping, Optional, Union

from ._errors import WebhookVerificationError

_PREFIX = "whsec_"


def _header(headers: Mapping[str, Any], name: str) -> Optional[str]:
    # Works with dicts, Django's request.headers, Flask/Werkzeug and Starlette headers.
    getter = getattr(headers, "get", None)
    value = getter(name) if getter else None
    if value is None:
        for key in headers:
            if str(key).lower() == name:
                value = headers[key]
                break
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    return None if value is None else str(value)


def verify_webhook(
    payload: Union[str, bytes],
    headers: Mapping[str, Any],
    secret: str,
    tolerance_seconds: int = 300,
    *,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """Check that a webhook request came from Vaartix and return its parsed JSON body.

    ``payload`` must be the raw request body, exactly as received (for example
    ``request.get_data()`` in Flask or ``request.body`` in Django), not parsed JSON.
    Raises ``WebhookVerificationError`` if the signature or timestamp is wrong.

    Follows the Standard Webhooks spec, so any Standard Webhooks library works too.
    """
    msg_id = _header(headers, "webhook-id")
    timestamp = _header(headers, "webhook-timestamp")
    signatures = _header(headers, "webhook-signature")
    if not msg_id or not timestamp or not signatures:
        raise WebhookVerificationError(
            "Missing webhook-id, webhook-timestamp or webhook-signature header."
        )

    try:
        sent_at = int(timestamp)
    except ValueError:
        raise WebhookVerificationError("The webhook timestamp is not a number.") from None
    current = time.time() if now is None else now
    if abs(current - sent_at) > tolerance_seconds:
        raise WebhookVerificationError("The webhook timestamp is too old or in the future.")

    if not secret.startswith(_PREFIX):
        raise WebhookVerificationError(f"The secret should start with {_PREFIX}.")
    try:
        key = base64.b64decode(secret[len(_PREFIX) :], validate=True)
    except (binascii.Error, ValueError):
        raise WebhookVerificationError("The secret is not valid base64.") from None

    body = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    signed = f"{msg_id}.{timestamp}.{body}".encode()
    expected = hmac.new(key, signed, hashlib.sha256).digest()

    # The header can hold several space-separated signatures, e.g. while a secret is rotated.
    for entry in signatures.split(" "):
        version, _, signature = entry.partition(",")
        if version != "v1" or not signature:
            continue
        try:
            given = base64.b64decode(signature)
        except (binascii.Error, ValueError):
            continue
        if hmac.compare_digest(given, expected):
            parsed: Dict[str, Any] = json.loads(body)
            return parsed
    raise WebhookVerificationError("The webhook signature does not match.")
