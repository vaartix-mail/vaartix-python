# Changelog

## Unreleased

- `DelayedEventDetails` and `BounceEventDetails` TypedDicts for the `details` of
  `email.delivery_delayed` and `email.bounced`, including `diagnosticCode`: the receiving
  server's exact reply, such as Yahoo's `421 4.7.0 [TSS04]` line.

## 0.3.0

- Open and click tracking: `"tracking": {"opens": ..., "clicks": ...}` on `emails.send()` and on
  each email in `batch.send()`, overriding the sending domain's defaults.
- Django: `message.tracking = {"opens": True}` sets tracking for one email.
- `domains.update(domain_id, open_tracking=..., click_tracking=...)` changes a domain's tracking
  defaults.
- `email.opened` and `email.clicked` webhook events, with `TypedDict`s for type checkers:
  `WebhookPayload`, `WebhookEventData`, `OpenedEventDetails` and `ClickedEventDetails`, exported
  from `vaartix`. `verify_webhook` still returns a plain `dict`.

## 0.2.0

- Django email backend: set `EMAIL_BACKEND = "vaartix.django.EmailBackend"` and Django's
  `send_mail`, `EmailMessage` and built-in emails (password resets and so on) go through Vaartix,
  with HTML alternatives, attachments, inline images, headers and tags.

## 0.1.0

- First release: `emails.send`, `get`, `list`, `cancel`, `batch.send`, webhook endpoints, and
  `verify_webhook` for signed webhooks (Standard Webhooks).
- Idempotency keys, scheduled sending and test mode.
- No dependencies; Python 3.10 or newer; fully typed.
