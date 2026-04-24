"""Classifier output parsing tests."""

import pytest
from app.pipeline.classifier import (
    _normalize_classification_items,
    _parse_classification,
)


def _classification_payload() -> dict[str, object]:
    return {
        "thread_id": "thread-1",
        "message_ids": [1],
        "category": "ignore",
        "reasoning": "Phishing message needs no CEO action",
        "source_message_ids": [1],
        "deadline": None,
        "flags": [
            {
                "type": "phishing",
                "description": "Suspicious billing domain",
                "severity": "high",
                "related_message_ids": [1],
                "recommendation": "Do not click the link",
                "connected_threads": [],
            }
        ],
        "delegate_to": None,
        "urgency": "high",
        "requires_response": False,
        "topic_summary": "Suspicious billing email",
    }


def test_normalize_classification_items_accepts_list() -> None:
    result = {"classifications": [_classification_payload()]}

    items = _normalize_classification_items(result)
    parsed = [_parse_classification(item) for item in items]

    assert parsed[0].thread_id == "thread-1"
    assert parsed[0].flags[0].type.value == "phishing"


def test_normalize_classification_items_accepts_thread_keyed_object() -> None:
    result = {"classifications": {"thread-1": _classification_payload()}}

    items = _normalize_classification_items(result)
    parsed = [_parse_classification(item) for item in items]

    assert parsed[0].thread_id == "thread-1"
    assert parsed[0].message_ids == [1]


def test_normalize_classification_items_rejects_string_item() -> None:
    result = {"classifications": ["thread-1"]}

    with pytest.raises(
        TypeError,
        match=r"Expected classifier result 'classifications\[0\]' to be an object; got str",
    ):
        _normalize_classification_items(result)
