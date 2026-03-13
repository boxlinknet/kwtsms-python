"""Tests for _load_env_file and from_env() edge cases."""
import os
import stat
import tempfile
import pytest
from kwtsms._core import _load_env_file, KwtSMS


def _write_env(content: str) -> str:
    """Write content to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    return f.name


# ── _load_env_file: quote stripping ───────────────────────────────────────────

def test_double_quoted_value():
    path = _write_env('KEY="hello"\n')
    try:
        assert _load_env_file(path)["KEY"] == "hello"
    finally:
        os.unlink(path)


def test_single_quoted_value():
    path = _write_env("KEY='hello'\n")
    try:
        assert _load_env_file(path)["KEY"] == "hello"
    finally:
        os.unlink(path)


def test_mixed_quotes_not_stripped():
    """A value starting with " but ending with ' must NOT be stripped at all."""
    path = _write_env('KEY="hello\'\n')
    try:
        assert _load_env_file(path)["KEY"] == '"hello\''
    finally:
        os.unlink(path)


def test_value_with_equals_sign():
    """Values containing = signs must be preserved fully."""
    path = _write_env("KEY=abc=def=ghi\n")
    try:
        assert _load_env_file(path)["KEY"] == "abc=def=ghi"
    finally:
        os.unlink(path)


def test_password_with_hash_char():
    """A value that contains # must be preserved (# is not a comment mid-value)."""
    path = _write_env("KWTSMS_PASSWORD=p@ss#word!\n")
    try:
        assert _load_env_file(path)["KWTSMS_PASSWORD"] == "p@ss#word!"
    finally:
        os.unlink(path)


def test_comment_lines_skipped():
    path = _write_env("# comment\nKEY=val\n")
    try:
        env = _load_env_file(path)
        assert "# comment" not in env
        assert env["KEY"] == "val"
    finally:
        os.unlink(path)


def test_missing_file_returns_empty_dict():
    assert _load_env_file("/nonexistent/.env.xyz") == {}


# ── from_env(): KWTSMS_LOG_FILE="" must disable logging ──────────────────────

def test_from_env_empty_log_file_env_var_disables_logging(monkeypatch):
    """KWTSMS_LOG_FILE='' in environment must disable logging, not fall through to default."""
    monkeypatch.setenv("KWTSMS_USERNAME", "user")
    monkeypatch.setenv("KWTSMS_PASSWORD", "pass")
    monkeypatch.setenv("KWTSMS_LOG_FILE", "")
    sms = KwtSMS.from_env("/nonexistent/.env.xyz")
    assert sms.log_file == "", "Empty KWTSMS_LOG_FILE should disable logging"


def test_from_env_env_var_takes_priority_over_env_file(monkeypatch, tmp_path):
    """Env var must override .env file value."""
    env_file = str(tmp_path / ".env")
    with open(env_file, "w") as f:
        f.write("KWTSMS_USERNAME=fileuser\nKWTSMS_PASSWORD=filepass\nKWTSMS_LOG_FILE=file.log\n")
    monkeypatch.setenv("KWTSMS_USERNAME", "fileuser")
    monkeypatch.setenv("KWTSMS_PASSWORD", "filepass")
    monkeypatch.setenv("KWTSMS_LOG_FILE", "env.log")
    sms = KwtSMS.from_env(env_file)
    assert sms.log_file == "env.log"
