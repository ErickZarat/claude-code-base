---
paths:
  - "**/*.py"
---

# Python

- Type hints on all public functions; keep `mypy`/`pyright` clean if configured.
- Use `Protocol` or `abc.ABC` for ports/interfaces; inject implementations.
- Dataclasses / Pydantic models for structured data; validate external input with Pydantic or the project's validator.
- No bare `except:`; catch specific exceptions. Use context managers for resources.
- Never `eval`/`exec`/`pickle.loads` untrusted data; `subprocess` with argument lists and `shell=False`.
- `logging` module, not `print`. Follow the project's ruff/black config.
- Tests with pytest; fixtures for setup; no network in unit tests.
