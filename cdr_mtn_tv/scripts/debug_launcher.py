"""Launch 3 Flask subprocesses for Windows/local debug mode."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "web" / "app.py"
PYTHON = sys.executable


def main():
    roles = [
        ("editor", "9000"),
        ("tv1", "9001"),
        ("tv2", "9002"),
    ]
    processes = []
    env_base = os.environ.copy()

    print("Starting cdr_mtn_tv debug mode (3 subprocesses, no threads)...")
    for role, port in roles:
        env = env_base.copy()
        env["CDR_ROLE"] = role
        cmd = [PYTHON, str(APP), "--role", role, "--host", "127.0.0.1", "--port", port]
        print(f"  {role}: http://127.0.0.1:{port}")
        proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env)
        processes.append(proc)

    print("\nOpen in browser:")
    print("  Editor:  http://127.0.0.1:9000/")
    print("  TV1:     http://127.0.0.1:9001/tv1")
    print("  TV2:     http://127.0.0.1:9002/tv2")
    print("\nPress Ctrl+C to stop.")

    try:
        for proc in processes:
            proc.wait()
    except KeyboardInterrupt:
        print("\nStopping...")
        for proc in processes:
            proc.terminate()
        for proc in processes:
            proc.wait()


if __name__ == "__main__":
    main()
