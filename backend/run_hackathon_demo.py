"""
Run server + webcam monitor (+ optional teacher dashboard) together.

Example:
    python backend/run_hackathon_demo.py --student-id student_01 --enable-phone-detection
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


def spawn(cmd: list[str], cwd: Path) -> subprocess.Popen:
    return subprocess.Popen(cmd, cwd=str(cwd))


def main() -> int:
    parser = argparse.ArgumentParser(description="Hackathon demo launcher")
    parser.add_argument("--student-id", required=True, help="Student id for webcam monitor")
    parser.add_argument("--host", default="127.0.0.1", help="FastAPI host")
    parser.add_argument("--port", type=int, default=8000, help="FastAPI port")
    parser.add_argument("--camera-index", type=int, default=-1, help="Webcam index (-1 = auto)")
    parser.add_argument("--cooldown", type=float, default=8.0, help="Seconds between same alerts")
    parser.add_argument("--enable-phone-detection", action="store_true", help="Enable YOLO phone detection")
    parser.add_argument("--with-dashboard", action="store_true", help="Open teacher terminal dashboard process")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    python_exe = sys.executable
    server_url = f"http://{args.host}:{args.port}"

    server_cmd = [
        python_exe,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    webcam_cmd = [
        python_exe,
        "backend/webcam_monitor.py",
        "--student-id",
        args.student_id,
        "--server-url",
        server_url,
        "--camera-index",
        str(args.camera_index),
        "--cooldown",
        str(args.cooldown),
    ]
    if args.enable_phone_detection:
        webcam_cmd.append("--enable-phone-detection")

    dashboard_cmd = [python_exe, "backend/teacher_ws_dashboard.py"]

    processes: list[subprocess.Popen] = []
    process_names: dict[int, str] = {}
    critical_pids: set[int] = set()
    try:
        print(f"Starting server on {server_url} ...")
        server_proc = spawn(server_cmd, root)
        processes.append(server_proc)
        process_names[server_proc.pid] = "server"
        critical_pids.add(server_proc.pid)
        time.sleep(2.0)

        print("Starting webcam monitor ...")
        webcam_proc = spawn(webcam_cmd, root)
        processes.append(webcam_proc)
        process_names[webcam_proc.pid] = "webcam_monitor"

        if args.with_dashboard:
            print("Starting teacher dashboard ...")
            dashboard_proc = spawn(dashboard_cmd, root)
            processes.append(dashboard_proc)
            process_names[dashboard_proc.pid] = "teacher_dashboard"

        print("Demo is running. Press Ctrl+C to stop all processes.")
        while True:
            time.sleep(1)
            for proc in processes:
                code = proc.poll()
                if code is not None and code != 0:
                    name = process_names.get(proc.pid, f"pid={proc.pid}")
                    if proc.pid in critical_pids:
                        print(f"Critical process '{name}' exited with code {code}. Stopping all.")
                        return code
                    print(f"Warning: process '{name}' exited with code {code}. Continuing.")
                    processes = [p for p in processes if p.pid != proc.pid]
                    break

    except KeyboardInterrupt:
        print("\nStopping all processes ...")
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            if proc.poll() is None:
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
