"""Storage Protocol and Redis implementation."""

from datetime import UTC, datetime, timedelta
from typing import Protocol

import redis.asyncio as aioredis

from app.config import TASK_TTL_SECONDS
from app.models import Person, PipelineResult, TaskState


class Storage(Protocol):
    """Async storage interface for pipeline state."""

    async def save_task(self, state: TaskState) -> None: ...
    async def load_task(self, task_id: str) -> TaskState | None: ...

    async def load_people(self) -> list[Person]: ...
    async def save_people(self, people: list[Person]) -> None: ...

    async def save_history(self, result: PipelineResult) -> None: ...
    async def load_history(self, date_str: str) -> PipelineResult | None: ...
    async def load_recent_history(self, days: int) -> list[PipelineResult]: ...


class RedisStorage:
    """Redis-backed storage."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def save_task(self, state: TaskState) -> None:
        key = f"task:{state.task_id}"
        await self._redis.set(key, state.model_dump_json(), ex=TASK_TTL_SECONDS)

    async def load_task(self, task_id: str) -> TaskState | None:
        data = await self._redis.get(f"task:{task_id}")
        if data is None:
            return None
        return TaskState.model_validate_json(data)

    async def load_people(self) -> list[Person]:
        data = await self._redis.get("people:registry")
        if data is None:
            return []
        import json

        raw: list[dict[str, object]] = json.loads(data)
        return [Person(**entry) for entry in raw]  # type: ignore[arg-type]

    async def save_people(self, people: list[Person]) -> None:
        import json

        payload = json.dumps([p.model_dump(mode="json") for p in people])
        await self._redis.set("people:registry", payload)

    async def save_history(self, result: PipelineResult) -> None:
        key = f"history:{result.date}"
        await self._redis.set(key, result.model_dump_json())

    async def load_history(self, date_str: str) -> PipelineResult | None:
        data = await self._redis.get(f"history:{date_str}")
        if data is None:
            return None
        return PipelineResult.model_validate_json(data)

    async def load_recent_history(self, days: int) -> list[PipelineResult]:
        results: list[PipelineResult] = []
        today = datetime.now(tz=UTC)
        for i in range(1, days + 1):
            date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            result = await self.load_history(date_str)
            if result:
                results.append(result)
        return results


_storage_check: Storage = RedisStorage(aioredis.Redis())
