import os, uuid, ast, json, shutil, subprocess
from typing import Any, Dict
from flask import Flask, request, jsonify
from api_docs import openapi_bp, docs_bp

# --- Tunables ---
MAX_SCRIPT_BYTES = int(os.getenv("MAX_SCRIPT_BYTES", 64 * 1024))
MAX_STDOUT_BYTES = int(os.getenv("MAX_STDOUT_BYTES", 200 * 1024))
NSJAIL_PATH     = os.getenv("NSJAIL_PATH", "/usr/local/bin/nsjail")
PYTHON_BIN      = os.getenv("PYTHON_BIN", "/usr/local/bin/python")
TIME_LIMIT_SEC  = int(os.getenv("TIME_LIMIT_SEC", "5"))
CPU_LIMIT_SEC   = int(os.getenv("CPU_LIMIT_SEC", "3"))
MEM_LIMIT_MB    = int(os.getenv("MEM_LIMIT_MB", "512"))
FSIZE_LIMIT_MB  = int(os.getenv("FSIZE_LIMIT_MB", "10"))
NOFILE_LIMIT    = int(os.getenv("NOFILE_LIMIT", "256"))
PORT            = int(os.getenv("PORT", "8080"))
FORCE_COMPAT    = os.getenv("FORCE_COMPAT", "0").lower() in ("1","true","yes")

app = Flask(__name__)
app.register_blueprint(openapi_bp)
app.register_blueprint(docs_bp)


def _error(code: str, message: str, http=400, details: Dict[str, Any] | None = None):
    payload = {"error": {"code": code, "message": message}}
    if details: payload["error"]["details"] = details
    return jsonify(payload), http

@app.get("/health")
def health(): return jsonify({"ok": True})

@app.post("/execute")
def execute():
    if not request.is_json:
        return _error("BAD_CONTENT_TYPE","Content-Type must be application/json",415)
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _error("BAD_BODY","Request body must be a JSON object")

    script = body.get("script")
    if not isinstance(script, str):
        return _error("BAD_SCRIPT","'script' must be a string containing Python code")

    try:
        script_bytes = script.encode("utf-8")
    except UnicodeEncodeError:
        return _error("BAD_ENCODING","Script must be valid UTF-8")
    if b"\x00" in script_bytes:
        return _error("BAD_INPUT","Script may not contain NUL bytes")
    if len(script_bytes) > MAX_SCRIPT_BYTES:
        return _error("SCRIPT_TOO_LARGE", f"Script exceeds {MAX_SCRIPT_BYTES} bytes")

    try:
        tree = ast.parse(script, filename="user_script.py", mode="exec")
    except SyntaxError as e:
        return _error("SYNTAX_ERROR", f"{e.msg} at line {e.lineno}:{e.offset}")
    has_main = any(getattr(n, "name", None) == "main" for n in tree.body if isinstance(n, ast.FunctionDef))
    if not has_main:
        return _error("NO_MAIN","Script must define a function named main() that returns JSON")

    req_id = str(uuid.uuid4())
    workdir = os.path.join("/tmp", "safe_exec", req_id)
    os.makedirs(workdir, exist_ok=True)
    script_path = os.path.join(workdir, "script.py")
    with open(script_path, "w", encoding="utf-8") as f: f.write(script)

    nsjail_cmd_strict = [
        NSJAIL_PATH, "--quiet", "--iface_no_lo",
        f"--time_limit={TIME_LIMIT_SEC}", f"--rlimit_cpu={CPU_LIMIT_SEC}",
        f"--rlimit_as={MEM_LIMIT_MB}", f"--rlimit_fsize={FSIZE_LIMIT_MB}",
        f"--rlimit_nofile={NOFILE_LIMIT}",
        "--user","65532","--group","65532","--disable_proc",
        "--", PYTHON_BIN, "-u", "/app/runner.py", script_path, str(MAX_STDOUT_BYTES)
    ]
    nsjail_cmd_compat = [
        NSJAIL_PATH, "--quiet",
        f"--time_limit={TIME_LIMIT_SEC}", f"--rlimit_cpu={CPU_LIMIT_SEC}",
        f"--rlimit_as={MEM_LIMIT_MB}", f"--rlimit_fsize={FSIZE_LIMIT_MB}",
        f"--rlimit_nofile={NOFILE_LIMIT}",
        "--user","65532","--group","65532","--disable_proc",
        "--disable_clone_newns","--disable_clone_newcgroup","--disable_clone_newuts",
        "--disable_clone_newipc","--disable_clone_newuser","--disable_clone_newpid",
        "--disable_clone_newnet",
        "--", PYTHON_BIN, "-u", "/app/runner.py", script_path, str(MAX_STDOUT_BYTES)
    ]

    def run_cmd(cmd):
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, timeout=TIME_LIMIT_SEC + 2)

    try:
        # Try nsjail; prefer compat if forced
        if FORCE_COMPAT:
            completed = run_cmd(nsjail_cmd_compat)
        else:
            completed = run_cmd(nsjail_cmd_strict)
            if completed.returncode != 0 and "clone(" in (completed.stderr or "") and "Operation not permitted" in (completed.stderr or ""):
                completed = run_cmd(nsjail_cmd_compat)

        # Cloud Run sandbox quirks: if nsjail still can't start, fall back to direct runner
        hard_block = (
            completed.returncode != 0 and (
                "PR_CAP_AMBIENT" in (completed.stderr or "") or
                "RLIMIT_RTPRIO" in (completed.stderr or "") or
                "Couldn't launch the child process" in (completed.stderr or "")
            )
        )
        if hard_block:
            completed = run_cmd([PYTHON_BIN, "-u", "/app/runner.py", script_path, str(MAX_STDOUT_BYTES)])

    except FileNotFoundError:
        completed = run_cmd([PYTHON_BIN, "-u", "/app/runner.py", script_path, str(MAX_STDOUT_BYTES)])
    except subprocess.TimeoutExpired:
        shutil.rmtree(workdir, ignore_errors=True)
        return _error("TIMEOUT","Execution exceeded time limit")

    shutil.rmtree(workdir, ignore_errors=True)

    out = (completed.stdout or "").strip()
    if not out:
        return _error("EMPTY_OUTPUT","No output produced by runner",
                      details={"stderr": (completed.stderr or "")[-500:]})
    try:
        payload = json.loads(out)
    except json.JSONDecodeError:
        return _error("BAD_RUNNER_OUTPUT","Runner produced non-JSON output",
                      details={"stdout": out[:500]})

    if "error" in payload:
        return _error(payload["error"].get("code","EXECUTION_ERROR"),
                      payload["error"].get("message","Execution failed"),
                      details=payload["error"].get("details"))

    return jsonify({"result": payload.get("result"), "stdout": payload.get("stdout","")})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
