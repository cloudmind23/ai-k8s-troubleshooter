"""Tests for the log sanitizer."""

import sys
from pathlib import Path

# Ensure project root is on path when running from tests/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.sanitizer import sanitize, sanitize_inputs


class TestSanitize:
    def test_aws_access_key(self):
        text = "export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        result = sanitize(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "[REDACTED-AWS-KEY]" in result

    def test_aws_secret_key(self):
        text = "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        result = sanitize(text)
        assert "wJalrXUtnFEMI" not in result
        assert "REDACTED" in result

    def test_jwt_token(self):
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        result = sanitize(jwt)
        assert jwt not in result
        assert "[REDACTED-JWT]" in result

    def test_bearer_token(self):
        text = "Authorization: Bearer eyABC123tokenXYZ"
        result = sanitize(text)
        assert "eyABC123tokenXYZ" not in result
        assert "[REDACTED-TOKEN]" in result

    def test_password_in_env(self):
        text = "DB_PASSWORD=supersecretpassword123"
        result = sanitize(text)
        assert "supersecretpassword123" not in result
        assert "[REDACTED]" in result

    def test_api_key_env(self):
        text = "API_KEY=abc123def456xyz789"
        result = sanitize(text)
        assert "abc123def456xyz789" not in result

    def test_pem_private_key(self):
        pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
        result = sanitize(pem)
        assert "MIIEpAIBAAKCAQEA" not in result
        assert "[REDACTED-PRIVATE-KEY]" in result

    def test_normal_log_line_unchanged(self):
        text = "2026-06-10T09:00:00Z INFO Starting server on port 8080"
        result = sanitize(text)
        # Shouldn't redact normal log content
        assert "Starting server on port 8080" in result

    def test_empty_string(self):
        assert sanitize("") == ""
        assert sanitize(None) == ""

    def test_sanitize_inputs_all_fields(self):
        clean = sanitize_inputs(
            logs="password=secret123",
            describe="Normal describe output",
            events="Normal event",
            yaml_manifest="apiVersion: v1",
        )
        assert "[REDACTED]" in clean["logs"]
        assert clean["describe"] == "Normal describe output"
        assert clean["events"] == "Normal event"
        assert clean["yaml_manifest"] == "apiVersion: v1"

    def test_sanitize_inputs_none_fields(self):
        clean = sanitize_inputs()
        assert all(v == "" for v in clean.values())
