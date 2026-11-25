"""Say hello to each provider with one raw HTTP call, no gateway in between."""

import time

import httpx

from peptalk.config import get_settings


def ping_provider(name: str, base_url: str, key: str, model: str) -> None:
    if not key:
        print(f"{name} NO KEY")
        return
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {key}"}
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 10,
    }
    start = time.perf_counter()
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, headers=headers, json=body)
        latency_ms = int((time.perf_counter() - start) * 1000)
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            usage = data.get("usage", {})
            tin = usage.get("prompt_tokens", 0)
            tout = usage.get("completion_tokens", 0)
            print(
                f"{name} OK {model} said '{content}' in {latency_ms} ms, tokens in={tin} out={tout}"
            )
        else:
            print(f"{name} FAILED HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        print(f"{name} FAILED: {exc}")


def main() -> None:
    s = get_settings()
    ping_provider("gemini", s.llm_primary_base_url, s.gemini_api_key, s.llm_primary_model)
    ping_provider("groq", s.llm_fallback_base_url, s.groq_api_key, s.llm_fallback_model)


if __name__ == "__main__":
    main()
