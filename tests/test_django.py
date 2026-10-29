import base64
from email.mime.image import MIMEImage

import pytest

django = pytest.importorskip("django")
from django.conf import settings  # noqa: E402

if not settings.configured:
    settings.configure(
        EMAIL_BACKEND="vaartix.django.EmailBackend",
        VAARTIX_API_KEY="vx_test",
        DEFAULT_FROM_EMAIL="Acme <noreply@acme.in>",
    )
    django.setup()

from django.core import mail  # noqa: E402
from django.core.mail import EmailMessage, EmailMultiAlternatives  # noqa: E402
from test_client import FakeTransport  # noqa: E402

from vaartix import VaartixError  # noqa: E402
from vaartix.django import EmailBackend  # noqa: E402


@pytest.fixture
def transport(monkeypatch):
    t = FakeTransport(body={"id": "em_django"})
    monkeypatch.setattr("vaartix._client._urllib_transport", t)
    return t


def test_send_mail_uses_vaartix(transport):
    sent = mail.send_mail("Welcome", "Hello Priya", None, ["priya@example.com"])
    assert sent == 1
    call = transport.calls[0]
    assert call["headers"]["Authorization"] == "Bearer vx_test"
    assert call["json"] == {
        "from": "Acme <noreply@acme.in>",
        "to": ["priya@example.com"],
        "subject": "Welcome",
        "text": "Hello Priya",
    }


def test_html_alternative_cc_bcc_reply_to_headers_and_tags(transport):
    message = EmailMultiAlternatives(
        "Order confirmed",
        "Thanks for your order",
        "orders@acme.in",
        ["priya@example.com"],
        cc=["ravi@example.com"],
        bcc=["audit@acme.in"],
        reply_to=["support@acme.in"],
        headers={"X-Order": "1042", "Subject": "ignored"},
    )
    message.attach_alternative("<p>Thanks for your order</p>", "text/html")
    message.tags = [{"name": "type", "value": "order"}]
    assert message.send() == 1
    sent = transport.calls[0]["json"]
    assert sent["text"] == "Thanks for your order"
    assert sent["html"] == "<p>Thanks for your order</p>"
    assert sent["cc"] == ["ravi@example.com"]
    assert sent["bcc"] == ["audit@acme.in"]
    assert sent["replyTo"] == ["support@acme.in"]
    assert sent["headers"] == {"X-Order": "1042"}
    assert sent["tags"] == [{"name": "type", "value": "order"}]
    assert message.vaartix_id == "em_django"


def test_html_only_body(transport):
    message = EmailMessage("Hi", "<b>Hi</b>", "a@acme.in", ["b@example.com"])
    message.content_subtype = "html"
    message.send()
    sent = transport.calls[0]["json"]
    assert sent["html"] == "<b>Hi</b>"
    assert "text" not in sent


def test_attachments(transport):
    message = EmailMessage("Invoice", "Attached", "a@acme.in", ["b@example.com"])
    message.attach("invoice.txt", "total: 100", "text/plain")
    image = MIMEImage(b"\x89PNG fake", "png")
    image.add_header("Content-ID", "<logo>")
    image.add_header("Content-Disposition", "inline", filename="logo.png")
    message.attach(image)
    message.send()
    first, second = transport.calls[0]["json"]["attachments"]
    assert first == {
        "filename": "invoice.txt",
        "content": base64.b64encode(b"total: 100").decode(),
        "contentType": "text/plain",
    }
    assert second["filename"] == "logo.png"
    assert second["contentId"] == "logo"
    assert base64.b64decode(second["content"]) == b"\x89PNG fake"


def test_errors_raise_unless_fail_silently(monkeypatch):
    t = FakeTransport(
        422, {"error": {"type": "domain_not_verified", "message": "Verify acme.in first"}}
    )
    monkeypatch.setattr("vaartix._client._urllib_transport", t)
    with pytest.raises(VaartixError):
        mail.send_mail("Hi", "x", None, ["b@example.com"])
    assert mail.send_mail("Hi", "x", None, ["b@example.com"], fail_silently=True) == 0


def test_mailers_style_construction_takes_options(transport):
    # Django 6.1 creates backends as Backend(alias=..., **OPTIONS).
    backend = EmailBackend(alias="default", api_key="vx_from_options")
    backend.send_messages([EmailMessage("Hi", "x", "a@acme.in", ["b@example.com"])])
    assert transport.calls[0]["headers"]["Authorization"] == "Bearer vx_from_options"


def test_skips_messages_without_recipients(transport):
    assert EmailBackend().send_messages([EmailMessage("Hi", "x", "a@acme.in", [])]) == 0
    assert transport.calls == []
