"""Functional tests for S1: Normalizer."""

from app.pipeline.normalizer import normalize_messages


def test_normalizes_all_messages(sample_messages: list[dict[str, object]]) -> None:
    messages, people = normalize_messages(sample_messages)
    assert len(messages) == 20
    assert len(people) > 0


def test_messages_sorted_by_timestamp(sample_messages: list[dict[str, object]]) -> None:
    messages, _ = normalize_messages(sample_messages)
    timestamps = [m.timestamp for m in messages]
    assert timestamps == sorted(timestamps)


def test_extracts_sender_name_from_email() -> None:
    raw = [
        {
            "id": 1,
            "channel": "email",
            "from": "John Doe <john@company.com>",
            "timestamp": "2026-03-18T08:00:00Z",
            "body": "Hello",
            "subject": "Test",
        }
    ]
    messages, people = normalize_messages(raw)
    assert messages[0].sender_name == "John Doe"
    assert messages[0].sender_email == "john@company.com"
    assert any(p.name == "John Doe" for p in people)


def test_extracts_slack_username() -> None:
    raw = [
        {
            "id": 1,
            "channel": "slack",
            "from": "tom.bradley",
            "channel_name": "#engineering",
            "timestamp": "2026-03-18T08:00:00Z",
            "body": "hello",
        }
    ]
    messages, _people = normalize_messages(raw)
    assert messages[0].sender_name == "Tom Bradley"
    assert messages[0].is_internal is True


def test_extracts_whatsapp_role() -> None:
    raw = [
        {
            "id": 1,
            "channel": "whatsapp",
            "from": "James (COO)",
            "timestamp": "2026-03-18T08:00:00Z",
            "body": "hi",
        }
    ]
    messages, _people = normalize_messages(raw)
    assert messages[0].sender_name == "James"
    assert messages[0].sender_role == "COO"


def test_detects_internal_by_domain() -> None:
    raw = [
        {
            "id": 1,
            "channel": "email",
            "from": "Alice <alice@company.com>",
            "timestamp": "2026-03-18T08:00:00Z",
            "body": "hi",
        },
        {
            "id": 2,
            "channel": "email",
            "from": "Bob <bob@external.com>",
            "timestamp": "2026-03-18T08:01:00Z",
            "body": "hi",
        },
    ]
    messages, _ = normalize_messages(raw, company_domains=["company.com"])
    assert messages[0].is_internal is True
    assert messages[1].is_internal is False


def test_extracts_mentions() -> None:
    raw = [
        {
            "id": 1,
            "channel": "slack",
            "from": "priya.sharma",
            "channel_name": "#sales",
            "timestamp": "2026-03-18T08:00:00Z",
            "body": "cc @tom.bradley and @lisa.park",
        }
    ]
    messages, people = normalize_messages(raw)
    assert "tom.bradley" in messages[0].mentions
    assert "lisa.park" in messages[0].mentions
    assert len(people) >= 3  # priya + tom + lisa


def test_extracts_urls() -> None:
    raw = [
        {
            "id": 1,
            "channel": "email",
            "from": "Attacker <a@evil.com>",
            "timestamp": "2026-03-18T08:00:00Z",
            "body": "Click here: https://seczure-verify.com/auth/reset?token=abc",
        }
    ]
    messages, _ = normalize_messages(raw)
    assert len(messages[0].links) == 1
    assert "seczure-verify.com" in messages[0].links[0]


def test_handles_missing_optional_fields() -> None:
    raw = [
        {
            "id": 1,
            "channel": "whatsapp",
            "from": "Unknown",
            "timestamp": "2026-03-18T08:00:00Z",
            "body": "test",
        }
    ]
    messages, _ = normalize_messages(raw)
    assert messages[0].subject is None
    assert messages[0].channel_name is None
    assert messages[0].sender_email is None
