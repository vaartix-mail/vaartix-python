# vaartix

Official Python SDK for [Vaartix](https://vaartix.com), the email API for Indian developers.

> Vaartix is in private beta. [Request early access](https://vaartix.com/#early-access).

```sh
pip install vaartix
```

Python 3.10 or newer. No dependencies.

## Send an email

```python
from vaartix import Vaartix

vaartix = Vaartix()  # reads the VAARTIX_API_KEY environment variable

email = vaartix.emails.send(
    {
        "from": "Acme <onboarding@acme.in>",
        "to": ["priya@example.com"],
        "subject": "Hello from Vaartix",
        "html": "<strong>It works!</strong>",
    }
)
print(email["id"])  # em_...
```

Emails are plain dicts because `from` is a Python keyword. Keys can be `snake_case`
(`reply_to`, `scheduled_at`) or the API's camelCase (`replyTo`, `scheduledAt`). Responses are the
API's JSON as dicts, exactly as in the [API reference](https://vaartix.com/docs/).

```python
# Retry safely: the same key within 24 hours returns the first email instead of sending twice.
vaartix.emails.send(email, idempotency_key=f"welcome-{user.id}")

# Send later (up to 30 days ahead), and cancel if plans change.
scheduled = vaartix.emails.send({**email, "scheduled_at": "2026-11-01T09:00:00+05:30"})
vaartix.emails.cancel(scheduled["id"])

# Up to 100 emails in one request.
vaartix.batch.send([email_1, email_2])

# Look up an email and its delivery events, or list recent bounces.
vaartix.emails.get("em_...")
vaartix.emails.list(status="bounced", days=7)

# Try it without a domain: test addresses simulate delivery, bounces and complaints.
vaartix.emails.send(
    {
        "from": "onboarding@test.vaartix.com",
        "to": "delivered@test.vaartix.com",
        "subject": "Hello",
        "text": "It works!",
    }
)
```

## Django

Send all of Django's email through Vaartix, including `send_mail`, `EmailMessage` and built-in
emails such as password resets:

```sh
pip install "vaartix[django]"
```

```python
# settings.py
VAARTIX_API_KEY = os.environ["VAARTIX_API_KEY"]
DEFAULT_FROM_EMAIL = "Acme <noreply@acme.in>"  # on a domain verified in Vaartix

# Django 6.1 and newer
MAILERS = {"default": {"BACKEND": "vaartix.django.EmailBackend"}}
# Django 4.2 to 6.0
EMAIL_BACKEND = "vaartix.django.EmailBackend"
```

With `MAILERS` you can also pass the key as an option instead:
`{"BACKEND": "vaartix.django.EmailBackend", "OPTIONS": {"api_key": "vx_live_..."}}`.

```python
from django.core.mail import EmailMultiAlternatives

message = EmailMultiAlternatives("Order confirmed", "Thanks!", to=["priya@example.com"])
message.attach_alternative("<p>Thanks!</p>", "text/html")
message.tags = [{"name": "type", "value": "order"}]  # optional
message.send()
print(message.vaartix_id)  # em_...
```

HTML alternatives, attachments, inline images (`Content-ID`), cc, bcc, reply-to and custom
headers are all supported. Errors raise `VaartixError` unless you pass `fail_silently=True`.

## Errors

API and network errors raise `VaartixError`:

```python
from vaartix import VaartixError

try:
    vaartix.emails.send(email)
except VaartixError as err:
    print(err.type, err.status_code, err.message)  # e.g. rate_limited 429 Too many requests...
```

`err.type` is a stable code; the full list is in [Errors](https://vaartix.com/docs/concepts/errors/).
Network failures have `type == "network_error"` and `status_code is None`.

## Webhooks

Check that a webhook request really came from Vaartix before trusting it. Pass the **raw** body.

```python
import os

from flask import Flask, request
from vaartix import verify_webhook, WebhookVerificationError

app = Flask(__name__)


@app.post("/webhooks/vaartix")
def vaartix_webhook():
    try:
        event = verify_webhook(
            request.get_data(),  # raw bytes, not request.json
            request.headers,
            os.environ["VAARTIX_WEBHOOK_SECRET"],
        )
    except WebhookVerificationError:
        return "", 400
    if event["type"] == "email.bounced":
        ...  # stop emailing event["data"]["recipient"]
    return "", 200
```

In Django use `request.body` and `request.headers`. Signatures follow the
[Standard Webhooks](https://www.standardwebhooks.com) spec.

Manage endpoints with `vaartix.webhooks.create(url=..., events=[...])`, `list()`, `get()`,
`update()`, `remove()`, `rotate_secret()`, `deliveries()` and `retry_delivery()`.

## Docs

Full API reference and guides: [vaartix.com/docs](https://vaartix.com/docs/).

## Contributing and security

Issues and pull requests are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). Please report
security problems privately as described in [SECURITY.md](SECURITY.md).

## License

MIT
