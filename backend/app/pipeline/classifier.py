"""S3: Classifier + Trap Detector."""

import json
from typing import Any, cast

import structlog

from app.llm import LLMClient
from app.models import (
    Category,
    ClassifiedItem,
    ExtractedThread,
    Flag,
    FlagType,
    Person,
    PersonRef,
    Urgency,
)
from app.prompts import classifier as prompts

logger = structlog.get_logger()


def _normalize_classification_items(result: dict[str, Any]) -> list[dict[str, Any]]:
    raw_classifications = result.get("classifications")
    logger.info(
        "classifier_payload_shape",
        classifications_type=type(raw_classifications).__name__,
    )

    if isinstance(raw_classifications, list):
        items = raw_classifications
    elif isinstance(raw_classifications, dict):
        items = list(raw_classifications.values())
    else:
        msg = (
            "Expected classifier result 'classifications' to be a list of objects "
            "or an object keyed by thread_id; got "
            f"{type(raw_classifications).__name__}"
        )
        raise TypeError(msg)

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            msg = (
                f"Expected classifier result 'classifications[{index}]' to be an object; "
                f"got {type(item).__name__}"
            )
            raise TypeError(msg)
        normalized.append(cast("dict[str, Any]", item))

    return normalized


def _parse_classification(c: dict[str, Any]) -> ClassifiedItem:
    flags = [
        Flag(
            type=FlagType(f["type"]),
            description=f["description"],
            severity=Urgency(f["severity"]),
            related_message_ids=f.get("related_message_ids", []),
            recommendation=f.get("recommendation", ""),
            connected_threads=f.get("connected_threads", []),
        )
        for f in c.get("flags", [])
    ]

    delegate_to = None
    if c.get("delegate_to"):
        delegate_to = PersonRef(
            name=c["delegate_to"]["name"],
            role=c["delegate_to"].get("role"),
        )

    return ClassifiedItem(
        thread_id=c.get("thread_id"),
        message_ids=c["message_ids"],
        category=Category(c["category"]),
        reasoning=c["reasoning"],
        source_message_ids=c.get("source_message_ids", []),
        deadline=c.get("deadline"),
        flags=flags,
        delegate_to=delegate_to,
        urgency=Urgency(c["urgency"]),
        requires_response=c["requires_response"],
        topic_summary=c["topic_summary"],
    )


async def classify(
    extracted_threads: list[ExtractedThread],
    people: list[Person],
    history_summary: str,
    *,
    llm: LLMClient,
    model: str,
) -> tuple[list[ClassifiedItem], list[Person]]:
    """Classify threads using pre-extracted facts. Returns (classifications, new_people)."""
    extracted_data = [t.model_dump(mode="json") for t in extracted_threads]
    people_data = [
        {"name": p.name, "role": p.role, "department": p.department, "expertise": p.expertise}
        for p in people
    ]

    user_prompt = prompts.build_user_prompt(
        extracted_threads_json=json.dumps(extracted_data, indent=2),
        people_json=json.dumps(people_data, indent=2),
        history_summary=history_summary or "No previous history.",
    )

    result = await llm.call(
        system=prompts.SYSTEM,
        user_prompt=user_prompt,
        tool=prompts.TOOL_DEFINITION,
        model=model,
    )

    classification_items = _normalize_classification_items(result)
    classifications = [_parse_classification(c) for c in classification_items]

    new_people = [
        Person(
            id=np["id"],
            name=np["name"],
            email=np.get("email"),
            role=np.get("role"),
            department=np.get("department"),
            expertise=np.get("expertise", []),
            is_internal=np.get("is_internal", True),
        )
        for np in result.get("new_people", [])
    ]

    return classifications, new_people


async def classify_single(
    extracted_thread: ExtractedThread,
    people: list[Person],
    feedback: str,
    history_summary: str,
    *,
    llm: LLMClient,
    model: str,
) -> ClassifiedItem:
    """Re-classify a single thread with verifier feedback."""
    extracted_data = [extracted_thread.model_dump(mode="json")]
    people_data = [
        {"name": p.name, "role": p.role, "department": p.department, "expertise": p.expertise}
        for p in people
    ]

    user_prompt = f"""VERIFIER FEEDBACK (fix these issues):
{feedback}

{
        prompts.build_user_prompt(
            extracted_threads_json=json.dumps(extracted_data, indent=2),
            people_json=json.dumps(people_data, indent=2),
            history_summary=history_summary,
        )
    }"""

    result = await llm.call(
        system=prompts.SYSTEM,
        user_prompt=user_prompt,
        tool=prompts.TOOL_DEFINITION,
        model=model,
    )

    classification_items = _normalize_classification_items(result)
    if not classification_items:
        msg = "Expected classifier result 'classifications' to contain at least one object"
        raise ValueError(msg)

    return _parse_classification(classification_items[0])
