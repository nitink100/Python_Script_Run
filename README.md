Nice—I've unpacked your latest zip and checked the repo. Here’s what you’ve got now:

* Root: `app.py`, `runner.py`, `policy.kafel`, `Dockerfile`, `requirements.txt`, `docker-compose.yml`, `Makefile`, `LICENSE`, `.gitignore`, `.editorconfig`, `.pre-commit-config.yaml`, `CONTRIBUTING.md`, `SECURITY.md`, `README.md`
* New docs: `openapi_spec.py`, `api_docs.py`
* Blueprints are correctly registered in `app.py` (`/docs` and `/openapi.json` are live).
* I noticed a macOS artifact `.DS_Store` in the root. Your `.gitignore` already ignores `.venv/` but **not** `.DS_Store`.

Two tiny, non-breaking improvements:

1. Add `.DS_Store` to `.gitignore` (one line; keeps the repo clean).
2. Replace `README.md` with the updated version below (includes `/docs` & `/openapi.json`, and an optional `/routes` debug tip).

If that works for you, do just these two edits.

---

# 1) Append to `.gitignore` (one line)

Add this to the end of `.gitignore`:

```
# macOS
.DS_Store
```

Optionally delete the existing file:

```bash
git rm -f .DS_Store
```

---

# 2) Replace `README.md` with this (copy–paste all)

````markdown
# Safe Python Execution Service

A small, secure microservice that executes **untrusted Python code** under strict limits.  
Built as a take-home exercise; packaged for easy local use and Google Cloud Run deployment.

---

## What it does

- **HTTP API** to execute a Python snippet that defines `main()`.
- Runs as a **non-root** user with **time/CPU/memory/file-descriptor** caps.
- **No network** access for user code (via nsjail policy); portable fallback when nsjail is restricted (e.g., on Cloud Run).
- Returns the `main()` return value (must be JSON-serializable) and captured `stdout`.

---

## Endpoints

### `GET /health` and `GET /healthz`
- **200 OK** → `{"ok": true}`

### `POST /execute`
**Request body**
```json
{
  "script": "def main():\n  print('hello')\n  return {'answer': 42}\n"
}
````

**Success (200)**

```json
{
  "result": {"answer": 42},
  "stdout": "hello\n"
}
```

**Errors**

Validation:

* `BAD_CONTENT_TYPE`, `BAD_BODY`, `BAD_SCRIPT`, `BAD_ENCODING`, `BAD_INPUT`, `SCRIPT_TOO_LARGE`, `SYNTAX_ERROR`, `NO_MAIN`

Runtime/timeouts:

* `TIMEOUT`, `EMPTY_OUTPUT`

Runner-level (normalized by API):

* `IMPORT_ERROR`, `INVALID_MAIN`, `EXCEPTION`, `NON_JSON_RETURN`, `BAD_RUNNER_OUTPUT`

Every error is returned as:

```json
{
  "error": {
    "code": "<CODE>",
    "message": "<human readable>",
    "details": { "..." : "optional" }
  }
}
```

### Docs & schema

* **Swagger UI**: `GET /docs`
* **OpenAPI JSON**: `GET /openapi.json`

> Tip (optional): add `GET /routes` locally to list all registered routes for debugging:
>
> ```python
> @app.get("/routes")
> def _routes():
>     return {"routes": sorted([str(r) for r in app.url_map.iter_rules()])}
> ```

---

## Quickstart

### Option A — Docker (recommended)

```bash
# Build
docker build -t safe-exec .

# Run
docker run --rm -p 8080:8080 safe-exec

# Health
curl -s http://localhost:8080/health

# Execute a script
curl -s -X POST http://localhost:8080/execute \
  -H "Content-Type: application/json" \
  -d '{"script":"def main():\n  print(\"hi\")\n  return {\"sum\": 1+2}\n"}'

# Docs (browser)
# http://localhost:8080/docs
```

### Option B — Python virtualenv (local dev)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
# server on http://127.0.0.1:8080
```

---

## Example failure cases (for reviewers)

```bash
# 1) Missing main()
curl -s -X POST http://localhost:8080/execute \
  -H "Content-Type: application/json" \
  -d '{"script":"print(123)"}'

# 2) Non-JSON return
curl -s -X POST http://localhost:8080/execute \
  -H "Content-Type: application/json" \
  -d '{"script":"def main():\n  return {x for x in range(3)}\n"}'

# 3) Infinite loop (timeout)
curl -s -X POST http://localhost:8080/execute \
  -H "Content-Type: application/json" \
  -d '{"script":"def main():\n  while True: pass\n"}'
```

