"""
Log sanitizer — redacts secrets before sending data to the LLM.

Patterns covered:
  - AWS access keys and secret keys
  - Generic API keys / Bearer tokens
  - JWT tokens
  - Passwords in key=value form
  - Private keys (PEM blocks)
  - Generic base64-encoded secrets in env vars
"""

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Redaction patterns  (pattern, replacement_label)
# ---------------------------------------------------------------------------
_PATTERNS: list[tuple[re.Pattern, str]] = [
    # AWS access key  (AKIA…)
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED-AWS-KEY]"),
    # AWS secret key — 40 char base64-ish following common env names
    (
        re.compile(
            r"(?i)(aws_secret_access_key|aws_secret_key)\s*[=:]\s*['\"]?([A-Za-z0-9+/]{40})['\"]?"
        ),
        r"\1=[REDACTED-AWS-SECRET]",
    ),
    # JWT   header.payload.signature
    (
        re.compile(
            r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
        ),
        "[REDACTED-JWT]",
    ),
    # Bearer tokens
    (
        re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-._~+/]+=*"),
        r"\1[REDACTED-TOKEN]",
    ),
    # Passwords in key=value / key: value form
    (
        re.compile(
            r"(?i)(password|passwd|secret|token|api[_-]?key|auth[_-]?token)"
            r"\s*[=:]\s*['\"]?([^\s'\"]{4,})['\"]?"
        ),
        r"\1=[REDACTED]",
    ),
    # PEM private keys
    (
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
        "[REDACTED-PRIVATE-KEY]",
    ),
    # Generic long hex strings that look like secrets (≥32 hex chars)
    (
        re.compile(r"\b[0-9a-fA-F]{32,}\b"),
        "[REDACTED-HEX-SECRET]",
    ),
]


def sanitize(text: Optional[str]) -> str:
    """Apply all redaction patterns to *text* and return the sanitized string."""
    if not text:
        return ""
    result = text
    for pattern, replacement in _PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def sanitize_inputs(
    logs: Optional[str] = None,
    describe: Optional[str] = None,
    events: Optional[str] = None,
    yaml_manifest: Optional[str] = None,
) -> dict[str, str]:
    """Sanitize all four input fields and return a dict of clean strings."""
    return {
        "logs": sanitize(logs),
        "describe": sanitize(describe),
        "events": sanitize(events),
        "yaml_manifest": sanitize(yaml_manifest),
    }
