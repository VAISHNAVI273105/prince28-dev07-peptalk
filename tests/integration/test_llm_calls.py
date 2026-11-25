"""Integration test for LlmCall persistence and UsageRepository against live PostgreSQL."""

import pytest

from peptalk.config import Settings
from peptalk.db.base import Base
from peptalk.db.llm_calls import UsageRepository
from peptalk.db.models import LlmCall
from peptalk.db.session import make_engine, make_sessionmaker


@pytest.fixture
async def session(database_url):
    engine = make_engine(Settings(app_env="ci", database_url=database_url, _env_file=None))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with make_sessionmaker(engine)() as db:
        await db.execute(LlmCall.__table__.delete())
        await db.commit()
        yield db
    await engine.dispose()


async def test_record_and_query_daily_usage(session):
    call = LlmCall(
        request_id="req-test-1",
        provider="gemini",
        model="gemini-3.8-flash",
        purpose="chat",
        prompt_version="chat_system_v1",
        status="ok",
        tokens_in=100,
        tokens_out=50,
        latency_ms=1200,
        cost_inr=0.045,
        fallback_used=False,
    )
    session.add(call)
    await session.commit()

    repo = UsageRepository(session)
    days = await repo.by_day(7)

    assert len(days) >= 1
    today = days[0]
    assert today["calls"] == 1
    assert today["tokens_in"] == 100
    assert today["tokens_out"] == 50
    assert today["cost_inr"] == 0.045
    assert today["fallbacks"] == 0
    assert today["errors"] == 0
