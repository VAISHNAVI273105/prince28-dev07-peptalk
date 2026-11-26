"""Unit tests for prompt classification router and prompt evaluation tools.

Tests build_messages, parse_label, accuracy, find_leaks, async classify,
and verifies repository prompt templates and eval test sets (7 tests).
"""

import json
from pathlib import Path

import pytest

from peptalk.llm.classify import (
    LABELS,
    accuracy,
    build_messages,
    classify,
    find_leaks,
    parse_label,
)
from peptalk.llm.gateway import FakeLLM, LLMGateway


# 1. build_messages formatting
def test_build_messages():
    prompt = "You are a classifier."
    question = "What is PEP 8?"
    messages = build_messages(prompt, question)

    assert len(messages) == 2
    assert messages[0] == {"role": "system", "content": prompt}
    assert messages[1] == {"role": "user", "content": "<question>\nWhat is PEP 8?\n</question>"}


# 2. parse_label valid inputs
def test_parse_label_valid():
    cases = [
        ("docs", "docs"),
        ("Docs.", "docs"),
        ("DOCS", "docs"),
        ("personal", "personal"),
        ("Personal!", "personal"),
        ("off_topic", "off_topic"),
        ("off-topic", "off_topic"),
        ("off topic", "off_topic"),
        ("Off-Topic.", "off_topic"),
    ]
    for reply, expected in cases:
        assert parse_label(reply) == expected


# 3. parse_label invalid inputs
def test_parse_label_invalid():
    cases = [
        "docs or personal",
        "It could be docs or off_topic",
        "I don't know the answer",
        "",
        "python",
        "invalid_label",
    ]
    for reply in cases:
        assert parse_label(reply) == "invalid"


# 4. accuracy calculation
def test_accuracy():
    assert accuracy([]) == 0.0

    perfect = [{"got": "docs", "label": "docs"}, {"got": "personal", "label": "personal"}]
    assert accuracy(perfect) == 1.0

    mixed = [
        {"got": "docs", "label": "docs"},
        {"got": "personal", "label": "docs"},
        {"got": "off_topic", "label": "off_topic"},
        {"got": "invalid", "label": "personal"},
    ]
    assert accuracy(mixed) == 0.5


# 5. find_leaks detection
def test_find_leaks():
    prompt = "Classify questions. For example: what is pep 8? Answer with docs."
    questions = [
        "What is PEP 8?",
        "What is PEP 634?",
    ]
    leaks = find_leaks(prompt, questions)
    assert leaks == ["What is PEP 8?"]

    clean_prompt = "You are a classifier. Reply with one word."
    assert find_leaks(clean_prompt, questions) == []


# 6. classify async with gateway
@pytest.mark.asyncio
async def test_classify_with_gateway():
    recorded = []

    async def recorder(row: dict) -> None:
        recorded.append(row)

    fake = FakeLLM("fake", "fake-1", ["docs"])
    gateway = LLMGateway([fake], recorder=recorder)

    label, result = await classify(gateway, "System prompt", "v1", "What is PEP 634?")

    assert label == "docs"
    assert result.text == "docs"
    assert len(recorded) == 1
    assert recorded[0]["purpose"] == "classify"
    assert recorded[0]["prompt_version"] == "v1"


# 7. Repo validation: prompt files and test set
def test_repo_has_prompts_and_testset():
    prompts_dir = Path("prompts")
    prompt_files = list(prompts_dir.glob("classify_v*.md"))
    assert len(prompt_files) >= 3, (
        f"Expected at least 3 classify_v*.md files, found {len(prompt_files)}"
    )

    testset_file = Path("eval/prompt_testset.jsonl")
    assert testset_file.is_file(), "eval/prompt_testset.jsonl must exist"

    lines = testset_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 20, f"Expected at least 20 test questions, found {len(lines)}"

    questions = []
    for idx, line in enumerate(lines, 1):
        row = json.loads(line)  # raises JSONDecodeError if invalid JSON
        assert "question" in row, f"Line {idx} missing 'question' field"
        assert "label" in row, f"Line {idx} missing 'label' field"
        assert row["label"] in LABELS, f"Line {idx} has invalid label '{row['label']}'"
        assert "TODO" not in row["question"], f"Line {idx} contains unresolved TODO"
        questions.append(row["question"])

    # Ensure no leaks in classify_v3.md
    v3_path = prompts_dir / "classify_v3.md"
    if v3_path.is_file():
        v3_text = v3_path.read_text(encoding="utf-8")
        leaks = find_leaks(v3_text, questions)
        assert leaks == [], f"classify_v3.md contains testset leaks: {leaks}"
