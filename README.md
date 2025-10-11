Safe Python Execution Service

A secure microservice for executing untrusted Python code.
Designed for take-home challenges and sandboxed environments.

Features

Python sandboxing with nsjail
 when supported, falling back to strict process isolation on Cloud Run.

Stateless HTTP API for code execution.

Security constraints:

Runs as non-root user.

Memory, CPU, time, and file-descriptor limits.

No network access inside the sandbox.

API validation:

User script must define main().

main() must return JSON-serializable value.

stdout is captured separately.

Error codes: NO_MAIN, NON_JSON_RETURN, EMPTY_OUTPUT, TIMEOUT.

Endpoints
Health
GET /health


Returns:

{"ok": true}

Execute
POST /execute
Content-Type: application/json
{
  "script": "def main():\n  print('hi')\n  return {\"sum\": 1+2}\n"
}


Response:

{
  "result": {"sum": 3},
  "stdout": "hi\n"
}

Live Deployment

The service is deployed on Google Cloud Run:

https://safe-exec-609738844375.us-central1.run.app


Test it:

# Health check
curl -s https://safe-exec-609738844375.us-central1.run.app/health

# Execute a script
curl -s -X POST https://safe-exec-609738844375.us-central1.run.app/execute \
  -H "Content-Type: application/json" \
  -d '{"script":"def main():\n  print(\"hi\")\n  return {\"sum\": 1+2}\n"}'

Local Development

Build the Docker image:

docker build -t safe-exec .


Run locally:

docker run --rm -p 8080:8080 safe-exec


Test:

curl -s http://localhost:8080/health

Deployment to Cloud Run

Enable APIs:

gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com storage.googleapis.com


Build & push for amd64:

docker buildx build \
  --platform linux/amd64 \
  -t us-central1-docker.pkg.dev/$PROJECT_ID/safe-exec-repo/safe-python-exec:latest \
  --push .


Deploy:

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

Security Notes & Limitations

Cloud Run sandbox already restricts syscalls, which may prevent nsjail from working fully (some policies fail).

The service falls back to a compatibility runner with strict:

Wall-time limits

CPU limits

Memory caps

No persistence: all files created in /tmp are cleared between requests.

No inbound networking allowed inside user code.

This service is not intended for production use without additional monitoring/logging.

Error Codes
Code	Description
NO_MAIN	Script did not define main()
NON_JSON_RETURN	main() did not return JSON-serializable output
EMPTY_OUTPUT	No output produced (sandbox error)
TIMEOUT	Script exceeded time limit
Example Test Cases
# Missing main
curl -s -X POST $SERVICE_URL/execute -H "Content-Type: application/json" \
  -d '{"script":"print(123)"}'

# Non-JSON return
curl -s -X POST $SERVICE_URL/execute -H "Content-Type: application/json" \
  -d '{"script":"def main(): return set([1,2])"}'

# Infinite loop (timeout)
curl -s -X POST $SERVICE_URL/execute -H "Content-Type: application/json" \
  -d '{"script":"def main():\n while True: pass"}'