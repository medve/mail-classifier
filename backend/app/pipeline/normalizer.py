"""S1: Normalizer — deterministic message parsing, no LLM."""

import re
from datetime import UTC, datetime

from app.models import Channel, NormalizedMessage, Person

EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
MENTION_PATTERN = re.compile(r"@([\w.-]+)")
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")
NAME_EMAIL_PATTERN = re.compile(r"^(.+?)\s*<(.+?)>$")


def _parse_sender(raw_from: str, channel: str) -> tuple[str, str | None]:
    match = NAME_EMAIL_PATTERN.match(raw_from.strip())
    if match:
        return match.group(1).strip(), match.group(2).strip()
    if channel == "slack":
        return raw_from.replace(".", " ").replace("_", " ").title(), None
    return raw_from.strip(), None


def _detect_role(name: str) -> str | None:
    match = re.search(r"\(([^)]+)\)", name)
    return match.group(1).strip() if match else None


def _clean_name(name: str) -> str:
    return re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()


def _is_internal(email: str | None, company_domains: list[str]) -> bool:
    if not email:
        return False
    domain = email.split("@")[-1].lower()
    return any(domain == d.lower().strip() for d in company_domains)


def _make_person_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def normalize_messages(
    raw_messages: list[dict[str, object]],
    company_domains: list[str] | None = None,
) -> tuple[list[NormalizedMessage], list[Person]]:
    """Parse raw messages into normalized form and extract initial people list."""
    if company_domains is None:
        company_domains = ["company.com"]

    messages: list[NormalizedMessage] = []
    people_map: dict[str, Person] = {}
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    for raw in raw_messages:
        channel = Channel(str(raw["channel"]))
        sender_raw = str(raw.get("from", ""))
        sender_name, sender_email = _parse_sender(sender_raw, str(raw["channel"]))
        sender_role = _detect_role(sender_raw)
        clean_sender = _clean_name(sender_name)
        is_internal = _is_internal(sender_email, company_domains)

        if sender_email is None and channel == Channel.SLACK:
            is_internal = True

        body = str(raw.get("body", ""))
        mentions = MENTION_PATTERN.findall(body)
        links = URL_PATTERN.findall(body)

        timestamp_raw = str(raw["timestamp"])
        ts = datetime.fromisoformat(timestamp_raw)

        msg = NormalizedMessage(
            id=int(str(raw["id"])),
            channel=channel,
            sender_name=clean_sender,
            sender_email=sender_email,
            sender_role=sender_role,
            is_internal=is_internal,
            timestamp=ts.isoformat(),
            subject=str(raw["subject"]) if raw.get("subject") else None,
            body=body,
            channel_name=str(raw["channel_name"]) if raw.get("channel_name") else None,
            mentions=mentions,
            links=links,
        )
        messages.append(msg)

        # Build people
        person_key = sender_email or clean_sender.lower()
        msg_id = int(str(raw["id"]))
        if person_key not in people_map:
            people_map[person_key] = Person(
                id=_make_person_id(clean_sender),
                name=clean_sender,
                email=sender_email,
                role=sender_role,
                is_internal=is_internal,
                first_seen=today,
                last_seen=today,
                source_messages=[msg_id],
            )
        else:
            p = people_map[person_key]
            if msg_id not in p.source_messages:
                p.source_messages.append(msg_id)
            p.last_seen = today
            if sender_role and not p.role:
                p.role = sender_role

        for mention in mentions:
            m_name = mention.replace(".", " ").replace("_", " ").title()
            m_key = mention.lower()
            if m_key not in people_map:
                people_map[m_key] = Person(
                    id=_make_person_id(m_name),
                    name=m_name,
                    is_internal=True,
                    first_seen=today,
                    last_seen=today,
                    source_messages=[msg_id],
                )
            elif msg_id not in people_map[m_key].source_messages:
                people_map[m_key].source_messages.append(msg_id)

    messages.sort(key=lambda m: m.timestamp)
    return messages, list(people_map.values())
