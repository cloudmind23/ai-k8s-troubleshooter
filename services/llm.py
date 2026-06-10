"""
LLM service — wraps the Anthropic Claude API and parses structured output.
"""

import json
import os
import re
from pathlib import Path

import anthropic

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "troubleshoot_prompt.txt"
_SYSTEM_PROMPT: str = _PROMPT_PATH.read_text(encoding="utf-8")

_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def analyze(
    logs: str,
    describe: str,
    events: str,
    yaml_manifest: str = "",
) -> dict:
    """
    Send sanitized k8s data to Claude and return a structured analysis dict.

    Returns keys: root_cause, severity, evidence, commands, remediation, prevention
    """
    user_content = _build_user_message(logs, describe, events, yaml_manifest)
    client = _get_client()

    message = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = message.content[0].text
    return _parse_response(raw)


def _build_user_message(logs: str, describe: str, events: str, yaml_manifest: str) -> str:
    parts: list[str] = []
    if logs:
        parts.append(f"## kubectl logs\n```\n{logs}\n```")
    if describe:
        parts.append(f"## kubectl describe pod\n```\n{describe}\n```")
    if events:
        parts.append(f"## kubectl get events\n```\n{events}\n```")
    if yaml_manifest:
        parts.append(f"## Kubernetes YAML manifest\n```yaml\n{yaml_manifest}\n```")

    if not parts:
        raise ValueError("At least one input (logs, describe, or events) must be provided.")

    return "\n\n".join(parts)


def _parse_response(raw: str) -> dict:
    """
    Try JSON block first; fall back to regex section extraction.
    """
    # 1. JSON block
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 2. Raw JSON object
    json_match2 = re.search(r"(\{.*\})", raw, re.DOTALL)
    if json_match2:
        try:
            return json.loads(json_match2.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Regex section extraction (human-readable fallback)
    def extract(label: str) -> str:
        m = re.search(
            rf"(?i)(?:^|\n)(?:#{1,3}\s*)?{label}\s*[:\-]?\s*\n(.*?)(?=\n(?:#{1,3}\s*)?\w[\w\s]*[:\-]|\Z)",
            raw,
            re.DOTALL,
        )
        return m.group(1).strip() if m else ""

    commands_raw = extract("Recommended Commands?")
    commands = [
        line.strip().lstrip("-").strip()
        for line in commands_raw.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    remediation_raw = extract("Remediation Steps?")
    remediation = [
        re.sub(r"^\d+\.\s*", "", line).strip()
        for line in remediation_raw.splitlines()
        if line.strip()
    ]

    return {
        "root_cause": extract("Root Cause"),
        "severity": _extract_severity(raw),
        "evidence": extract("Evidence"),
        "commands": commands,
        "remediation": remediation,
        "prevention": extract("Prevention"),
    }


def _extract_severity(text: str) -> str:
    m = re.search(r"(?i)severity\s*[:\-]?\s*(critical|high|medium|low)", text)
    return m.group(1).capitalize() if m else "Unknown"
