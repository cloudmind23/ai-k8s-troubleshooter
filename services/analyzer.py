"""
Analyzer — orchestrates sanitization → LLM analysis → structured response.
"""

from datetime import datetime, timezone

from .sanitizer import sanitize_inputs
from .llm import analyze as llm_analyze


def run_analysis(
    logs: str = "",
    describe: str = "",
    events: str = "",
    yaml_manifest: str = "",
) -> dict:
    """
    Full pipeline:
      1. Sanitize all inputs
      2. Call LLM
      3. Enrich response with metadata

    Returns the analysis dict (root_cause, severity, evidence, commands,
    remediation, prevention, timestamp, sanitized_inputs).
    """
    clean = sanitize_inputs(logs, describe, events, yaml_manifest)

    result = llm_analyze(
        logs=clean["logs"],
        describe=clean["describe"],
        events=clean["events"],
        yaml_manifest=clean["yaml_manifest"],
    )

    # Normalise fields so downstream consumers can rely on types
    result.setdefault("root_cause", "Unable to determine root cause")
    result.setdefault("severity", "Unknown")
    result.setdefault("evidence", "")
    result.setdefault("commands", [])
    result.setdefault("remediation", [])
    result.setdefault("prevention", "")

    if isinstance(result["commands"], str):
        result["commands"] = [
            line.strip()
            for line in result["commands"].splitlines()
            if line.strip()
        ]
    if isinstance(result["remediation"], str):
        result["remediation"] = [
            line.strip()
            for line in result["remediation"].splitlines()
            if line.strip()
        ]

    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    return result