You can also post the ready-made samples in `tests/`:

```bash
curl -s -X POST http://localhost:8080/execute \
  -H "Content-Type: application/json" \
  -d @tests/sample_ok.json
```

---

## How it works (short)

```
Client --> Flask API (app.py)
            • Validates payload & size
            • Writes script into /tmp/safe_exec/<uuid>/script.py
            • Tries nsjail strict mode; falls back to compat if needed
            • Captures stdout, enforces limits, parses runner JSON
            • Returns {result, stdout} or a structured error

Runner (runner.py)
            • Imports script as a module
            • Calls main(), collects stdout
            • Ensures JSON-serializable return
```

* **nsjail policy** (`policy.kafel`): disables socket syscalls (no network).
* **Fallback**: If nsjail is unavailable/restricted (common on Cloud Run), the service automatically runs a portable compatibility path with conservative limits.

---

## Configuration

Environment variables (sane defaults baked in):

| Variable           | Default                 | Meaning                                 |
| ------------------ | ----------------------- | --------------------------------------- |
| `PORT`             | `8080`                  | HTTP port (Flask/Gunicorn)              |
| `MAX_SCRIPT_BYTES` | `65536`                 | Max script size (bytes)                 |
| `MAX_STDOUT_BYTES` | `204800`                | Truncate stdout after this many bytes   |
| `TIME_LIMIT_SEC`   | `5`                     | Wall-clock limit (nsjail runner)        |
| `CPU_LIMIT_SEC`    | `3`                     | CPU seconds limit                       |
| `MEM_LIMIT_MB`     | `512`                   | Memory limit (address space)            |
| `FSIZE_LIMIT_MB`   | `10`                    | Max file size                           |
| `NOFILE_LIMIT`     | `256`                   | Max open file descriptors               |
| `NSJAIL_PATH`      | `/usr/local/bin/nsjail` | nsjail binary path (inside container)   |
| `PYTHON_BIN`       | `/usr/local/bin/python` | Python interpreter used by runner       |
| `FORCE_COMPAT`     | `0`                     | If `1/true`, skip nsjail and use compat |

> The Docker image builds nsjail in a separate stage and copies it into the runtime image. Cloud Run’s sandbox may still restrict certain capabilities; the app safely falls back automatically.

---

## Project layout

```
.
├── app.py              # HTTP API (registers /docs, /openapi.json)
├── runner.py           # Sandboxed execution logic
├── policy.kafel        # nsjail policy (sockets off)
├── openapi_spec.py     # OpenAPI 3.0 spec dict
├── api_docs.py         # Minimal Swagger UI page + /openapi.json
├── tests/
│   ├── sample_ok.json
│   ├── missing_main.json
│   ├── not_json_return.json
│   └── infinite_loop.json
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── Makefile
├── .editorconfig
├── .pre-commit-config.yaml
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
└── README.md
```

---

## Local testing

This repo includes ready-to-post JSON samples under `tests/`. Use the `curl` examples above or wire simple client scripts.

If you add Python tests later, `pytest -q` will run them:

```bash
pip install -U pytest
pytest -q
```

---

## Deployment (Google Cloud Run)

Below is a simple, reproducible flow (replace `$PROJECT_ID` and repo path as needed):

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# Build & push (amd64 is typical for Cloud Run)
docker buildx build --platform linux/amd64 \
  -t us-central1-docker.pkg.dev/$PROJECT_ID/safe-exec-repo/safe-python-exec:latest \
  --push .

gcloud run deploy safe-exec \
  --image us-central1-docker.pkg.dev/$PROJECT_ID/safe-exec-repo/safe-python-exec:latest \
  --platform managed \
  --allow-unauthenticated \
  --region us-central1 \
  --port 8080 \
  --concurrency 1 \
  --timeout 10s \
  --memory 1Gi \
  --set-env-vars=FORCE_COMPAT=1
```

If you already have a deployed service, you can keep the public URL in this README for easy verification.

---

## Security & limitations

* This is an educational sandbox; not production-grade without platform-level egress controls, monitoring/alerting, and more exhaustive jail policies.
* No inbound/outbound network from user code (policy-enforced).
* Scripts must define a callable `main()` and return a JSON-serializable value.

---

## License

MIT License