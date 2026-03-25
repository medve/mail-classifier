"""S2: Correlator — groups messages into threads, finds contradictions."""

import json
from typing import Any

from app.llm import LLMClient
from app.models import Contradiction, NormalizedMessage, Thread
from app.prompts import correlator as prompts


async def correlate(
    messages: list[NormalizedMessage],
    history_summary: str,
    *,
    llm: LLMClient,
    model: str,
) -> list[Thread]:
    """Group messages into threads and find contradictions."""
    messages_data: list[dict[str, Any]] = [
        {
            "id": m.id,
            "channel": m.channel.value,
            "sender": m.sender_name,
            "sender_email": m.sender_email,
            "sender_role": m.sender_role,
            "timestamp": m.timestamp,
            "subject": m.subject,
            "body": m.body,
            "channel_name": m.channel_name,
        }
        for m in messages
    ]

    user_prompt = prompts.build_user_prompt(
        messages_json=json.dumps(messages_data, indent=2),
        history_summary=history_summary or "No previous history available.",
    )

    result = await llm.call(
        system=prompts.SYSTEM,
        user_prompt=user_prompt,
        tool=prompts.TOOL_DEFINITION,
        model=model,
    )

    threads: list[Thread] = []
    for t in result["threads"]:
        threads.append(
            Thread(
                id=t["id"],
                message_ids=t["message_ids"],
                topic=t["topic"],
                latest_state=t["latest_state"],
                is_resolved=t.get("is_resolved", False),
                latest_message_id=t.get("latest_message_id"),
                contradictions=[Contradiction(**c) for c in t.get("contradictions", [])],
                superseded_message_ids=t.get("superseded_message_ids", []),
            )
        )

    # Ensure every message appears in at least one thread
    all_ids = {m.id for m in messages}
    covered: set[int] = set()
    for t in threads:
        covered.update(t.message_ids)

    for mid in all_ids - covered:
        msg = next(m for m in messages if m.id == mid)
        threads.append(
            Thread(
                id=f"thread-standalone-{mid}",
                message_ids=[mid],
                topic=msg.subject or f"Message from {msg.sender_name}",
                latest_state=msg.body[:200],
            )
        )

    return threads
