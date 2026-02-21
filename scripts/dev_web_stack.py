"""Run Chronicle API + Reference UI together for local development.

Usage:
  PYTHONPATH=. ./.venv/bin/python scripts/dev_web_stack.py
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def _terminate(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Chronicle API and frontend dev server together."
    )
    parser.add_argument("--api-host", default="127.0.0.1")
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--ui-host", default="127.0.0.1")
    parser.add_argument("--ui-port", type=int, default=5173)
    parser.add_argument(
        "--project-path",
        default="/tmp/chronicle_dev_project",
        help="CHRONICLE_PROJECT_PATH for the API process.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    frontend_dir = repo_root / "frontend"
    if not frontend_dir.is_dir():
        print("frontend directory not found", file=sys.stderr)
        return 1

    api_env = os.environ.copy()
    api_env["CHRONICLE_PROJECT_PATH"] = str(Path(args.project_path).resolve())
    api_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "chronicle.api.app:app",
        "--host",
        args.api_host,
        "--port",
        str(args.api_port),
        "--reload",
    ]

    ui_env = os.environ.copy()
    ui_env.setdefault("VITE_API_BASE_URL", "/api")
    ui_env.setdefault("VITE_API_DOCS_URL", f"http://{args.api_host}:{args.api_port}/docs")
    ui_cmd = ["npm", "run", "dev", "--", "--host", args.ui_host, "--port", str(args.ui_port)]

    api_proc: subprocess.Popen[bytes] | None = None
    ui_proc: subprocess.Popen[bytes] | None = None
    try:
        print(
            f"[dev-web] API  -> http://{args.api_host}:{args.api_port} (project: {api_env['CHRONICLE_PROJECT_PATH']})"
        )
        print(f"[dev-web] UI   -> http://{args.ui_host}:{args.ui_port}")
        api_proc = subprocess.Popen(api_cmd, cwd=repo_root, env=api_env)
        ui_proc = subprocess.Popen(ui_cmd, cwd=frontend_dir, env=ui_env)

        while True:
            api_code = api_proc.poll()
            ui_code = ui_proc.poll()
            if api_code is not None:
                print(f"[dev-web] API exited with code {api_code}", file=sys.stderr)
                return api_code or 1
            if ui_code is not None:
                print(f"[dev-web] UI exited with code {ui_code}", file=sys.stderr)
                return ui_code or 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[dev-web] stopping...")
        return 0
    finally:
        _terminate(ui_proc)
        _terminate(api_proc)


if __name__ == "__main__":
    raise SystemExit(main())
