"""Unit tests for ingest worker planning, pacing, and file resolution."""

from pathlib import Path

import pytest

from peptalk.ingest.store import document_id
from peptalk.workers.ingest import Pace, Permanent, get_file, plan, raw_url


def test_plan_filters_downloaded_and_avoids_duplicates():
    records = [
        {"sha256": "abc1", "status": "downloaded", "source": "pep"},
        {"sha256": "abc1", "status": "downloaded", "source": "pep"},  # duplicate sha
        {"sha256": "abc2", "status": "downloaded", "source": "pep"},
        {"sha256": "abc3", "status": "failed", "source": "pep"},  # not downloaded
    ]
    done_ids = {document_id("abc1")}  # already ingested
    planned = plan(records, done_ids)
    assert len(planned) == 1
    assert planned[0]["sha256"] == "abc2"


def test_plan_source_filter_and_limit():
    records = [
        {"sha256": "a1", "status": "downloaded", "source": "pep"},
        {"sha256": "a2", "status": "downloaded", "source": "whatsnew"},
        {"sha256": "a3", "status": "downloaded", "source": "pep"},
    ]
    planned = plan(records, set(), source="pep", limit=1)
    assert len(planned) == 1
    assert planned[0]["sha256"] == "a1"


def test_raw_url_github_blob_conversion():
    record = {
        "url": "https://github.com/python/peps/blob/main/peps/pep-0634.rst",
        "via": "git",
        "commit": "3b2c89b3",
    }
    url = raw_url(record)
    assert url == "https://raw.githubusercontent.com/python/peps/3b2c89b3/peps/pep-0634.rst"


def test_raw_url_non_git_or_unmatched_stays_same():
    record = {"url": "https://docs.python.org/3/whatsnew/3.13.html", "via": "http"}
    assert raw_url(record) == "https://docs.python.org/3/whatsnew/3.13.html"


@pytest.mark.asyncio
async def test_pace_rate_limiting():
    current_time = 0.0

    def mock_clock():
        nonlocal current_time
        return current_time

    async def mock_sleep(d):
        nonlocal current_time
        current_time += d

    pace = Pace(per_minute=12.0, clock=mock_clock, sleep=mock_sleep)  # 5s gap
    await pace.wait()
    assert current_time == 0.0  # first is immediate
    await pace.wait()
    assert current_time == 5.0  # second sleeps 5s


@pytest.mark.asyncio
async def test_get_file_local_exists_and_manual_raises_permanent(tmp_path: Path):
    local_file = tmp_path / "test.txt"
    local_file.write_text("content", encoding="utf-8")

    rec_existing = {"path": str(local_file)}
    res = await get_file(rec_existing, tmp_path, None)  # type: ignore[arg-type]
    assert res == local_file

    rec_manual = {"path": str(tmp_path / "missing.txt"), "via": "manual"}
    with pytest.raises(Permanent, match="downloaded by hand"):
        await get_file(rec_manual, tmp_path, None)  # type: ignore[arg-type]
