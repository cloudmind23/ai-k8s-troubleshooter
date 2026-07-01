Just shipped something I'm really excited about — **RootLens** 🔍

If you've ever stared at a wall of Kubernetes logs at 2am trying to figure out why a pod keeps crashing, this one's for you.

**RootLens** is an AI-powered K8s troubleshooter that takes your `kubectl logs`, `describe pod`, and `get events` output and gives you back:

✅ Root cause analysis
✅ Severity rating (Critical / High / Medium / Low)
✅ Exact `kubectl` commands to run
✅ Step-by-step remediation
✅ Prevention recommendations

Built with Python, FastAPI, and Claude (Anthropic's LLM) — and yes, it has a visual dashboard with real-time metrics, a severity donut chart, and full analysis history.

One thing I'm especially proud of: **all inputs are sanitized before hitting the LLM** — secrets, API keys, JWTs, AWS credentials are automatically redacted. Security-first by design.

Supports the most common K8s failure modes out of the box:
CrashLoopBackOff · ImagePullBackOff · OOMKilled · Pending Pods · FailedMount · DNS issues · RBAC errors · and more

It's fully containerized with Docker and exposes a clean JSON API — so it plugs straight into CI/CD pipelines or alerting workflows.

Would love to hear what failure scenarios you deal with most in your clusters 👇

#Kubernetes #DevOps #DevSecOps #SRE #CloudNative #AI #Python #FastAPI #OpenSource
