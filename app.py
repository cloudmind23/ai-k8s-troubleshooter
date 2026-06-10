"""
AI-powered Kubernetes Troubleshooter — FastAPI application.

Endpoints:
  POST /analyze      — analyse k8s logs / describe / events
  GET  /metrics      — aggregated usage statistics
  GET  /history      — last N analysis records
  GET  /health       — liveness probe
  GET  /             — serve the visual dashboard
"""

from __future__ import annotations

import os
from dotenv import load_dotenv
load_dotenv()  # loads .env from the project directory
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from services.analyzer import run_analysis

# ---------------------------------------------------------------------------
# In-memory store  (replaced by a real DB in production)
# ---------------------------------------------------------------------------
MAX_HISTORY = 200

_history: Deque[dict] = deque(maxlen=MAX_HISTORY)
_metrics: dict = {
    "total_analyses": 0,
    "by_severity": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Unknown": 0},
    "started_at": datetime.now(timezone.utc).isoformat(),
}


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀  AI K8s Troubleshooter ready")
    yield
    print("🛑  AI K8s Troubleshooter shutting down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Kubernetes Troubleshooter",
    description="LLM-powered DevSecOps tool for K8s root-cause analysis",
    version="1.0.0",
    lifespan=lifespan,
)

# Serve dashboard static files
_dashboard_dir = Path(__file__).parent / "dashboard"
if _dashboard_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_dashboard_dir)), name="static")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    logs: Optional[str] = Field(default="", description="Output of `kubectl logs <pod>`")
    describe: Optional[str] = Field(default="", description="Output of `kubectl describe pod <pod>`")
    events: Optional[str] = Field(default="", description="Output of `kubectl get events`")
    yaml_manifest: Optional[str] = Field(default="", description="Kubernetes YAML manifest (optional)")


class AnalyzeResponse(BaseModel):
    root_cause: str
    severity: str
    evidence: str
    commands: list[str]
    remediation: list[str]
    prevention: str
    timestamp: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard():
    """Serve the visual dashboard."""
    index = _dashboard_dir / "index.html"
    if not index.exists():
        return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)
    return HTMLResponse(content=index.read_text(encoding="utf-8"))


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    """
    Analyse Kubernetes diagnostic data and return structured root-cause analysis.
    Secrets are automatically redacted before data is sent to the LLM.
    """
    if not any([req.logs, req.describe, req.events, req.yaml_manifest]):
        raise HTTPException(
            status_code=422,
            detail="Provide at least one of: logs, describe, events, yaml_manifest",
        )

    try:
        result = run_analysis(
            logs=req.logs or "",
            describe=req.describe or "",
            events=req.events or "",
            yaml_manifest=req.yaml_manifest or "",
        )
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")

    # Update metrics & history
    severity = result.get("severity", "Unknown")
    _metrics["total_analyses"] += 1
    _metrics["by_severity"][severity] = _metrics["by_severity"].get(severity, 0) + 1

    _history.appendleft(
        {
            "id": _metrics["total_analyses"],
            "root_cause": result["root_cause"][:120],
            "severity": severity,
            "timestamp": result["timestamp"],
        }
    )

    return AnalyzeResponse(**result)


@app.get("/metrics")
async def metrics():
    """Return aggregated usage statistics."""
    return JSONResponse(content=_metrics)


@app.get("/history")
async def history(limit: int = 50):
    """Return the last *limit* analysis records (most-recent first)."""
    limit = min(limit, MAX_HISTORY)
    return JSONResponse(content=list(_history)[:limit])


@app.get("/examples/{name}")
async def get_example(name: str):
    """Return the contents of a named example file."""
    safe_name = Path(name).name  # strip path traversal
    example_file = Path(__file__).parent / "examples" / f"{safe_name}.txt"
    if not example_file.exists():
        raise HTTPException(status_code=404, detail=f"Example '{name}' not found")
    return JSONResponse(content={"name": name, "content": example_file.read_text(encoding="utf-8")})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() == "true",
    )
