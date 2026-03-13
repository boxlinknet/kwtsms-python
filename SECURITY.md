# Security Policy

## Supported Versions

Only the latest release receives security fixes.

| Version | Supported |
|---------|-----------|
| 0.7.x (latest) | Yes |
| < 0.7 | No |

## Reporting a Vulnerability

Email: mo@boxlink.net

Please do not open a public GitHub issue for security vulnerabilities.

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact

You will receive a response within 48 hours.

## Security Notes

### Trusted configuration parameters

`log_file` and `env_file` are passed directly to `open()`. These are trusted configuration values set by the developer, not user input. Do not expose them to end users or accept them from untrusted sources.

### Thread safety

`KwtSMS` and `AsyncKwtSMS` instances are not thread-safe. Cached values (`_cached_balance`, `_cached_purchased`) are read and written without locks. In CPython, the GIL makes simple float assignment atomic in practice, but this is not guaranteed by the language spec. If sharing a client instance across threads, protect calls with your own lock.

### Error messages may contain user input

Validation error messages (e.g., `"'user@gmail.com' is an email address, not a phone number"`) include the raw input. This is safe in JSONL logs (JSON-encoded). If you display these messages in HTML, escape them first to prevent XSS.
