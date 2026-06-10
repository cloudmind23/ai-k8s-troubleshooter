"""Integration tests for the FastAPI endpoints (no real LLM calls)."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

# Patch the analyzer before importing app so the LLM is never called
_MOCK_RESULT = {
    "root_cause": "Container is crashing due to an unhandled index error in main.go.",
    "severity": "High",
    "evidence": "Exit Code: 2, Restart Count: 8, panic: runtime error: index out of range",
    "commands": ["kubectl logs api-server-7d4b9c8f6-xk2p9 -n production --previous"],
    "remediation": ["Fix the index boundary in main.go line 42", "Redeploy the pod"],
    "prevention": "Add unit tests for boundary conditions and set up liveness probes.",
    "timestamp": "2026-06-10T09:00:00+00:00",
}

with patch("services.analyzer.run_analysis", return_value=_MOCK_RESULT):
    from app import app

client = TestClient(app)


class TestHealth:
    def test_health_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestAnalyze:
    def test_analyze_with_logs(self):
        with patch("services.analyzer.run_analysis", return_value=_MOCK_RESULT):
            r = client.post("/analyze", json={"logs": "CrashLoopBackOff restart count 8"})
        assert r.status_code == 200
        body = r.json()
        assert body["severity"] == "High"
        assert "root_cause" in body
        assert isinstance(body["commands"], list)
        assert isinstance(body["remediation"], list)

    def test_analyze_empty_inputs_rejected(self):
        r = client.post("/analyze", json={})
        assert r.status_code == 422

    def test_analyze_all_empty_strings_rejected(self):
        r = client.post("/analyze", json={"logs": "", "describe": "", "events": ""})
        assert r.status_code == 422

    def test_analyze_response_shape(self):
        with patch("services.analyzer.run_analysis", return_value=_MOCK_RESULT):
            r = client.post("/analyze", json={"events": "Warning FailedScheduling"})
        body = r.json()
        required_keys = {"root_cause", "severity", "evidence", "commands", "remediation", "prevention", "timestamp"}
        assert required_keys.issubset(body.keys())


class TestMetrics:
    def test_metrics_returns_counts(self):
        r = client.get("/metrics")
        assert r.status_code == 200
        body = r.json()
        assert "total_analyses" in body
        assert "by_severity" in body
        assert "started_at" in body

    def test_metrics_by_severity_keys(self):
        r = client.get("/metrics")
        body = r.json()
        for key in ("Critical", "High", "Medium", "Low"):
            assert key in body["by_severity"]


class TestHistory:
    def test_history_returns_list(self):
        r = client.get("/history")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_history_limit_param(self):
        r = client.get("/history?limit=5")
        assert r.status_code == 200
        assert len(r.json()) <= 5


class TestExamples:
    def test_get_example_crashloopbackoff(self):
        r = client.get("/examples/crashloopbackoff")
        assert r.status_code == 200
        body = r.json()
        assert "content" in body
        assert "CrashLoopBackOff" in body["content"] or "crash" in body["content"].lower()

    def test_get_example_oomkilled(self):
        r = client.get("/examples/oomkilled")
        assert r.status_code == 200

    def test_get_example_not_found(self):
        r = client.get("/examples/nonexistent_example")
        assert r.status_code == 404

    def test_path_traversal_blocked(self):
        r = client.get("/examples/../app")
        # FastAPI normalises the path so it won't match a valid route
        assert r.status_code in (404, 422)
