"""Small CLI client for asking PEPTalk questions and timing streaming responses."""

import argparse
import json
import sys
import time

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ask PEPTalk a question via the /v1/chat endpoint."
    )
    parser.add_argument("message", help="The question or prompt to send to PEPTalk")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the PEPTalk server (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Use non-streaming mode and print raw JSON output",
    )
    args = parser.parse_args()

    endpoint = f"{args.url.rstrip('/')}/v1/chat"

    if args.json:
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    endpoint,
                    json={"message": args.message, "stream": False},
                )
            if resp.status_code != 200:
                print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
                sys.exit(1)
            data = resp.json()
            print(data.get("answer", ""))
            provider = data.get("provider", "unknown")
            model = data.get("model", "unknown")
            tokens_in = data.get("tokens_in", 0)
            tokens_out = data.get("tokens_out", 0)
            cost_inr = data.get("cost_inr", 0.0)
            attempts = data.get("attempts", 1)
            fallback = "YES" if data.get("fallback_used") else "no"
            print(
                f"\n--- {provider} / {model}: tokens in={tokens_in} out={tokens_out} "
                f"cost Rs {cost_inr:.6f} attempts={attempts} fallback={fallback}"
            )
        except Exception as exc:
            print(f"ConnectError: is the API running? {exc}", file=sys.stderr)
            sys.exit(1)
        return

    # Streaming mode (SSE)
    start_time = time.perf_counter()
    first_words_time: float | None = None
    summary_data: dict = {}

    try:
        with (
            httpx.Client(timeout=60.0) as client,
            client.stream(
                "POST",
                endpoint,
                json={"message": args.message, "stream": True},
            ) as response,
        ):
            if response.status_code != 200:
                print(
                    f"Error {response.status_code}: {response.read().decode('utf-8')}",
                    file=sys.stderr,
                )
                sys.exit(1)

            current_event = ""
            for line in response.iter_lines():
                if line.startswith("event:"):
                    current_event = line[6:].strip()
                    continue
                if line.startswith("data:"):
                    payload = line[5:].strip()
                    if not payload:
                        continue
                    try:
                        parsed = json.loads(payload)
                    except json.JSONDecodeError:
                        continue

                    if current_event == "done":
                        summary_data = parsed
                        break
                    if current_event == "error":
                        print(
                            f"\n[Error: {parsed.get('detail', 'Unknown error')}]",
                            file=sys.stderr,
                        )
                        break

                    delta = parsed.get("delta", "")
                    if delta:
                        if first_words_time is None:
                            first_words_time = time.perf_counter() - start_time
                        sys.stdout.write(delta)
                        sys.stdout.flush()

        total_time = time.perf_counter() - start_time
        fw_str = f"{first_words_time:.2f} s" if first_words_time is not None else "N/A"
        provider = summary_data.get("provider", "unknown")
        model = summary_data.get("model", "unknown")
        tokens_in = summary_data.get("tokens_in", 0)
        tokens_out = summary_data.get("tokens_out", 0)
        cost_inr = summary_data.get("cost_inr", 0.0)
        attempts = summary_data.get("attempts", 1)
        fallback = "YES" if summary_data.get("fallback_used") else "no"

        print(
            f"\n\n--- {provider} / {model}: first words after {fw_str}, "
            f"total {total_time:.2f} s tokens in={tokens_in} out={tokens_out} "
            f"cost Rs {cost_inr:.6f} attempts={attempts} fallback={fallback}"
        )
    except Exception as exc:
        print(f"\nConnectError: is the API running? {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
