"""Explicit live smoke test. Run against a locally running DevProbe API."""

import argparse
import json

import requests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_url")
    parser.add_argument("pr_number", type=int)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = args.api_url.rstrip("/")
    health = requests.get(f"{base}/health", timeout=10)
    health.raise_for_status()
    created = requests.post(
        f"{base}/scans",
        json={"repo_url": args.repo_url, "pr_number": args.pr_number},
        timeout=180,
    )
    if not created.ok:
        print(json.dumps(created.json(), indent=2))
        raise SystemExit(1)
    scan_id = created.json()["scan_id"]
    result = requests.get(f"{base}/scans/{scan_id}", timeout=10)
    result.raise_for_status()
    scan = result.json()
    print(json.dumps(scan, indent=2))
    if scan["status"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
