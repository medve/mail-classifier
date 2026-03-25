"""Functional tests for FastAPI endpoints."""

import asyncio
from unittest.mock import patch

import pytest
from app.server import app
from httpx import ASGITransport, AsyncClient

from tests.conftest import SAMPLE_DATA_PATH, StubLLMClient, StubStorage


@pytest.fixture
def _patch_storage() -> None:
    storage = StubStorage()
    app.state.storage = storage


@pytest.fixture
def _patch_llm() -> None:  # type: ignore[return]
    stub = StubLLMClient()
    with patch("app.server._get_llm", return_value=stub):
        yield


@pytest.mark.asyncio
@pytest.mark.usefixtures("_patch_storage", "_patch_llm")
async def test_process_endpoint() -> None:
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        data = SAMPLE_DATA_PATH.read_bytes()
        response = await client.post(
            "/api/process",
            files={"file": ("messages.json", data, "application/json")},
        )

    assert response.status_code == 200
    body = response.json()
    assert "task_id" in body
    assert body["status"] == "pending"

    # Let background task complete
    await asyncio.sleep(0.5)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        task_response = await client.get(f"/api/tasks/{body['task_id']}")

    assert task_response.status_code == 200
    task = task_response.json()
    assert task["status"] == "completed"
    assert task["result"]["messages_processed"] == 20
    assert len(task["result"]["classifications"]) > 0
    assert len(task["result"]["briefing"]) > 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("_patch_storage")
async def test_task_not_found() -> None:
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/tasks/nonexistent-id")

    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.usefixtures("_patch_storage")
async def test_people_endpoint() -> None:
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/people")

    assert response.status_code == 200
    assert response.json() == []
