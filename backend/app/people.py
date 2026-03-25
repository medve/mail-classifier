"""People registry — merge, fuzzy matching."""

from app.models import DelegationRecord, Person


def _normalize_name(name: str) -> str:
    return name.lower().strip()


def find_person(name: str, registry: list[Person]) -> Person | None:
    """Find person by email, full name, or unique first name."""
    target = _normalize_name(name)

    for p in registry:
        if p.email and p.email.lower() == target:
            return p

    for p in registry:
        if _normalize_name(p.name) == target:
            return p

    first = target.split()[0] if target else ""
    matches = [p for p in registry if _normalize_name(p.name).split()[0] == first]
    if len(matches) == 1:
        return matches[0]

    return None


def merge_people(existing: list[Person], new: list[Person]) -> list[Person]:
    """Merge new people into existing registry. Updates roles, expertise, source_messages."""
    by_email: dict[str, Person] = {}
    by_name: dict[str, Person] = {}

    for p in existing:
        if p.email:
            by_email[p.email.lower()] = p
        by_name[_normalize_name(p.name)] = p

    for np in new:
        matched: Person | None = None

        if np.email and np.email.lower() in by_email:
            matched = by_email[np.email.lower()]
        elif _normalize_name(np.name) in by_name:
            matched = by_name[_normalize_name(np.name)]

        if matched:
            matched.last_seen = np.last_seen or matched.last_seen
            if np.role and not matched.role:
                matched.role = np.role
            if np.department and not matched.department:
                matched.department = np.department
            for exp in np.expertise:
                if exp not in matched.expertise:
                    matched.expertise.append(exp)
            for mid in np.source_messages:
                if mid not in matched.source_messages:
                    matched.source_messages.append(mid)
            if np.email and not matched.email:
                matched.email = np.email
                by_email[np.email.lower()] = matched
        else:
            if np.email:
                by_email[np.email.lower()] = np
            by_name[_normalize_name(np.name)] = np
            existing.append(np)

    return existing


def add_delegation(person_id: str, record: DelegationRecord, registry: list[Person]) -> None:
    for p in registry:
        if p.id == person_id:
            p.delegation_history.append(record)
            return
