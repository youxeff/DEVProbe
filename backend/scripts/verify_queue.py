"""Real Redis + separate Celery worker + Uvicorn; mocked providers, real persistence.

Run from backend with REDIS_SERVER=/path/to/redis-server python scripts/verify_queue.py.
"""

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from celery import Celery


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    backend = Path(__file__).resolve().parents[1]
    binary = os.getenv("REDIS_SERVER") or shutil.which("redis-server")
    if not binary:
        raise SystemExit("Set REDIS_SERVER to a Redis server executable.")
    processes = []
    with tempfile.TemporaryDirectory(prefix="devprobe-queue-test-") as temporary:
        path = Path(temporary)
        redis_port, api_port = free_port(), free_port()
        broker = f"redis://127.0.0.1:{redis_port}/0"
        env = {
            **os.environ,
            "DATABASE_URL": f"sqlite:///{path / 'queue.db'}",
            "REDIS_URL": broker,
            "SCAN_MODE": "async",
            "EXTERNAL_ANALYZERS": "",
            "PYTHONPATH": str(backend),
        }
        with (path / "process.log").open("w+") as log:
            try:
                subprocess.run(
                    [sys.executable, "-m", "alembic", "upgrade", "head"],
                    cwd=backend,
                    env=env,
                    check=True,
                )
                commands = [
                    [
                        binary,
                        "--bind",
                        "127.0.0.1",
                        "--port",
                        str(redis_port),
                        "--save",
                        "",
                        "--appendonly",
                        "no",
                        "--dir",
                        str(path),
                    ],
                    [
                        sys.executable,
                        "-m",
                        "celery",
                        "-A",
                        "tests.worker_fixture:celery_app",
                        "worker",
                        "--pool=solo",
                        "--concurrency=1",
                        "--loglevel=WARNING",
                    ],
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "tests.e2e_server:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(api_port),
                    ],
                ]
                for command in commands:
                    processes.append(
                        subprocess.Popen(command, cwd=backend, env=env, stdout=log, stderr=log)
                    )
                base = f"http://127.0.0.1:{api_port}"
                with httpx.Client(timeout=10, trust_env=False) as client:
                    for _ in range(60):
                        try:
                            if client.get(base + "/health").status_code == 200:
                                break
                        except httpx.TransportError:
                            pass
                        time.sleep(0.2)
                    response = client.post(
                        base + "/scans",
                        json={
                            "repo_url": "https://github.com/devprobe-fixtures/review-lab",
                            "pr_number": 12,
                        },
                    )
                    response.raise_for_status()
                    assert response.json()["status"] == "pending", response.text
                    scan_id = response.json()["scan_id"]
                    for _ in range(100):
                        saved = client.get(base + f"/scans/{scan_id}").json()
                        if saved["status"] in ("completed", "failed"):
                            break
                        time.sleep(0.2)
                    assert saved["status"] == "completed", saved
                    assert saved["risk_score"] == 16 and saved["total_issues"] == 4, saved
                    Celery(broker=broker).send_task("devprobe.scan", args=[scan_id])
                    time.sleep(0.5)
                    again = client.get(base + f"/scans/{scan_id}").json()
                    assert again["started_at"] == saved["started_at"]
                    print(
                        "PASS: API → Redis → worker → SQL scan; duplicate delivery retained result."
                    )
            except Exception:
                log.flush()
                log.seek(0)
                print(log.read()[-6000:])
                raise
            finally:
                for process in reversed(processes):
                    process.terminate()
                for process in reversed(processes):
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()


if __name__ == "__main__":
    main()
