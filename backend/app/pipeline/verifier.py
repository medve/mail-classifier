"""S5: Verifier — quality gate with 6-category checklist."""

import json
from typing import Any

from app.llm import LLMClient
from app.models import (
    ClassifiedItem,
    DraftResponse,
    ExtractedThread,
    NormalizedMessage,
    Person,
    VerificationIssueType,
    VerificationResult,
)
from app.prompts import verifier as prompts


async def verify(
    classifications: list[ClassifiedItem],
    drafts: list[DraftResponse],
    messages: list[NormalizedMessage],
    extracted_threads: list[ExtractedThread],
    people: list[Person],
    *,
    llm: LLMClient,
    model: str,
) -> tuple[list[VerificationResult], list[dict[str, Any]]]:
    """Verify outputs against 6-category checklist.

    Returns (results, retry_items).
    """
    messages_data = [
        {
            "id": m.id,
            "channel": m.channel.value,
            "sender": m.sender_name,
            "sender_email": m.sender_email,
            "timestamp": m.timestamp,
            "subject": m.subject,
            "body": m.body,
        }
        for m in messages
    ]

    extracted_data = [t.model_dump(mode="json") for t in extracted_threads]
    people_data = [{"name": p.name, "role": p.role, "department": p.department} for p in people]

    user_prompt = prompts.build_user_prompt(
        classifications_json=json.dumps(
            [c.model_dump(mode="json") for c in classifications], indent=2
        ),
        drafts_json=json.dumps([d.model_dump(mode="json") for d in drafts], indent=2),
        extracted_threads_json=json.dumps(extracted_data, indent=2),
        messages_json=json.dumps(messages_data, indent=2),
        people_json=json.dumps(people_data, indent=2),
    )

    result = await llm.call(
        system=prompts.SYSTEM,
        user_prompt=user_prompt,
        tool=prompts.TOOL_DEFINITION,
        model=model,
    )

    raw_results = result.get("results", [])
    results: list[VerificationResult] = []
    for r in raw_results:
        if not isinstance(r, dict):
            continue
        results.append(
            VerificationResult(
                message_id=r.get("message_id"),
                thread_id=r.get("thread_id"),
                passed=r.get("passed", False),
                issues=r.get("issues", []),
                suggested_fix=r.get("suggested_fix", ""),
                issue_type=VerificationIssueType(r.get("issue_type", "other")),
            )
        )

    raw_retry = result.get("retry_items", [])
    retry_items: list[dict[str, Any]] = [ri for ri in raw_retry if isinstance(ri, dict)]

    return results, retry_items
