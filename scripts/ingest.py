"""CLI client to start and monitor an ingestion job via the PEPTalk API."""

import argparse
import os
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Start an ingestion job and monitor progress.")
    parser.add_argument("--limit", type=int, default=20, help="Number of documents to queue")
    parser.add_argument(
        "--source", type=str, default="", help="Only ingest documents from this source"
    )
    parser.add_argument(
        "--retry-failed", action="store_true", help="Retry failed items from dead letter"
    )
    parser.add_argument(
        "--url",
        type=str,
        default=os.getenv("API_URL", "http://localhost:8000"),
        help="Base API URL",
    )
    parser.add_argument(
        "--token", type=str, default=os.getenv("ADMIN_TOKEN", ""), help="X-Admin-Token value"
    )
    args = parser.parse_args()

    url = args.url.rstrip("/")
    headers = {"X-Admin-Token": args.token} if args.token else {}

    client = httpx.Client(timeout=30.0)

    try:
        resp = client.post(
            f"{url}/v1/ingest",
            headers=headers,
            json={
                "limit": args.limit,
                "source": args.source,
                "retry_failed": args.retry_failed,
            },
        )
    except httpx.RequestError as exc:
        print(f"Error connecting to API: {exc}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code == 200:
        data = resp.json()
        print(data.get("detail", "Nothing to do: all of it is ingested."))
        sys.exit(0)

    if resp.status_code != 202:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    job_id = data["job_id"]
    queued = data["queued"]
    print(f"HTTP 202: job {job_id}, {queued} queued")

    started = time.monotonic()
    last_line = ""

    while True:
        time.sleep(2)
        try:
            p_resp = client.get(f"{url}/v1/ingest/{job_id}")
            if p_resp.status_code != 200:
                print(
                    f"Error polling progress: {p_resp.status_code} {p_resp.text}", file=sys.stderr
                )
                time.sleep(2)
                continue
            prog = p_resp.json()
        except httpx.RequestError as exc:
            print(f"Warning: polling failed: {exc}", file=sys.stderr)
            time.sleep(2)
            continue

        elapsed = int(time.monotonic() - started)
        q = prog.get("queued", 0)
        r = prog.get("running", 0)
        d = prog.get("done", 0)
        s = prog.get("skipped", 0)
        f = prog.get("failed", 0)
        p = prog.get("pages", 0)

        line = f"queued={q} running={r} done={d} skipped={s} failed={f} pages={p} {elapsed}s"
        if q == 0 and r == 0:
            print(f"finished {line}")
            if f > 0:
                try:
                    dl_resp = client.get(f"{url}/v1/ingest/dead-letter")
                    if dl_resp.status_code == 200:
                        dead_items = dl_resp.json().get("items", [])
                        for item in dead_items:
                            if item.get("job_id") == job_id:
                                path = item.get("path", "")
                                tries = item.get("attempts", 1)
                                err = item.get("error", "")
                                print(f"FAILED   {path} ({tries} try) {err}")
                except Exception:
                    pass
            break
        else:
            if line != last_line:
                print(f"working  {line}")
                last_line = line


if __name__ == "__main__":
    main()
