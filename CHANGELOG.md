# Changelog

## Unreleased

## 0.2.0

- Django email backend: set `EMAIL_BACKEND = "vaartix.django.EmailBackend"` and Django's
  `send_mail`, `EmailMessage` and built-in emails (password resets and so on) go through Vaartix,
  with HTML alternatives, attachments, inline images, headers and tags.

## 0.1.0

- First release: `emails.send`, `get`, `list`, `cancel`, `batch.send`, webhook endpoints, and
  `verify_webhook` for signed webhooks (Standard Webhooks).
- Idempotency keys, scheduled sending and test mode.
- No dependencies; Python 3.10 or newer; fully typed.
