"""S4: Response Drafter."""

import json
from typing import Any

from app.llm import LLMClient
from app.models import (
    Channel,
    ClassifiedItem,
    DraftResponse,
    ExtractedThread,
    NormalizedMessage,
)
from app.prompts import drafter as prompts


def _build_draft_items(
    classifications: list[ClassifiedItem],
    messages: list[NormalizedMessage],
    extracted_threads: list[ExtractedThread],
) -> list[dict[str, Any]]:
    msg_map = {m.id: m for m in messages}
    ext_map = {t.thread_id: t for t in extracted_threads}
    items: list[dict[str, Any]] = []
    for c in classifications:
        if not c.requires_response:
            continue
        ext_thread = ext_map.get(c.thread_id or "")
        extracted_facts = (
            [f.model_dump(mode="json") for f in ext_thread.facts] if ext_thread else []
        )
        for mid in c.message_ids:
            m = msg_map.get(mid)
            if not m:
                continue
            items.append(
                {
                    "message_id": m.id,
                    "channel": m.channel.value,
                    "sender": m.sender_name,
                    "subject": m.subject,
                    "body": m.body,
                    "category": c.category.value,
                    "delegate_to": c.delegate_to.model_dump() if c.delegate_to else None,
                    "topic_summary": c.topic_summary,
                    "reasoning": c.reasoning,
                    "extracted_facts": extracted_facts,
                }
            )
    return items


def _parse_draft(d: dict[str, Any]) -> DraftResponse:
    return DraftResponse(
        message_id=d["message_id"],
        channel=Channel(d["channel"]),
        draft_response=d["draft_response"],
        tone_notes=d.get("tone_notes", ""),
        subject=d.get("subject"),
    )


async def draft_responses(
    classifications: list[ClassifiedItem],
    messages: list[NormalizedMessage],
    extracted_threads: list[ExtractedThread],
    *,
    llm: LLMClient,
    model: str,
) -> list[DraftResponse]:
    """Draft responses for messages that need them."""
    items = _build_draft_items(classifications, messages, extracted_threads)
    if not items:
        return []

    user_prompt = prompts.build_user_prompt(items_json=json.dumps(items, indent=2))

    result = await llm.call(
        system=prompts.SYSTEM,
        user_prompt=user_prompt,
        tool=prompts.TOOL_DEFINITION,
        model=model,
    )

    return [_parse_draft(d) for d in result["drafts"]]


async def draft_single(
    message_id: int,
    classifications: list[ClassifiedItem],
    messages: list[NormalizedMessage],
    extracted_threads: list[ExtractedThread],
    feedback: str,
    *,
    llm: LLMClient,
    model: str,
) -> DraftResponse:
    """Re-draft a single response with verifier feedback."""
    msg_map = {m.id: m for m in messages}
    ext_map = {t.thread_id: t for t in extracted_threads}
    m = msg_map[message_id]
    classification = next(
        (c for c in classifications if message_id in c.message_ids),
        None,
    )

    ext_thread = ext_map.get(classification.thread_id or "") if classification else None
    extracted_facts = [f.model_dump(mode="json") for f in ext_thread.facts] if ext_thread else []

    item: dict[str, Any] = {
        "message_id": m.id,
        "channel": m.channel.value,
        "sender": m.sender_name,
        "subject": m.subject,
        "body": m.body,
        "category": classification.category.value if classification else "decide",
        "delegate_to": (
            classification.delegate_to.model_dump()
            if classification and classification.delegate_to
            else None
        ),
        "topic_summary": classification.topic_summary if classification else "",
        "reasoning": classification.reasoning if classification else "",
        "extracted_facts": extracted_facts,
    }

    user_prompt = prompts.build_retry_prompt(
        items_json=json.dumps([item], indent=2),
        feedback=feedback,
    )

    result = await llm.call(
        system=prompts.SYSTEM,
        user_prompt=user_prompt,
        tool=prompts.TOOL_DEFINITION,
        model=model,
    )

    return _parse_draft(result["drafts"][0])
