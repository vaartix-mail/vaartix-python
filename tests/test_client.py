import json
import urllib.error

import pytest

from vaartix import Vaartix, VaartixError, __version__


class FakeTransport:
    def __init__(self, status=200, body=None):
        self.status = status
        self.body = body if body is not None else {"id": "em_1"}
        self.calls = []

    def __call__(self, method, url, headers, data, timeout):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "json": json.loads(data) if data else None,
                "timeout": timeout,
            }
        )
        raw = self.body if isinstance(self.body, bytes) else json.dumps(self.body).encode()
        return self.status, raw


def client(transport, **kwargs):
    return Vaartix("vx_test", transport=transport, **kwargs)


def test_sends_with_auth_json_and_idempotency_key():
    t = FakeTransport()
    result = client(t, base_url="https://api.example.test/").emails.send(
        {"from": "a@acme.in", "to": "b@example.com", "subject": "Hi", "html": "<p>Hi</p>"},
        idempotency_key="order-42",
    )
    assert result == {"id": "em_1"}
    call = t.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "https://api.example.test/emails"
    assert call["headers"]["Authorization"] == "Bearer vx_test"
    assert call["headers"]["Idempotency-Key"] == "order-42"
    assert call["headers"]["User-Agent"] == f"vaartix-python/{__version__}"
    assert call["json"]["subject"] == "Hi"


def test_snake_case_keys_become_api_names():
    t = FakeTransport()
    client(t).emails.send(
        {
            "from": "a@acme.in",
            "to": ["b@example.com"],
            "subject": "Invoice",
            "text": "Attached",
            "reply_to": "billing@acme.in",
            "scheduled_at": "2026-11-01T09:00:00+05:30",
            "attachments": [
                {"filename": "a.pdf", "content": "QQ==", "content_type": "application/pdf"}
            ],
        }
    )
    sent = t.calls[0]["json"]
    assert sent["replyTo"] == "billing@acme.in"
    assert sent["scheduledAt"] == "2026-11-01T09:00:00+05:30"
    assert sent["attachments"][0]["contentType"] == "application/pdf"
    assert "reply_to" not in sent


def test_api_errors_raise_vaartix_error():
    t = FakeTransport(422, {"error": {"type": "validation_error", "message": "from is required"}})
    with pytest.raises(VaartixError) as info:
        client(t).emails.send({"to": "b@example.com", "subject": "Hi"})
    assert info.value.type == "validation_error"
    assert info.value.message == "from is required"
    assert info.value.status_code == 422


def test_non_json_errors_still_raise():
    t = FakeTransport(502, b"<html>Bad gateway</html>")
    with pytest.raises(VaartixError) as info:
        client(t).emails.get("em_1")
    assert info.value.type == "api_error"
    assert info.value.status_code == 502


def test_network_errors_raise_with_no_status():
    def broken(*args):
        raise urllib.error.URLError("connection refused")

    with pytest.raises(VaartixError) as info:
        client(broken).emails.get("em_1")
    assert info.value.type == "network_error"
    assert info.value.status_code is None


def test_list_builds_query_and_skips_empty_filters():
    t = FakeTransport(body={"data": [], "hasMore": False})
    client(t).emails.list(limit=5, status="bounced", api_key_id="key_1")
    assert (
        t.calls[0]["url"] == "https://api.vaartix.com/emails?limit=5&status=bounced&apiKeyId=key_1"
    )


def test_ids_are_escaped_in_paths():
    t = FakeTransport(body={"id": "em_1", "status": "canceled"})
    client(t).emails.cancel("em_1/../x")
    assert t.calls[0]["url"] == "https://api.vaartix.com/emails/em_1%2F..%2Fx/cancel"


def test_batch_sends_a_list():
    t = FakeTransport(body={"data": [{"id": "em_1"}, {"id": "em_2"}]})
    result = client(t).batch.send(
        [
            {"from": "a@acme.in", "to": "b@example.com", "subject": "1", "text": "x"},
            {
                "from": "a@acme.in",
                "to": "c@example.com",
                "subject": "2",
                "text": "y",
                "reply_to": "r@acme.in",
            },
        ]
    )
    assert [e["id"] for e in result["data"]] == ["em_1", "em_2"]
    assert t.calls[0]["url"].endswith("/emails/batch")
    assert t.calls[0]["json"][1]["replyTo"] == "r@acme.in"


def test_webhook_management():
    t = FakeTransport(body={"id": "wh_1", "status": "disabled"})
    hooks = client(t).webhooks
    hooks.create(url="https://acme.in/hooks", events=["email.bounced"])
    hooks.update("wh_1", status="disabled")
    hooks.deliveries("wh_1", limit=10)
    hooks.retry_delivery("wh_1", "whd_1")
    assert [(c["method"], c["url"].replace("https://api.vaartix.com", "")) for c in t.calls] == [
        ("POST", "/webhooks"),
        ("PATCH", "/webhooks/wh_1"),
        ("GET", "/webhooks/wh_1/deliveries?limit=10"),
        ("POST", "/webhooks/wh_1/deliveries/whd_1/retry"),
    ]
    assert t.calls[0]["json"] == {"url": "https://acme.in/hooks", "events": ["email.bounced"]}
    assert t.calls[1]["json"] == {"status": "disabled"}


def test_api_key_from_environment(monkeypatch):
    monkeypatch.setenv("VAARTIX_API_KEY", "vx_env")
    t = FakeTransport()
    Vaartix(transport=t).emails.get("em_1")
    assert t.calls[0]["headers"]["Authorization"] == "Bearer vx_env"


def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("VAARTIX_API_KEY", raising=False)
    with pytest.raises(ValueError, match="VAARTIX_API_KEY"):
        Vaartix()


def test_many_trailing_slashes_in_base_url():
    t = FakeTransport()
    client(t, base_url="https://api.example.test" + "/" * 50_000).emails.get("em_1")
    assert t.calls[0]["url"] == "https://api.example.test/emails/em_1"
