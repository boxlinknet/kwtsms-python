# Changelog

All notable changes to the kwtSMS Python client are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [0.7.35] - 2026-03-14

### Added
- `README.md`: Downloads and GitGuardian badges

---

## [0.7.34] - 2026-03-14

### Added
- Country-specific phone validation rules for 80+ countries (`_PHONE_RULES`)
- `find_country_code()` function: find country code prefix from a normalized phone number
- `validate_phone_format()` function: validate phone numbers against country-specific length and mobile prefix rules
- Domestic trunk prefix stripping in `normalize_phone()` (e.g., `9660559...` becomes `966559...`)
- Both new functions exported from top-level `kwtsms` package
- 24 new phone validation tests

### Changed
- `validate_phone_input()` now runs country-specific format validation after basic checks

---

## [0.7.33] - 2026-03-14

### Added
- `.github/workflows/gitguardian.yml`: GitGuardian secret scanning on push and pull request

---

## [0.7.32] - 2026-03-13

### Removed
- CLI module (`_cli.py`) and `[project.scripts]` entry point removed. Use the standalone [kwtsms-cli](https://github.com/boxlinknet/kwtsms-cli) instead.

---

## [0.7.31] - 2026-03-06

### Added
- `README.md`: CI and CodeQL status badges

---

## [0.7.30] - 2026-03-06

### Changed
- Version bump to unblock PyPI publish (v0.7.29 publish workflow stuck in queue due to GitHub infrastructure issue)

---

## [0.7.29] - 2026-03-06

### Fixed
- `README.md`: corrected error handling example (`send()` never raises, removed incorrect `try/except RuntimeError`)
- `README.md`: documented `status()`, `send_with_retry()`, `parse_webhook()`, and `AsyncKwtSMS` (were missing)
- `README.md`: added `parse_webhook` to utility functions import line, added `_async.py` to repository layout
- `CONTRIBUTING.md`: fixed repo URL (`kwtsms_python` → `kwtsms-python`), updated project structure and exports, added new test files, corrected optional dependency policy
- `examples/README.md`: fixed CLI example syntax (`--phone`/`--message` flags do not exist)

---

## [0.7.28] - 2026-03-06

### Changed
- GitHub Actions: bumped `actions/checkout` to v6, `actions/setup-python` to v6, `github/codeql-action` to v4 across all workflows

### Fixed
- `.gitignore`: added `.pytest_cache/` exclusion
- Removed empty `tests/__init__.py` (not required by pytest)
- `uv.lock`: synced to match declared dev dependencies

---

## [0.7.27] - 2026-03-06

### Added
- `.github/workflows/codeql.yml`: CodeQL security scanning on push, pull request, and weekly schedule
- `.github/dependabot.yml`: Dependabot weekly checks for pip and GitHub Actions dependency updates

---

## [0.7.26] - 2026-03-06

### Changed
- Module docstring: added `send_with_retry()` to the quick start example block

---

## [0.7.25] - 2026-03-05

### Added
- `SECURITY.md`: security policy and vulnerability reporting guidelines

---

## [0.7.24] - 2026-03-05

### Added
- `send_with_retry()` method on `KwtSMS`: automatically retries on ERR028 (rate limit) with a 16-second wait between attempts
- `tests/test_retry.py`: four tests covering first-attempt success, ERR028 retry with sleep, exhausted retries, and non-ERR028 errors not retried

---

## [0.7.23] - 2026-03-05

### Added
- `AsyncKwtSMS` class in `src/kwtsms/_async.py`: async version of `KwtSMS` using `aiohttp`
- Methods: `verify()`, `balance()`, `send()`, `status()`, `from_env()`, `purchased` property
- Optional dependency: `pip install kwtsms[async]` (installs aiohttp)
- `tests/test_async.py`: six tests covering constructor validation, verify, send (OK and pre-validation errors), and network error handling
- `AsyncKwtSMS` exported from top-level `kwtsms` package

---

## [0.7.22] - 2026-03-05

### Added
- `parse_webhook()` module-level function: parses kwtSMS delivery receipt webhook payloads, returning a clean dict with snake_case keys (`msg_id`, `phone`, `status`, `delivered_at`)
- `tests/test_webhook.py`: seven tests covering valid payload, missing required fields, non-dict input, all known status values, and unknown status passthrough
- `parse_webhook` exported from top-level `kwtsms` package

---

## [0.7.21] - 2026-03-05

### Added
- `status()` method on `KwtSMS`: looks up delivery status for a sent message via `/report/` endpoint
- `tests/test_status.py`: three tests covering OK response, error enrichment, and network error handling

---

## [0.7.20] - 2026-03-05

### Added
- GitHub Actions CI workflow: runs pytest on Python 3.8 through 3.13 on every push and pull request
- GitHub Actions publish workflow: builds and publishes to PyPI automatically on tag push using trusted publisher (no stored secrets)

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
