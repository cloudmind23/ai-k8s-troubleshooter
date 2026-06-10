"""Tests for the LLM response parser (no API calls)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.llm import _parse_response, _extract_severity


class TestParseResponse:
    def test_parses_json_block(self):
        raw = '''Here is the analysis:
```json
{
  "root_cause": "OOMKilled due to heap overflow",
  "severity": "High",
  "evidence": "Exit Code: 137",
  "commands": ["kubectl top pod foo"],
  "remediation": ["Increase memory limit"],
  "prevention": "Use VPA"
}
```'''
        result = _parse_response(raw)
        assert result["severity"] == "High"
        assert result["root_cause"] == "OOMKilled due to heap overflow"
        assert isinstance(result["commands"], list)

    def test_parses_raw_json(self):
        raw = '{"root_cause":"DNS failure","severity":"Medium","evidence":"NXDOMAIN","commands":[],"remediation":["Check CoreDNS"],"prevention":"Use readiness probes"}'
        result = _parse_response(raw)
        assert result["severity"] == "Medium"

    def test_fallback_section_extraction(self):
        raw = """
Root Cause: The pod is OOMKilled because the JVM heap exceeds the container limit.

Severity: Critical

Evidence: Exit Code 137, OOMKilled in Last State

Recommended Commands:
kubectl describe pod worker-abc -n production
kubectl top pod worker-abc

Remediation Steps:
1. Increase memory limit to 1Gi
2. Set -Xmx to 80% of container limit
3. Redeploy the workload

Prevention:
Use Vertical Pod Autoscaler and set JVM heap flags correctly.
"""
        result = _parse_response(raw)
        assert result["severity"] == "Critical"
        assert "OOMKilled" in result["root_cause"]
        assert len(result["commands"]) >= 1
        assert len(result["remediation"]) >= 1

    def test_missing_fields_default_to_empty(self):
        result = _parse_response("{}")
        # Should return empty strings/lists for missing keys (handled by analyzer)
        assert isinstance(result, dict)


class TestExtractSeverity:
    def test_critical(self):
        assert _extract_severity("Severity: Critical") == "Critical"

    def test_high_case_insensitive(self):
        assert _extract_severity("severity: HIGH") == "High"

    def test_medium(self):
        assert _extract_severity("**Severity:** Medium") == "Medium"

    def test_low(self):
        assert _extract_severity("Severity - low") == "Low"

    def test_not_found(self):
        assert _extract_severity("No severity info here") == "Unknown"
