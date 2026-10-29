# Contributing

Thanks for helping improve the Vaartix Python SDK.

```sh
python -m venv .venv && . .venv/bin/activate
pip install -e . pytest ruff mypy
pytest            # tests
ruff check .      # lint
ruff format .     # formatting
mypy              # types
```

- Open an issue first for anything larger than a small fix, so we can agree on the approach.
- Keep the SDK free of runtime dependencies; it uses only the standard library.
- Add a line to `CHANGELOG.md` under "Unreleased".
