"""Compare prompt versions for the question classification router."""

import asyncio
import hashlib
import json
from collections import Counter
from pathlib import Path

from peptalk.config import get_settings
from peptalk.db.llm_calls import record_call
from peptalk.llm.classify import accuracy, classify, find_leaks
from peptalk.llm.gateway import build_gateway
from peptalk.llm.prompts import list_prompt_files

CACHE_DIR = Path("eval/cache")


def get_cache_path(prompt_text: str, question: str) -> Path:
    key = hashlib.sha256(f"{prompt_text}\n---\n{question}".encode()).hexdigest()
    return CACHE_DIR / f"{key}.json"


async def main() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    gateway = build_gateway(settings, recorder=record_call)

    testset_path = Path("eval/prompt_testset.jsonl")
    if not testset_path.is_file():
        print(f"Error: {testset_path} not found")
        return

    testset = [
        json.loads(line)
        for line in testset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    questions = [row["question"] for row in testset]

    prompt_files = list_prompt_files("classify", prompts_dir="prompts")
    if not prompt_files:
        print("No classify prompts found.")
        return

    print(f"Loaded {len(testset)} test questions.\n")
    results_summary = []

    for _num, ver, path in prompt_files:
        prompt_text = path.read_text(encoding="utf-8")
        if "TODO" in prompt_text:
            print(f"skipped {path.name}: the file still contains TODO")
            continue

        leaks = find_leaks(prompt_text, questions)
        if leaks:
            print(f"LEAK in {path.name}: {leaks}")
            continue

        print(f"Evaluating {ver} ({path.name})...")
        rows = []
        total_tokens_in = 0
        total_tokens_out = 0
        total_cost = 0.0
        cached_count = 0

        for row in testset:
            q = row["question"]
            wanted = row["label"]
            cache_file = get_cache_path(prompt_text, q)

            if cache_file.is_file():
                cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
                got = cached_data["got"]
                tokens_in = cached_data.get("tokens_in", 0)
                tokens_out = cached_data.get("tokens_out", 0)
                cost = cached_data.get("cost_inr", 0.0)
                cached_count += 1
            else:
                got, res = await classify(gateway, prompt_text, ver, q)
                tokens_in = res.tokens_in
                tokens_out = res.tokens_out
                cost = res.cost_inr
                cache_file.write_text(
                    json.dumps(
                        {
                            "got": got,
                            "tokens_in": tokens_in,
                            "tokens_out": tokens_out,
                            "cost_inr": cost,
                            "model": res.model,
                        }
                    ),
                    encoding="utf-8",
                )
                await asyncio.sleep(0.5)

            rows.append({"label": wanted, "got": got, "question": q})
            total_tokens_in += tokens_in
            total_tokens_out += tokens_out
            total_cost += cost

        acc = accuracy(rows)
        score_str = f"{sum(r['got'] == r['label'] for r in rows)}/{len(rows)}"
        avg_tin = round(total_tokens_in / len(rows), 1)
        avg_tout = round(total_tokens_out / len(rows), 1)

        confusion = Counter(f"{r['label']} -> {r['got']}" for r in rows if r["label"] != r["got"])

        results_summary.append(
            {
                "version": ver,
                "filename": path.name,
                "score": score_str,
                "accuracy": acc,
                "avg_tin": avg_tin,
                "avg_tout": avg_tout,
                "total_cost": total_cost,
                "cached": cached_count,
                "confusion": confusion,
                "rows": rows,
            }
        )

    print("\n" + "=" * 70)
    header = (
        f"{'Version':<10} | {'Score':<8} | {'Accuracy':<10} | "
        f"{'Avg In':<8} | {'Avg Out':<8} | {'Cost (INR)':<10}"
    )
    print(header)
    print("-" * 70)
    for res in results_summary:
        pct = f"{res['accuracy'] * 100:>7.1f}%"
        row_str = (
            f"{res['version']:<10} | {res['score']:<8} | {pct} | "
            f"{res['avg_tin']:<8} | {res['avg_tout']:<8} | Rs {res['total_cost']:.4f}"
        )
        print(row_str)
    print("=" * 70)

    for res in results_summary:
        if res["confusion"]:
            print(f"\nMisses in {res['version']}:")
            for pattern, count in res["confusion"].items():
                print(f"  • {pattern}: {count}")
            for idx, r in enumerate(res["rows"], 1):
                if r["label"] != r["got"]:
                    q_trunc = r["question"][:40]
                    print(
                        f"    Line {idx}: wanted '{r['label']}', got '{r['got']}' | \"{q_trunc}\""
                    )


if __name__ == "__main__":
    asyncio.run(main())
