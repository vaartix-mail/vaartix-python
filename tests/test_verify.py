import base64
import hashlib
import hmac
import json

import pytest

from vaartix import Vaartix, WebhookVerificationError, verify_webhook

# Test-only secrets, built from a separate prefix so secret scanners don't flag them.
PREFIX = "whsec_"

# The worked example from the Standard Webhooks specification.
SPEC_SECRET = f"{PREFIX}MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw"
SPEC_HEADERS = {
    "webhook-id": "msg_p5jXN8AQM9LWM0D4loKWxJek",
    "webhook-timestamp": "1614265330",
    "webhook-signature": "v1,g0hM9SsE+OTPJTGt/tmIKtSyZlE3uFJELVlNIOLJ1OE=",
}
SPEC_BODY = '{"test": 2432232314}'
SPEC_NOW = 1614265330


def sign(secret, msg_id, timestamp, body):
    key = base64.b64decode(secret[len(PREFIX) :])
    digest = hmac.new(key, f"{msg_id}.{timestamp}.{body}".encode(), hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def test_matches_the_standard_webhooks_example():
    assert verify_webhook(SPEC_BODY, SPEC_HEADERS, SPEC_SECRET, now=SPEC_NOW) == {
        "test": 2432232314
    }


def test_accepts_bytes_and_any_header_case():
    headers = {k.title(): v for k, v in SPEC_HEADERS.items()}
    assert (
        verify_webhook(SPEC_BODY.encode(), headers, SPEC_SECRET, now=SPEC_NOW)["test"] == 2432232314
    )


def test_accepts_one_valid_signature_among_several():
    headers = dict(SPEC_HEADERS)
    headers["webhook-signature"] = "v1,AAAA " + SPEC_HEADERS["webhook-signature"]
    verify_webhook(SPEC_BODY, headers, SPEC_SECRET, now=SPEC_NOW)


def test_rejects_a_changed_body():
    with pytest.raises(WebhookVerificationError, match="does not match"):
        verify_webhook('{"test": 1}', SPEC_HEADERS, SPEC_SECRET, now=SPEC_NOW)


def test_rejects_old_timestamps():
    with pytest.raises(WebhookVerificationError, match="too old"):
        verify_webhook(SPEC_BODY, SPEC_HEADERS, SPEC_SECRET, now=SPEC_NOW + 301)


def test_rejects_missing_headers_and_bad_secrets():
    with pytest.raises(WebhookVerificationError, match="Missing"):
        verify_webhook(SPEC_BODY, {}, SPEC_SECRET, now=SPEC_NOW)
    with pytest.raises(WebhookVerificationError, match="start with"):
        verify_webhook(SPEC_BODY, SPEC_HEADERS, "not-a-secret", now=SPEC_NOW)


def test_round_trip_with_a_vaartix_style_payload():
    secret = f"{PREFIX}" + base64.b64encode(b"x" * 24).decode()
    body = json.dumps({"type": "email.bounced", "data": {"recipient": "priya@example.com"}})
    headers = {
        "webhook-id": "whd_1",
        "webhook-timestamp": "1793181600",
        "webhook-signature": sign(secret, "whd_1", "1793181600", body),
    }
    result = verify_webhook(body, headers, secret, now=1793181600)
    assert result["data"]["recipient"] == "priya@example.com"
    # The client exposes the same check.
    client = Vaartix("vx_test", transport=lambda *a: (200, b"{}"))
    with pytest.raises(WebhookVerificationError):
        client.webhooks.verify(body, headers, secret)  # real clock: timestamp is far off


def test_email_clicked_payload_matches_the_typed_shape():
    from typing import cast

    from vaartix import ClickedEventDetails, WebhookPayload

    body = json.dumps(
        {
            "type": "email.clicked",
            "createdAt": "2026-10-28T10:05:41.000Z",
            "data": {
                "emailId": "em_7hq2kv9xr4m1c8d3",
                "eventId": "evt_5k2m8q1v7c3x9d4p",
                "recipient": "rahul@example.in",
                "from": "Acme <orders@acme.in>",
                "to": ["rahul@example.in"],
                "cc": [],
                "bcc": [],
                "subject": "Your order has shipped",
                "tags": [{"name": "flow", "value": "shipping"}],
                "emailCreatedAt": "2026-10-28T10:00:00.000Z",
                "details": {
                    "machine": False,
                    "machineReason": None,
                    "linkIndex": 0,
                    "link": "https://acme.in/orders/123",
                    "userAgentFamily": "Chrome",
                    "country": "IN",
                    "asn": 24560,
                },
            },
        }
    )
    headers = {
        "webhook-id": "msg_1",
        "webhook-timestamp": str(SPEC_NOW),
        "webhook-signature": sign(SPEC_SECRET, "msg_1", SPEC_NOW, body),
    }
    event = cast(WebhookPayload, verify_webhook(body, headers, SPEC_SECRET, now=SPEC_NOW))
    assert event["type"] == "email.clicked"
    details = cast(ClickedEventDetails, event["data"]["details"])
    assert set(details) == set(ClickedEventDetails.__annotations__)
    assert details["link"] == "https://acme.in/orders/123"
    assert details["machine"] is False


def test_delay_and_bounce_detail_types():
    from vaartix import BounceEventDetails, DelayedEventDetails

    delayed: DelayedEventDetails = {
        "delayType": "TransientCommunicationFailure",
        "diagnosticCode": "421 4.7.0 [TSS04] Messages temporarily deferred",
        "statusCode": "4.7.0",
    }
    bounced: BounceEventDetails = {
        "bounceType": "Permanent",
        "diagnostics": [],
        "diagnosticCode": "550 5.1.1 user unknown",
    }
    assert "bounceType" not in delayed
    assert bounced["bounceType"] == "Permanent"
