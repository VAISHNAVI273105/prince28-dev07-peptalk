"""Unit tests for prompt loading, listing, and version sorting."""

import pytest

from peptalk.llm.prompts import (
    list_prompt_files,
    list_versions,
    load_prompt,
)


def test_list_prompt_files():
    files = list_prompt_files("classify", prompts_dir="prompts")
    assert len(files) >= 3
    # Check numeric order
    versions = [num for num, _, _ in files]
    assert versions == sorted(versions)


def test_list_versions():
    versions = list_versions("classify", prompts_dir="prompts")
    assert "v1" in versions
    assert "v2" in versions
    assert "v3" in versions
    assert versions[0] == "v1"
    assert versions[1] == "v2"
    assert versions[2] == "v3"


def test_load_prompt_specific_version():
    content_v1, ver1 = load_prompt("classify", "v1", prompts_dir="prompts")
    assert ver1 == "v1"
    assert "Classify the user's question" in content_v1

    content_v2, ver2 = load_prompt("classify", 2, prompts_dir="prompts")
    assert ver2 == "v2"
    assert "question router of PEPTalk" in content_v2


def test_load_prompt_latest_defaults():
    content, ver = load_prompt("classify", prompts_dir="prompts")
    # Latest version is at least v3
    assert ver == "v3"
    assert "Examples:" in content


def test_load_prompt_missing_task_raises():
    with pytest.raises(FileNotFoundError) as exc:
        load_prompt("nonexistent_task_xyz", prompts_dir="prompts")
    assert "No prompt templates found" in str(exc.value)


def test_load_prompt_missing_version_raises():
    with pytest.raises(FileNotFoundError) as exc:
        load_prompt("classify", "v999", prompts_dir="prompts")
    assert "Prompt version 'v999' not found" in str(exc.value)


def test_list_prompt_files_invalid_dir():
    assert list_prompt_files("classify", prompts_dir="nonexistent_dir_12345") == []
