"""History — fact-based summary generation for LLM context."""

from app.models import PipelineResult


def generate_history_summary(results: list[PipelineResult]) -> str:
    """Fact-based summary of recent history for LLM context (target <2000 tokens).

    Lists concrete facts from each day's classifications — names, numbers,
    deadlines, and outcomes — not vague summaries.
    """
    if not results:
        return "No previous history available."

    lines = ["Recent communication history:"]

    for r in results:
        lines.append(f"\n## {r.date} ({r.messages_processed} messages)")

        # Key facts from decide items
        decide_items = [c for c in r.classifications if c.category.value == "decide"]
        if decide_items:
            lines.append("Decisions needed:")
            for item in decide_items[:5]:
                parts = [f"  - {item.topic_summary}"]
                if item.deadline:
                    parts.append(f"Deadline: {item.deadline}")
                if item.source_message_ids:
                    ids = ", ".join(f"#{mid}" for mid in item.source_message_ids[:3])
                    parts.append(f"[Source: {ids}]")
                lines.append(" | ".join(parts))

        # Delegated items with specific names
        delegated = [c for c in r.classifications if c.category.value == "delegate"]
        if delegated:
            lines.append("Delegated:")
            for item in delegated[:5]:
                who = item.delegate_to.name if item.delegate_to else "unassigned"
                lines.append(f"  - {item.topic_summary} → {who}")

        # Flags with concrete details
        if r.flags:
            lines.append("Flags:")
            for flag in r.flags[:5]:
                ids = ", ".join(f"#{mid}" for mid in flag.related_message_ids[:3])
                lines.append(f"  - [{flag.type.value}] {flag.description} [Source: {ids}]")

    return "\n".join(lines)
