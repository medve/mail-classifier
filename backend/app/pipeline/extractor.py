"""S2.5: Fact Extractor — extracts grounded facts from threaded messages."""

import json
from typing import Any

import structlog

from app.llm import LLMClient
from app.models import (
    ExtractedFact,
    ExtractedPerson,
    ExtractedThread,
    NormalizedMessage,
    Thread,
)
from app.prompts import extractor as prompts

logger = structlog.get_logger()


def _build_threads_with_messages(
    threads: list[Thread],
    messages: list[NormalizedMessage],
) -> list[dict[str, Any]]:
    """Attach full message content to threads for extraction."""
    msg_map = {m.id: m for m in messages}
    result: list[dict[str, Any]] = []
    for t in threads:
        thread_data: dict[str, Any] = {
            "thread_id": t.id,
            "message_ids": t.message_ids,
            "topic": t.topic,
            "is_resolved": t.is_resolved,
            "latest_message_id": t.latest_message_id,
            "messages": [
                {
                    "id": m.id,
                    "channel": m.channel.value,
                    "sender": m.sender_name,
                    "sender_role": m.sender_role,
                    "sender_email": m.sender_email,
                    "timestamp": m.timestamp,
                    "subject": m.subject,
                    "body": m.body,
                }
                for mid in t.message_ids
                if (m := msg_map.get(mid))
            ],
        }
        result.append(thread_data)
    return result


def _parse_fact(f: dict[str, Any]) -> ExtractedFact:
    return ExtractedFact(
        claim=f["claim"],
        source_message_id=f["source_message_id"],
        source_quote=f["source_quote"],
    )


def _parse_extracted_thread(t: dict[str, Any]) -> ExtractedThread:
    latest_status = None
    if t.get("latest_status"):
        latest_status = _parse_fact(t["latest_status"])

    return ExtractedThread(
        thread_id=t["thread_id"],
        message_ids=t["message_ids"],
        topic=t["topic"],
        facts=[_parse_fact(f) for f in t.get("facts", [])],
        people_mentioned=[
            ExtractedPerson(
                name=p["name"],
                role=p.get("role"),
                source_message_id=p["source_message_id"],
            )
            for p in t.get("people_mentioned", [])
        ],
        deadlines=[_parse_fact(f) for f in t.get("deadlines", [])],
        monetary_amounts=[_parse_fact(f) for f in t.get("monetary_amounts", [])],
        actions_requested=[_parse_fact(f) for f in t.get("actions_requested", [])],
        latest_status=latest_status,
        is_resolved=t.get("is_resolved", False),
        resolution_source=t.get("resolution_source"),
    )


async def extract(
    threads: list[Thread],
    messages: list[NormalizedMessage],
    *,
    llm: LLMClient,
    model: str,
) -> list[ExtractedThread]:
    """Extract grounded facts from threaded messages."""
    threads_data = _build_threads_with_messages(threads, messages)

    user_prompt = prompts.build_user_prompt(
        threads_json=json.dumps(threads_data, indent=2),
    )

    result = await llm.call(
        system=prompts.SYSTEM,
        user_prompt=user_prompt,
        tool=prompts.TOOL_DEFINITION,
        model=model,
    )

    raw_threads = result.get("extracted_threads")
    if raw_threads is None:
        logger.warning("extraction_missing_key", keys=list(result.keys()))
        # Fallback: try first list-typed value in result
        for v in result.values():
            if isinstance(v, list):
                raw_threads = v
                break
    if raw_threads is None:
        raw_threads = []

    return [_parse_extracted_thread(t) for t in raw_threads]
