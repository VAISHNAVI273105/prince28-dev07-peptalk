"""Smoke test script for verifying live deployment health and version."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any


def http_get(url: str, timeout: float = 10.0) -> tuple[int, dict[str, Any] | str]:
    """Perform a GET request and return HTTP status code and parsed JSON or raw text."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PEPTalk-SmokeTest/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            body = response.read().decode("utf-8")
            try:
                data = json.loads(body)
                return status, data
            except json.JSONDecodeError:
                return status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            data = json.loads(body)
            return exc.code, data
        except json.JSONDecodeError:
            return exc.code, body
    except Exception as exc:
        return 0, str(exc)


def smoke_test(
    base_url: str,
    expect_version: str | None = None,
    timeout: int = 300,
    interval: int = 5,
) -> bool:
    """Run smoke test suite against target base URL."""
    base = base_url.rstrip("/")
    health_url = f"{base}/health"
    ready_url = f"{base}/ready"
    docs_url = f"{base}/v1/documents?limit=1"

    start_time = time.time()
    health_ok = False
    active_version = None

    # Step 1: Poll /health until ready and version matches if expected
    while time.time() - start_time < timeout:
        status, data = http_get(health_url)
        if status == 200 and isinstance(data, dict):
            active_version = data.get("version")
            if expect_version is None or active_version == expect_version:
                print(f"ok   /health -> 200, version {active_version}")
                health_ok = True
                break
            else:
                print(f"waiting: /health -> 200 {active_version} (waiting for {expect_version})")
        else:
            print(f"waiting: /health -> {status} (service starting)")
        time.sleep(interval)

    if not health_ok:
        print(f"FAIL /health did not match expected version '{expect_version}' within {timeout}s")
        return False

    # Step 2: Test /ready
    status, ready_data = http_get(ready_url)
    if status == 200:
        print(f"ok   /ready -> 200 {ready_data}")
    else:
        print(f"FAIL /ready returned status {status}: {ready_data}")
        return False

    # Step 3: Test /v1/documents?limit=1
    status, docs_data = http_get(docs_url)
    if status == 200:
        print("ok   /v1/documents?limit=1 -> 200")
    else:
        print(f"FAIL /v1/documents?limit=1 returned status {status}: {docs_data}")
        return False

    print("Smoke test passed")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test live PEPTalk deployment.")
    parser.add_argument(
        "url", help="Base URL of the deployment (e.g. https://peptalk.onrender.com)"
    )
    parser.add_argument(
        "--expect-version",
        default=None,
        help="Expected commit SHA or version reported by /health",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Maximum seconds to wait for version rollout (default 300)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Polling interval in seconds (default 5)",
    )

    args = parser.parse_args()
    success = smoke_test(
        base_url=args.url,
        expect_version=args.expect_version,
        timeout=args.timeout,
        interval=args.interval,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
