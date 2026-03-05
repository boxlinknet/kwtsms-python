# Changelog

All notable changes to the kwtSMS Python client are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [Unreleased]

---

## [0.7.19] - 2026-03-05

### Added
- PyPI version, Python versions, and License badges to README

---

## [0.7.18] - 2026-03-05

### Changed
- Development Status classifier: Alpha to Beta
- Added Python 3.13 classifier
- Fixed project.urls: added Repository and Changelog links, updated Documentation to point to examples

---

## [0.7.17] - 2026-03-05

### Fixed
- `examples/README.md`: em dash in title replaced with colon (style rule)

---

## [0.7.16] - 2026-03-05

### Added
- `examples/` directory with 10 runnable Python example scripts
- `examples/docs/` with a detailed `.md` guide for each example
- `examples/README.md` index with setup instructions and table of all examples
- `examples/.env.example` template for credential setup
- `CHANGELOG.md` (this file)
- `CONTRIBUTING.md` with Python-specific contribution guidelines

### Changed
- `.gitignore`: removed `/tests/` (tests are now committed); added `.claude/` local config exclusion

---

## [0.7.15] - 2026-03-04

### Added
- `KwtSMS.purchased` public property (exposes `_cached_purchased`)
- `TestNetworkFailureOnSend`, `TestCoverageNetworkError`, `TestPurchasedProperty`,
  `TestEmptyMessageAfterCleaning` test classes in `tests/test_api_errors.py`
- `tests/test_bulk.py`: routing threshold, bulk result statuses, ERR013 retry logic
- `tests/test_env.py`: `_load_env_file` quote handling, `KWTSMS_LOG_FILE=""` behavior,
  newline sanitization

### Fixed
- `_load_env_file()`: quote stripping now only strips one matching outer pair
  (`"hello'"` was previously corrupted by chained `.strip('"').strip("'")`)
- `from_env()`: `get()` helper now uses `is not None` check so `KWTSMS_LOG_FILE=""`
  is honored instead of falling through to the default
- `_request()`: renamed second `body` variable to `err_body` in HTTPError handler
  to prevent shadowing
- `_cli.py`: `--sender` without a value now prints the actual argparse error message
  instead of silently swallowing it
- `coverage()`: network error response now includes the `action` field

---

## [0.7.14] - 2026-03-04

### Added
- Emoji stripping extended to cover flags (regional indicator symbols U+1F1E0–U+1F1FF),
  keycap U+20E3 (1️⃣ 2️⃣), mahjong tiles and playing cards (U+1F000–U+1F0FF),
  and tags block subdivision flags (U+E0000–U+E007F)
- ERR009 local detection: `send()` now catches emoji-only or invisible-character-only
  messages before any API call and returns ERR009 without consuming credits
- `.env` write in `kwtsms setup` now sets file permissions to `0o600`
- `.env` write sanitizes newlines from all credential inputs to prevent injection

### Fixed
- `_char_is_sms_safe()` and `_HIDDEN_CHARS` moved to module level to avoid
  redefinition on every `clean_message()` call
- `sms._cached_purchased` replaced with public `sms.purchased` property in CLI output

### Changed
- All test and documentation placeholder credentials changed to `python_username` /
  `python_password` for easier library identification in API logs

---

## [0.7.13] - 2026-03-01

### Added
- `_enrich_error()`: adds developer-friendly `action` field to all API error
  responses (ERR001–ERR033)
- `tests/test_api_errors.py`: comprehensive error enrichment tests
- `tests/test_phone.py`: phone normalization and validation tests
- `tests/test_message.py`: message cleaning tests
- `tests/test_integration.py`: live API integration tests (requires credentials)

### Fixed
- `send()` now wraps `_request()` in try/except and returns a dict instead of
  raising on network errors
- ERR013 retry logic in `_send_bulk()` now uses correct backoff delays (30s/60s/120s)

---

## [0.7.10] - 2026-02-15

### Added
- `senderids()` method: list registered Sender IDs via `/senderid/` endpoint
- `coverage()` method: list active country prefixes via `/coverage/` endpoint

### Changed
- `verify()` error string now includes both description and action:
  `"Authentication error... -> Wrong API username or password..."`

---

## [0.7.6] - 2026-02-01

### Changed
- Repository structure flattened: `pyproject.toml` moved to repo root
- `src/kwtsms/` layout adopted (PEP 517 src layout)

---

## [0.7.0] - 2026-01-15

### Added
- Initial release
- `KwtSMS` class with `verify()`, `balance()`, `send()`, `validate()`
- `KwtSMS.from_env()` class method
- `normalize_phone()` and `validate_phone_input()` module-level functions
- `clean_message()` with HTML stripping, emoji removal, Arabic digit conversion,
  hidden character removal
- `_load_env_file()` for `.env` file loading
- JSONL request logging with password masking
- CLI: `kwtsms verify`, `kwtsms send`, `kwtsms balance`, `kwtsms setup`
- Bulk send with auto-batching for > 200 numbers
- ERR013 retry with 30s/60s/120s backoff in bulk mode
- Zero external dependencies, Python 3.8+
