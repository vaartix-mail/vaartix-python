from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from ._errors import VaartixError
from ._types import (
    SendEmailParams,
    SendEmailResponse,
    Webhook,
    WebhookEventType,
    WebhookWithSecret,
)
from ._verify import verify_webhook
from ._version import __version__

DEFAULT_BASE_URL = "https://api.vaartix.com"

# (method, url, headers, body, timeout) -> (status code, response body)
Transport = Callable[[str, str, Dict[str, str], Optional[bytes], float], Tuple[int, bytes]]

# snake_case keys Python developers expect, mapped to the API's names.
_KEY_NAMES = {
    "reply_to": "replyTo",
    "scheduled_at": "scheduledAt",
    "content_type": "contentType",
    "content_id": "contentId",
}


def _api_keys(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {_KEY_NAMES.get(k, k): _api_keys(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_api_keys(v) for v in value]
    return value


def _urllib_transport(
    method: str, url: str, headers: Dict[str, str], body: Optional[bytes], timeout: float
) -> Tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def _trim_trailing_slashes(url: str) -> str:
    end = len(url)
    while end > 0 and url[end - 1] == "/":
        end -= 1
    return url[:end]


class Vaartix:
    """Client for the Vaartix email API.

    >>> vaartix = Vaartix()  # reads VAARTIX_API_KEY
    >>> vaartix.emails.send({"from": "Acme <hi@acme.in>", "to": "priya@example.com",
    ...                      "subject": "Hello", "html": "<p>Hi</p>"})
    {'id': 'em_...'}
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        transport: Optional[Transport] = None,
    ) -> None:
        key = api_key or os.environ.get("VAARTIX_API_KEY")
        if not key:
            raise ValueError(
                'Missing API key. Pass it as Vaartix("vx_...") or set the VAARTIX_API_KEY '
                "environment variable."
            )
        self._key = key
        self._base_url = _trim_trailing_slashes(base_url or DEFAULT_BASE_URL)
        self._timeout = timeout
        self._transport = transport or _urllib_transport
        self.emails = Emails(self)
        self.batch = Batch(self)
        self.webhooks = Webhooks(self)

    def _request(
        self,
        method: str,
        path: str,
        body: Any = None,
        *,
        query: Optional[Mapping[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        url = self._base_url + path
        if query:
            params = {k: v for k, v in query.items() if v is not None}
            if params:
                url += "?" + urllib.parse.urlencode(params)
        headers = {
            "Authorization": f"Bearer {self._key}",
            "User-Agent": f"vaartix-python/{__version__}",
            "Accept": "application/json",
        }
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        try:
            status, raw = self._transport(method, url, headers, data, self._timeout)
        except (TimeoutError, urllib.error.URLError, OSError) as err:
            reason = getattr(err, "reason", err)
            raise VaartixError("network_error", str(reason)) from err

        payload: Any = None
        if raw:
            try:
                payload = json.loads(raw)
            except ValueError:
                payload = None
        if status >= 400:
            error = payload.get("error") if isinstance(payload, dict) else None
            error = error if isinstance(error, dict) else {}
            raise VaartixError(
                str(error.get("type") or "api_error"),
                str(error.get("message") or f"Request failed with status {status}"),
                status,
            )
        return payload


class Emails:
    def __init__(self, client: Vaartix) -> None:
        self._client = client

    def send(
        self, params: SendEmailParams, *, idempotency_key: Optional[str] = None
    ) -> SendEmailResponse:
        """Send an email. Returns ``{"id": "em_..."}`` once it is queued.

        With ``idempotency_key``, retrying within 24 hours returns the first email instead of
        sending again.
        """
        result: SendEmailResponse = self._client._request(
            "POST", "/emails", _api_keys(params), idempotency_key=idempotency_key
        )
        return result

    def get(self, email_id: str) -> Dict[str, Any]:
        """An email with its status and event timeline. Needs a full-access key."""
        result: Dict[str, Any] = self._client._request(
            "GET", f"/emails/{urllib.parse.quote(email_id, safe='')}"
        )
        return result

    def list(
        self,
        *,
        limit: Optional[int] = None,
        before: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        days: Optional[int] = None,
        api_key_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Recent emails, newest first: ``{"data": [...], "hasMore": bool}``.

        Page with ``before=<last email ID>``. Needs a full-access key.
        """
        result: Dict[str, Any] = self._client._request(
            "GET",
            "/emails",
            query={
                "limit": limit,
                "before": before,
                "status": status,
                "search": search,
                "days": days,
                "apiKeyId": api_key_id,
            },
        )
        return result

    def cancel(self, email_id: str) -> Dict[str, Any]:
        """Cancel a scheduled email before it is sent. Needs a full-access key."""
        result: Dict[str, Any] = self._client._request(
            "POST", f"/emails/{urllib.parse.quote(email_id, safe='')}/cancel"
        )
        return result


class Batch:
    def __init__(self, client: Vaartix) -> None:
        self._client = client

    def send(self, emails: Sequence[SendEmailParams]) -> Dict[str, List[SendEmailResponse]]:
        """Send up to 100 emails in one request (no attachments or scheduling). All or nothing."""
        result: Dict[str, List[SendEmailResponse]] = self._client._request(
            "POST", "/emails/batch", [_api_keys(e) for e in emails]
        )
        return result


class Webhooks:
    """Webhook endpoints. Managing them needs a full-access key."""

    def __init__(self, client: Vaartix) -> None:
        self._client = client

    def _path(self, webhook_id: str, suffix: str = "") -> str:
        return f"/webhooks/{urllib.parse.quote(webhook_id, safe='')}{suffix}"

    def create(self, *, url: str, events: Sequence[WebhookEventType]) -> WebhookWithSecret:
        """Create an endpoint. The response includes the signing secret, shown only this once."""
        result: WebhookWithSecret = self._client._request(
            "POST", "/webhooks", {"url": url, "events": list(events)}
        )
        return result

    def list(self) -> Dict[str, List[Webhook]]:
        result: Dict[str, List[Webhook]] = self._client._request("GET", "/webhooks")
        return result

    def get(self, webhook_id: str) -> Webhook:
        result: Webhook = self._client._request("GET", self._path(webhook_id))
        return result

    def update(
        self,
        webhook_id: str,
        *,
        url: Optional[str] = None,
        events: Optional[Sequence[WebhookEventType]] = None,
        status: Optional[str] = None,
    ) -> Webhook:
        """Change the URL or events, or turn the endpoint off (``status="disabled"``) and on."""
        body: Dict[str, Any] = {}
        if url is not None:
            body["url"] = url
        if events is not None:
            body["events"] = list(events)
        if status is not None:
            body["status"] = status
        result: Webhook = self._client._request("PATCH", self._path(webhook_id), body)
        return result

    def remove(self, webhook_id: str) -> None:
        self._client._request("DELETE", self._path(webhook_id))

    def rotate_secret(self, webhook_id: str) -> WebhookWithSecret:
        """Replace the signing secret. The old one stops working immediately."""
        result: WebhookWithSecret = self._client._request(
            "POST", self._path(webhook_id, "/rotate-secret")
        )
        return result

    def deliveries(self, webhook_id: str, *, limit: Optional[int] = None) -> Dict[str, Any]:
        """Recent deliveries to an endpoint, newest first, with your server's responses."""
        result: Dict[str, Any] = self._client._request(
            "GET", self._path(webhook_id, "/deliveries"), query={"limit": limit}
        )
        return result

    def retry_delivery(self, webhook_id: str, delivery_id: str) -> Dict[str, Any]:
        """Send a delivery again, with the same ``webhook-id``."""
        path = self._path(
            webhook_id, f"/deliveries/{urllib.parse.quote(delivery_id, safe='')}/retry"
        )
        result: Dict[str, Any] = self._client._request("POST", path)
        return result

    @staticmethod
    def verify(
        payload: Any, headers: Mapping[str, Any], secret: str, tolerance_seconds: int = 300
    ) -> Dict[str, Any]:
        """Same as the standalone ``verify_webhook``."""
        return verify_webhook(payload, headers, secret, tolerance_seconds)
