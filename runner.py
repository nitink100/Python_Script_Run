import importlib.util
import io
import json
import os
import sys
import traceback
from contextlib import redirect_stdout
from types import ModuleType

def jsonable(obj):
    try:
        json.dumps(obj)
        return True
    except Exception:
        return False

def load_module_from_path(path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location("user_script", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load script")
    mod = importlib.util.module_from_spec(spec)
    # Ensure module cannot easily resolve relative imports from arbitrary CWD
    mod.__package__ = None
    sys.modules["user_script"] = mod
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": {"code": "BAD_INVOCATION", "message": "Usage: runner.py <script_path> <stdout_cap>"}}))
        return 2

    script_path = sys.argv[1]
    try:
        stdout_cap = int(sys.argv[2])
    except Exception:
        stdout_cap = 200 * 1024

    try:
        mod = load_module_from_path(script_path)
    except Exception as e:
        print(json.dumps({"error": {"code": "IMPORT_ERROR", "message": str(e)}}))
        return 1

    if not hasattr(mod, "main"):
        print(json.dumps({"error": {"code": "NO_MAIN", "message": "Function main() not found"}}))
        return 1

    user_main = getattr(mod, "main")
    if not callable(user_main):
        print(json.dumps({"error": {"code": "INVALID_MAIN", "message": "main is not callable"}}))
        return 1

    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            result = user_main()
    except Exception as e:
        tb = traceback.format_exc(limit=3)
        print(json.dumps({"error": {"code": "EXCEPTION", "message": str(e), "details": {"trace": tb}}}))
        return 1

    stdout_str = buf.getvalue()
    if len(stdout_str) > stdout_cap:
        stdout_str = stdout_str[:stdout_cap] + "\n...<truncated>..."

    if not jsonable(result):
        print(json.dumps({"error": {"code": "NON_JSON_RETURN", "message": "main() must return JSON-serializable value"}}))
        return 1

    payload = {"result": result, "stdout": stdout_str}
    # Emit exactly one JSON line for the parent to parse
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()
    return 0

if __name__ == "__main__":
    rc = main()
    sys.exit(rc)