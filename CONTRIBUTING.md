# Contributing to kwtSMS Python

Thank you for contributing. Please read this guide before opening a pull request.

---

## Code of Conduct

Be respectful and constructive. Treat all contributors as professionals.

---

## Getting Started

### 1. Clone and set up

```bash
git clone https://github.com/boxlinknet/kwtsms_python.git
cd kwtsms_python
```

### 2. Install dependencies

```bash
# With uv (recommended)
uv sync

# With pip
pip install -e ".[dev]"
```

Requires Python 3.8+.

### 3. Configure credentials for integration tests

```bash
cp examples/.env.example .env
# Edit .env and set KWTSMS_USERNAME and KWTSMS_PASSWORD
```

Integration tests are skipped automatically if no credentials are found.

---

## Running Tests

| Command | What it runs |
|---------|-------------|
| `uv run pytest` | All tests except integration |
| `uv run pytest tests/test_integration.py -v` | Live API tests (requires `.env`) |
| `uv run pytest tests/ -v` | All tests |
| `uv run pytest tests/test_phone.py -v` | Phone normalization only |

All tests use `test_mode=True`. No real SMS messages are sent and no credits
are consumed.

### Test structure

```
tests/
  test_phone.py        # normalize_phone(), validate_phone_input()
  test_message.py      # clean_message(), emoji ranges, edge cases
  test_api_errors.py   # _enrich_error(), verify(), send() error paths
  test_bulk.py         # _send_bulk() routing, batching, ERR013 retry
  test_env.py          # _load_env_file(), from_env(), .env edge cases
  test_integration.py  # live API tests (skipped without credentials)
```

---

## Reporting Bugs

Open an issue at https://github.com/boxlinknet/kwtsms_python/issues with:

1. Python version and OS
2. Package version (`pip show kwtsms`)
3. Minimal code that reproduces the issue
4. Actual vs expected behavior
5. JSONL log output if available (remove your password first)

For suspected API bugs, include the relevant kwtSMS error code (ERR001–ERR033).

---

## Feature Suggestions

Open an issue before writing code for new features. Describe:

1. The use case (what problem does it solve?)
2. What the API would look like (function signature, return value)
3. Whether it requires a new API endpoint

Features that add external dependencies will not be accepted. The package
is and will remain zero-dependency.

---

## Development Setup

### Project structure

```
src/kwtsms/
  __init__.py     # Public API: KwtSMS, clean_message, normalize_phone, validate_phone_input
  _core.py        # All client logic
  _cli.py         # CLI entry points (kwtsms verify/send/balance/setup)

tests/            # pytest test suite
examples/         # Runnable example scripts
  docs/           # Markdown documentation for each example
```

### Coding standards

- Target Python 3.8+. Do not use syntax or stdlib features introduced after 3.8
- No external dependencies. Standard library only
- All public functions must have type hints and docstrings
- `send()` never raises. Errors are returned as dicts
- All error responses must include an `action` field (use `_enrich_error()`)
- Phone numbers are always normalized before any API call
- Messages are always cleaned before any API call
- Log entries always use UTC ISO-8601 timestamps
- Never log passwords in plaintext (the log sanitizes them to `***`)

### Style

- Follow existing naming conventions: `snake_case` for functions and variables
- Private helpers are prefixed with `_` (e.g., `_request`, `_enrich_error`)
- Module-level constants are `ALL_CAPS` (e.g., `BASE_URL`, `_API_ERRORS`)

---

## Writing Tests

All new features require tests. Follow these patterns:

### Unit test (no network)

```python
from unittest.mock import patch
from kwtsms import KwtSMS

def _client(**kwargs) -> KwtSMS:
    defaults = dict(username="python_username", password="python_password",
                    sender_id="TEST", log_file="")
    defaults.update(kwargs)
    return KwtSMS(**defaults)

def test_send_returns_error_on_network_failure():
    with patch("kwtsms._core._request", side_effect=RuntimeError("Timeout")):
        result = _client().send("96598765432", "Test")
    assert result["result"] == "ERROR"
    assert result["code"] == "NETWORK"
```

Use `patch("kwtsms._core._request", ...)` to mock the API. Never make real
HTTP calls in unit tests.

### Integration test

```python
import pytest
from kwtsms import KwtSMS

# Skip if no credentials
pytestmark = pytest.mark.skipif(
    not os.environ.get("KWTSMS_USERNAME"),
    reason="No credentials"
)

def test_verify_live():
    sms = KwtSMS(
        username=os.environ["KWTSMS_USERNAME"],
        password=os.environ["KWTSMS_PASSWORD"],
        test_mode=True,
        log_file="",
    )
    ok, balance, error = sms.verify()
    assert ok is True
```

Integration tests must use `test_mode=True`.

---

## Submitting a Pull Request

1. Fork the repository and create a branch: `git checkout -b feat/my-feature`
2. Write failing tests first (TDD)
3. Implement the feature
4. Run the full test suite: `uv run pytest`
5. Commit with a clear message: `git commit -m "feat: add X"`
6. Open the pull request with a description of what and why

### Commit message format

```
feat: add X         (new feature)
fix: correct Y      (bug fix)
docs: update Z      (documentation only)
test: add tests for (new or updated tests)
chore: update deps  (maintenance)
```

---

## Versioning

This project uses [Semantic Versioning](https://semver.org/).

- `PATCH` (0.7.x): bug fixes, documentation, internal refactoring
- `MINOR` (0.x.0): new features, backward-compatible API additions
- `MAJOR` (x.0.0): breaking API changes

Version is tracked in two places:

```
pyproject.toml       [project] version = "..."
src/kwtsms/__init__.py  __version__ = "..."
```

Both must be updated together.
