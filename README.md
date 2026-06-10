# RootLens 🔍

> AI-powered Kubernetes incident analyzer for DevOps, DevSecOps, and SRE teams.

RootLens takes your raw `kubectl` output — logs, events, pod descriptions — and uses Claude to instantly diagnose what went wrong, how bad it is, and exactly how to fix it.

No more grepping through walls of logs at 2am.

## Features

- **AI-powered root-cause analysis** — Claude analyzes `kubectl logs`, `describe pod`, and `get events` output
- **Severity classification** — Critical / High / Medium / Low with color-coded visual dashboard
- **Security-first** — secrets, API keys, JWTs, and AWS credentials are automatically redacted before LLM submission
- **Visual dashboard** — real-time metrics, severity distribution chart, analysis history
- **Structured JSON API** — suitable for automation pipelines and CI/CD integration
- **Example incidents** — CrashLoopBackOff, ImagePullBackOff, OOMKilled, Pending Pods, FailedMount

## Supported Issues

| Issue | Signals detected |
|---|---|
| CrashLoopBackOff | Restart loops, exit codes, back-off messages |
| ImagePullBackOff | Registry auth failures, missing images |
| OOMKilled | Memory limit breaches, exit code 137 |
| Pending Pod | Insufficient resources, unschedulable |
| FailedMount | Missing ConfigMaps / Secrets |
| Readiness/Liveness Probe Failures | Probe timeouts and failures |
| DNS Resolution Issues | lookup errors, NXDOMAIN |
| Service Discovery | Connection refused, no endpoints |
| Resource Exhaustion | CPU throttling, quota exceeded |
| RBAC Errors | Forbidden, permission denied |

## Quick Start

### 1. Clone and configure

```bash
git clone <repo>
cd rootlens
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
```

### 2. Run locally

```bash
pip3 install -r requirements.txt
python3 app.py
# Open http://localhost:8000
```

### 3. Run with Docker

```bash
docker build -t rootlens .
docker run -p 8000:8000 --env-file .env rootlens
```

## API

### `POST /analyze`

```json
{
  "logs":          "...",
  "describe":      "...",
  "events":        "...",
  "yaml_manifest": "..."
}
```

Response:

```json
{
  "root_cause":   "The container is OOMKilled due to a heap size exceeding the 512Mi memory limit.",
  "severity":     "High",
  "evidence":     "Exit Code: 137, Last State Reason: OOMKilled, java.lang.OutOfMemoryError",
  "commands":     ["kubectl top pod worker-7c9f4d6b5-nz8qr -n production", "kubectl describe pod ..."],
  "remediation":  ["Increase memory limit to 1Gi in the Deployment spec", "..."],
  "prevention":   "Set JVM -Xmx flag to 80% of the container memory limit. Use VPA to autoscale.",
  "timestamp":    "2026-06-10T09:00:00Z"
}
```

### `GET /metrics`

Returns aggregate counts by severity since server start.

### `GET /history?limit=50`

Returns the last N analyses (most-recent first).

### `GET /examples/{name}`

Returns a pre-built example incident. Names: `crashloopbackoff`, `imagepullbackoff`, `oomkilled`, `pending-pod`, `failedmount`.

## Security

All inputs are sanitized before reaching the LLM:

| Pattern | Replacement |
|---|---|
| AWS access key (`AKIA…`) | `[REDACTED-AWS-KEY]` |
| AWS secret key | `[REDACTED-AWS-SECRET]` |
| JWT tokens | `[REDACTED-JWT]` |
| Bearer tokens | `[REDACTED-TOKEN]` |
| `password=…`, `api_key=…` | `[REDACTED]` |
| PEM private keys | `[REDACTED-PRIVATE-KEY]` |
| Long hex strings (≥32 chars) | `[REDACTED-HEX-SECRET]` |

## Project Structure

```
rootlens/
├── app.py                    # FastAPI app + routes + metrics/history store
├── services/
│   ├── sanitizer.py          # Secret redaction
│   ├── llm.py                # Anthropic API client + response parser
│   └── analyzer.py           # Orchestration pipeline
├── prompts/
│   └── troubleshoot_prompt.txt  # System prompt for Claude
├── examples/                 # Sample k8s incidents for demo/testing
├── dashboard/
│   └── index.html            # Single-page visual dashboard
├── tests/                    # pytest test suite
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required.** Your Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-opus-4-8` | Model to use |
| `LLM_MAX_TOKENS` | `2048` | Max tokens in LLM response |
| `PORT` | `8000` | Server port |
| `HOST` | `0.0.0.0` | Bind address |
| `RELOAD` | `false` | Enable hot-reload (dev only) |

## Running Tests

```bash
pytest tests/ -v
```
