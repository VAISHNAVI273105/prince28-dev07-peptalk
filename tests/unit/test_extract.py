"""Unit tests for metadata extraction, parsing, validation, and contract consistency."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from peptalk.llm.doc_meta import DocMeta
from peptalk.llm.extract import explain, extract, parse_json
from peptalk.llm.gateway import FakeLLM, LLMGateway

SAMPLE_VALID_RECORD = {
    "doc_kind": "guideline",
    "year": 2024,
    "language": "en",
    "summary": "This document specifies modern coding standards for modern Python applications.",
    "topics": ["style", "pep8"],
    "pep_number": ["8"],
    "status": ["Active"],
    "type": ["Process"],
    "python_version": ["3.13"],
    "created": ["2001-07-05"],
}


# 1. parse_json valid JSON
def test_parse_json_valid():
    raw = '{"doc_kind": "rule", "year": 2023}'
    res = parse_json(raw)
    assert res == {"doc_kind": "rule", "year": 2023}


# 2. parse_json markdown fenced and outer noise
def test_parse_json_fenced():
    raw = (
        "Here is the extraction:\n"
        '```json\n{"summary": "Sample summary text", "year": 2022}\n```\n'
        "Done."
    )
    res = parse_json(raw)
    assert res == {"summary": "Sample summary text", "year": 2022}


# 3. parse_json invalid or non-object raises ValueError
def test_parse_json_invalid_raises():
    with pytest.raises(ValueError, match="contains no JSON object"):
        parse_json("No JSON at all here")

    with pytest.raises(ValueError):
        parse_json("Malformed JSON {not_valid: json}")


# 4. explain format
def test_explain_validation_error():
    try:
        DocMeta.model_validate({"doc_kind": "not_a_valid_kind"})
    except ValidationError as err:
        msg = explain(err)
        assert "doc_kind" in msg
        assert len(msg) > 5

    assert explain(ValueError("Custom error")) == "Custom error"


# 5. extract happy path
@pytest.mark.asyncio
async def test_extract_happy_path():
    fake = FakeLLM("fake", "fake-1", [json.dumps(SAMPLE_VALID_RECORD)])
    gateway = LLMGateway([fake])

    res = await extract(
        gateway=gateway,
        schema=DocMeta,
        prompt="Extract prompt",
        version="v1",
        title="PEP 8",
        text="Style Guide for Python Code",
    )

    assert res.record is not None
    assert isinstance(res.record, DocMeta)
    assert res.record.doc_kind == "guideline"
    assert res.record.pep_number == ["8"]
    assert res.attempts == 1
    assert res.errors == []


# 6. extract validation repair loop
@pytest.mark.asyncio
async def test_extract_repair_loop():
    # Attempt 1: invalid doc_kind, Attempt 2: corrected
    invalid = dict(SAMPLE_VALID_RECORD, doc_kind="invalid_kind")
    fake = FakeLLM("fake", "fake-1", [json.dumps(invalid), json.dumps(SAMPLE_VALID_RECORD)])
    gateway = LLMGateway([fake])

    res = await extract(
        gateway=gateway,
        schema=DocMeta,
        prompt="Extract prompt",
        version="v1",
        title="PEP 8",
        text="Style Guide for Python Code",
    )

    assert res.record is not None
    assert res.record.doc_kind == "guideline"
    assert res.attempts == 2
    assert len(res.errors) == 1
    assert "doc_kind" in res.errors[0]


# 7. extract exhausts retries returns None
@pytest.mark.asyncio
async def test_extract_exhausts_retries_returns_none():
    invalid = dict(SAMPLE_VALID_RECORD, doc_kind="bad_kind")
    fake = FakeLLM(
        "fake",
        "fake-1",
        [json.dumps(invalid), json.dumps(invalid), json.dumps(invalid)],
    )
    gateway = LLMGateway([fake])

    res = await extract(
        gateway=gateway,
        schema=DocMeta,
        prompt="Extract prompt",
        version="v1",
        title="PEP 8",
        text="Style Guide for Python Code",
        max_attempts=3,
    )

    assert res.record is None
    assert res.attempts == 3
    assert len(res.errors) == 3


# 8. DocMeta strict contract & prompt consistency
def test_doc_meta_contract_and_prompt_consistency():
    # Contract checks
    assert DocMeta.model_config.get("extra") == "forbid"
    common_fields = {"doc_kind", "year", "language", "summary", "topics"}
    assert common_fields.issubset(set(DocMeta.model_fields))

    # Tidy validator check
    tidied = DocMeta._tidy(["Python", "python", "Style", "style"])
    assert tidied == ["python", "style"]

    # Prompt consistency check
    prompt_path = Path("prompts/extract_v1.md")
    assert prompt_path.is_file(), "prompts/extract_v1.md must exist"
    prompt_text = prompt_path.read_text(encoding="utf-8")

    missing_fields = [
        field_name for field_name in DocMeta.model_fields if f"- {field_name}:" not in prompt_text
    ]
    assert not missing_fields, f"prompts/extract_v1.md does not mention: {missing_fields}"


# 9. Hallucination guardrail: invented year not in document text is rejected
@pytest.mark.asyncio
async def test_extract_rejects_hallucinated_year():
    # Attempt 1: valid DocMeta JSON but year 2024 does not exist anywhere in text (hallucinated)
    # Attempt 2: corrected with year=None or year 1999 (which is in the text)
    invented = dict(SAMPLE_VALID_RECORD, year=2024)
    corrected = dict(SAMPLE_VALID_RECORD, year=1999)
    fake = FakeLLM("fake", "fake-1", [json.dumps(invented), json.dumps(corrected)])
    gateway = LLMGateway([fake])

    text_without_2024 = "Published in 1999. Python standards and guidelines."
    res = await extract(
        gateway=gateway,
        schema=DocMeta,
        prompt="Extract prompt",
        version="v1",
        title="Python Doc",
        text=text_without_2024,
    )

    assert res.record is not None
    assert res.record.year == 1999
    assert res.attempts == 2
    assert len(res.errors) == 1
    assert "year 2024 is not in the document" in res.errors[0]
