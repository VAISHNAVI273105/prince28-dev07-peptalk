"""CLI utility to inspect queue health and status distribution."""

import argparse
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Inspect live ingestion queue health and stats.")
    parser.add_argument(
        "--url",
        type=str,
        default=os.getenv("API_URL", "http://localhost:8000"),
        help="Base API URL",
    )
    args = parser.parse_args()
    base_url = args.url.rstrip("/")

    client = httpx.Client(timeout=10.0)
    try:
        resp = client.get(f"{base_url}/v1/ingest/stats")
        resp.raise_for_status()
        stats = resp.json()
    except Exception as exc:
        print(f"Error fetching stats from {base_url}: {exc}", file=sys.stderr)
        sys.exit(1)

    counts = stats.get("counts", {})
    healthy = stats.get("queue_healthy", False)
    health_badge = "[OK] HEALTHY" if healthy else "[ALERT] LAGGING"
    age = stats.get("oldest_queued_age_seconds")
    age_str = f"{age:.1f}s" if age is not None else "None (idle)"

    print("\n" + "=" * 45)
    print(f"  PEPTalk Ingestion Queue Health: {health_badge}")
    print("=" * 45)
    print(f"  Total Batch Items:      {stats.get('total_items', 0)}")
    print(f"  Oldest Queued Item Age: {age_str}")
    print("-" * 45)
    print(f"  Queued:   {counts.get('queued', 0):>5}")
    print(f"  Running:  {counts.get('running', 0):>5}")
    print(f"  Done:     {counts.get('done', 0):>5}")
    print(f"  Skipped:  {counts.get('skipped', 0):>5}")
    print(f"  Failed:   {counts.get('failed', 0):>5}")
    print("=" * 45 + "\n")


if __name__ == "__main__":
    main()
