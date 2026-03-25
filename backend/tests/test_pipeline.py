"""End-to-end pipeline tests with stubbed LLM and storage."""

import pytest
from app.pipeline.orchestrator import run_pipeline

from tests.conftest import StubLLMClient, StubStorage


@pytest.mark.asyncio
async def test_pipeline_runs_end_to_end(
    sample_messages: list[dict[str, object]],
    stub_llm: StubLLMClient,
    stub_storage: StubStorage,
) -> None:
    result = await run_pipeline(sample_messages, llm=stub_llm, storage=stub_storage)

    assert result.messages_processed == 20
    assert len(result.threads) > 0
    assert len(result.classifications) > 0
    assert len(result.briefing) > 0


@pytest.mark.asyncio
async def test_pipeline_classifies_all_categories(
    sample_messages: list[dict[str, object]],
    stub_llm: StubLLMClient,
    stub_storage: StubStorage,
) -> None:
    result = await run_pipeline(sample_messages, llm=stub_llm, storage=stub_storage)

    categories = {c.category.value for c in result.classifications}
    assert "decide" in categories
    assert "delegate" in categories
    assert "ignore" in categories


@pytest.mark.asyncio
async def test_pipeline_detects_phishing(
    sample_messages: list[dict[str, object]],
    stub_llm: StubLLMClient,
    stub_storage: StubStorage,
) -> None:
    result = await run_pipeline(sample_messages, llm=stub_llm, storage=stub_storage)

    flag_types = {f.type.value for f in result.flags}
    assert "phishing" in flag_types


@pytest.mark.asyncio
async def test_pipeline_has_specific_delegations(
    sample_messages: list[dict[str, object]],
    stub_llm: StubLLMClient,
    stub_storage: StubStorage,
) -> None:
    result = await run_pipeline(sample_messages, llm=stub_llm, storage=stub_storage)

    delegated = [c for c in result.classifications if c.category.value == "delegate"]
    for d in delegated:
        assert d.delegate_to is not None
        assert len(d.delegate_to.name) > 0


@pytest.mark.asyncio
async def test_pipeline_generates_drafts(
    sample_messages: list[dict[str, object]],
    stub_llm: StubLLMClient,
    stub_storage: StubStorage,
) -> None:
    result = await run_pipeline(sample_messages, llm=stub_llm, storage=stub_storage)

    assert len(result.drafts) > 0
    for draft in result.drafts:
        assert len(draft.draft_response) > 0
        assert draft.channel.value in ("email", "slack", "whatsapp")


@pytest.mark.asyncio
async def test_pipeline_persists_people(
    sample_messages: list[dict[str, object]],
    stub_llm: StubLLMClient,
    stub_storage: StubStorage,
) -> None:
    await run_pipeline(sample_messages, llm=stub_llm, storage=stub_storage)

    assert len(stub_storage.people) > 0


@pytest.mark.asyncio
async def test_pipeline_calls_all_stages(
    sample_messages: list[dict[str, object]],
    stub_llm: StubLLMClient,
    stub_storage: StubStorage,
) -> None:
    await run_pipeline(sample_messages, llm=stub_llm, storage=stub_storage)

    tool_names = [c["tool"] for c in stub_llm.calls]
    assert "submit_threads" in tool_names
    assert "submit_extraction" in tool_names
    assert "submit_classifications" in tool_names
    assert "submit_drafts" in tool_names
    assert "submit_verification" in tool_names
    assert "submit_briefing" in tool_names


@pytest.mark.asyncio
async def test_pipeline_extraction_before_classification(
    sample_messages: list[dict[str, object]],
    stub_llm: StubLLMClient,
    stub_storage: StubStorage,
) -> None:
    """Extraction stage must run before classification."""
    await run_pipeline(sample_messages, llm=stub_llm, storage=stub_storage)

    tool_names = [c["tool"] for c in stub_llm.calls]
    extract_idx = tool_names.index("submit_extraction")
    classify_idx = tool_names.index("submit_classifications")
    assert extract_idx < classify_idx
