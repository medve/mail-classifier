"""FastAPI application — CEO Communication Triage System."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import ANTHROPIC_API_KEY, REDIS_URL
from app.llm import AnthropicLLMClient, LLMClient
from app.models import (
    BriefingResponse,
    OverrideRequest,
    Person,
    PipelineResult,
    TaskState,
    TaskStatus,
    TaskSubmitted,
)
from app.pipeline.orchestrator import run_pipeline
from app.storage import RedisStorage, Storage

logger = structlog.get_logger()

_background_tasks: set[asyncio.Task[None]] = set()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    redis_client = aioredis.from_url(REDIS_URL)
    _app.state.redis = redis_client
    _app.state.storage = RedisStorage(redis_client)
    yield
    await redis_client.aclose()


app = FastAPI(title="CEO Communication Triage", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_llm() -> LLMClient:
    return AnthropicLLMClient(api_key=ANTHROPIC_API_KEY)


def _get_storage(request: Request) -> Storage:
    return request.app.state.storage  # type: ignore[no-any-return]


async def _run_pipeline_task(
    task_id: str,
    raw_messages: list[dict[str, object]],
    llm: LLMClient,
    storage: Storage,
) -> None:
    now = datetime.now(tz=UTC).isoformat()
    await storage.save_task(
        TaskState(task_id=task_id, status=TaskStatus.RUNNING, created_at=now, updated_at=now)
    )
    try:
        result = await run_pipeline(raw_messages, llm=llm, storage=storage)
        await storage.save_task(
            TaskState(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                result=result,
                created_at=now,
                updated_at=datetime.now(tz=UTC).isoformat(),
            )
        )
    except Exception:
        logger.exception("pipeline_failed", task_id=task_id)
        await storage.save_task(
            TaskState(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error="Pipeline execution failed",
                created_at=now,
                updated_at=datetime.now(tz=UTC).isoformat(),
            )
        )


@app.post("/api/process")
async def process_messages(request: Request, file: Annotated[UploadFile, File()]) -> TaskSubmitted:
    content = await file.read()
    raw_messages: list[dict[str, object]] = json.loads(content)
    storage = _get_storage(request)
    task_id = str(uuid.uuid4())

    now = datetime.now(tz=UTC).isoformat()
    await storage.save_task(
        TaskState(task_id=task_id, status=TaskStatus.PENDING, created_at=now, updated_at=now)
    )
    task = asyncio.create_task(_run_pipeline_task(task_id, raw_messages, _get_llm(), storage))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return TaskSubmitted(task_id=task_id, status=TaskStatus.PENDING)


@app.post("/api/process-json")
async def process_messages_json(
    request: Request, messages: list[dict[str, object]]
) -> TaskSubmitted:
    storage = _get_storage(request)
    task_id = str(uuid.uuid4())

    now = datetime.now(tz=UTC).isoformat()
    await storage.save_task(
        TaskState(task_id=task_id, status=TaskStatus.PENDING, created_at=now, updated_at=now)
    )
    task = asyncio.create_task(_run_pipeline_task(task_id, messages, _get_llm(), storage))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return TaskSubmitted(task_id=task_id, status=TaskStatus.PENDING)


@app.get("/api/tasks/{task_id}")
async def get_task(request: Request, task_id: str) -> TaskState:
    storage = _get_storage(request)
    state = await storage.load_task(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return state


@app.get("/api/tasks/{task_id}/result")
async def get_task_result(request: Request, task_id: str) -> PipelineResult:
    storage = _get_storage(request)
    state = await storage.load_task(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if state.result is None:
        raise HTTPException(status_code=409, detail=f"Task is {state.status}")
    return state.result


@app.get("/api/tasks/{task_id}/briefing")
async def get_task_briefing(request: Request, task_id: str) -> BriefingResponse:
    storage = _get_storage(request)
    state = await storage.load_task(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if state.result is None:
        raise HTTPException(status_code=409, detail=f"Task is {state.status}")
    return BriefingResponse(briefing=state.result.briefing, date=state.result.date)


@app.get("/api/people")
async def get_people(request: Request) -> list[Person]:
    storage = _get_storage(request)
    return await storage.load_people()


@app.put("/api/tasks/{task_id}/override/{item_index}")
async def override_classification(
    request: Request, task_id: str, item_index: int, override: OverrideRequest
) -> dict[str, object]:
    storage = _get_storage(request)
    state = await storage.load_task(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if state.result is None:
        raise HTTPException(status_code=409, detail=f"Task is {state.status}")
    if item_index < 0 or item_index >= len(state.result.classifications):
        raise HTTPException(status_code=400, detail="Invalid item index")

    item = state.result.classifications[item_index]
    item.category = override.category
    if override.reasoning:
        item.reasoning = f"[CEO Override] {override.reasoning}"

    state.updated_at = datetime.now(tz=UTC).isoformat()
    await storage.save_task(state)

    return {"status": "ok", "updated": item.model_dump()}
