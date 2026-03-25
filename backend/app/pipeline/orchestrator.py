"""Pipeline orchestrator — runs all stages with retry logic."""

import json
import re
from datetime import UTC, datetime
from typing import Any

import structlog

from app.config import (
    BRIEFING_MODEL,
    CLASSIFICATION_MODEL,
    CORRELATION_MODEL,
    DRAFTING_MODEL,
    EXTRACTION_MODEL,
    HISTORY_DAYS,
    MAX_RETRIES_PER_STAGE,
    VERIFICATION_MODEL,
)
from app.history import generate_history_summary
from app.llm import LLMClient
from app.models import (
    ClassifiedItem,
    DraftResponse,
    ExtractedThread,
    Flag,
    NormalizedMessage,
    Person,
    PipelineResult,
    VerificationIssueType,
)
from app.people import merge_people
from app.pipeline.classifier import classify, classify_single
from app.pipeline.correlator import correlate
from app.pipeline.drafter import draft_responses, draft_single
from app.pipeline.extractor import extract
from app.pipeline.normalizer import normalize_messages
from app.pipeline.verifier import verify
from app.storage import Storage

logger = structlog.get_logger()


BRIEFING_SYSTEM = """\
You generate a daily briefing for a CEO. It must be readable in under 2 minutes.

You receive PRE-EXTRACTED facts and classifications. You may ONLY use information from the \
triage data and extracted facts provided. Do not add, infer, or invent any details.

FORMAT SPEC (follow exactly):

# Daily Briefing — {date}

## Today's Schedule
- {time} — {event} ({status: confirmed/tentative/projected})
Include ALL confirmed meetings from the data. \
If a pending decision would create a new meeting, show it as "(projected — pending confirmation)". \
Only show times that appear in the extracted facts.

## Needs Your Decision ({N} items)
Ordered by deadline urgency — hard deadlines first (nearest first), no-deadline items last.
For each item:
- **{Topic}**: {one-sentence summary with key numbers from extracted facts}. \
Deadline: {exact from data or "none"}. Contact: {name from data}. [Source: #{message_ids}]

Financial details (amounts, ARR, deal terms) MUST be included when present in extracted facts. \
Separate unrelated items even if from same message — each distinct decision gets its own entry.

## Flags & Alerts
Group by severity (Critical → High → Medium → Low).
For each:
- [{severity}] **{type}**: {description from extracted facts}. [Source: #{message_ids}]
Resolved items: use [Resolved] tag and move to FYI section, NOT here.

## Delegated ({N} items)
- **{Topic}** → {person name from data} | Status: {current status}. [Source: #{message_ids}]

## FYI ({N} items)
- **{Topic}**: {one line}. [Source: #{message_ids}]
Include: resolved items with [Resolved] tag, personal messages needing response, \
informational updates. Do NOT skip personal messages (family, etc.) — they belong here or in DECIDE.

## Top 3 Priorities
1. {priority} — {one sentence with concrete action}
2. ...
3. ...

STRICT RULES:
- Every item MUST have [Source: #{ids}] suffix with real message IDs.
- Every name, number, date, and status MUST come from the triage data or extracted facts.
- Do not invent dollar amounts, percentages, valuations, deadlines, company names, or person names.
- NEVER say a message is incomplete, truncated, or "cuts off". All messages are complete as given.
- Resolved items go to FYI with [Resolved] tag, NOT to Flags or Needs Your Decision.
- An item CANNOT appear in both "Needs Your Decision" and "Delegated". Pick one.
- No delegation to generic groups. Only specific named people from the data.
- Do not merge unrelated action items. Different urgency/deadline = separate entries.
- Check latest state: if a deal is classified as lost, show as lost — not closed or won.
- Count items in each section header and ensure the count matches actual items.
- One-liners where possible, no paragraphs in body.
- CEO should scan in 90 seconds and deep-read in 2 minutes."""

BRIEFING_TOOL: dict[str, Any] = {
    "name": "submit_briefing",
    "description": "Submit the daily briefing",
    "input_schema": {
        "type": "object",
        "properties": {
            "briefing": {"type": "string"},
        },
        "required": ["briefing"],
    },
}

BRIEFING_VERIFY_SYSTEM = """\
You verify a CEO daily briefing against extracted facts and triage data. \
For EVERY factual claim in the briefing (names, numbers, dates, statuses, delegations):

1. Find the supporting extracted fact or classification. \
Every claim must trace to a specific source.
2. If no support → HALLUCINATION.
3. If data contradicts the claim (e.g. deal lost but briefing says closed) → WRONG.
4. If item appears in wrong section (e.g. resolved issue in "Needs Your Decision") → MISPLACED.
5. If count in header doesn't match actual items → WRONG COUNT.
6. If briefing says message is incomplete/truncated/cuts off → WRONG (messages are complete).

Also check:
- No item appears in both "Needs Your Decision" and "Delegated".
- Phishing not delegated to generic groups.
- DECIDE items ordered by deadline urgency.
- Resolved items in FYI with [Resolved] tag, not in DECIDE or Flags.
- No invented dollar amounts, percentages, company names, person names, or times.
- Personal messages (family) are not skipped.
- Financial details from extracted monetary_amounts are included where relevant.
- Every item has [Source: #ids] with valid message IDs."""

BRIEFING_VERIFY_TOOL: dict[str, Any] = {
    "name": "submit_briefing_verification",
    "description": "Submit briefing verification results",
    "input_schema": {
        "type": "object",
        "properties": {
            "passed": {"type": "boolean"},
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {
                            "type": "string",
                            "description": "The specific claim in the briefing",
                        },
                        "issue": {"type": "string", "description": "What's wrong"},
                        "fix": {"type": "string", "description": "How to fix it"},
                    },
                    "required": ["claim", "issue", "fix"],
                },
            },
        },
        "required": ["passed", "issues"],
    },
}


def _ensure_blank_lines_before_headers(text: str) -> str:
    """Ensure blank lines before headers and convert plain-text headers to markdown."""
    known_headers = [
        "Daily Briefing",
        "Today's Schedule",
        "Needs Your Decision",
        "Requires Your Decision",
        "Flags & Alerts",
        "Flags",
        "Delegated",
        "FYI",
        "Confirmed Meetings",
        "Top 3 Priorities",
    ]
    for h in known_headers:
        text = re.sub(rf"(?m)^{re.escape(h)}\b(.*)", rf"## {h}\1", text)
    # Ensure blank line before every markdown header
    return re.sub(r"(?<!\n)\n(#{1,6} )", r"\n\n\1", text)


def _derive_pipeline_date(messages: list[NormalizedMessage]) -> str:
    """Derive YYYY-MM-DD date from the latest message timestamp."""
    if not messages:
        return datetime.now(tz=UTC).strftime("%Y-%m-%d")
    latest = max(m.timestamp for m in messages)
    try:
        return datetime.fromisoformat(latest).strftime("%Y-%m-%d")
    except ValueError:
        return datetime.now(tz=UTC).strftime("%Y-%m-%d")


def _build_messages_summary(messages: list[NormalizedMessage]) -> str:
    """Condensed message summary for briefing context — source of truth for names."""
    lines: list[str] = []
    for m in messages:
        sender = m.sender_name
        if m.sender_role:
            sender += f" ({m.sender_role})"
        if m.sender_email:
            sender += f" <{m.sender_email}>"
        line = f"#{m.id} [{m.channel.value}] {sender}: {m.body[:200]}"
        lines.append(line)
    return "\n".join(lines)


def _derive_date_from_messages(messages: list[NormalizedMessage]) -> str:
    """Get the latest date from message timestamps."""
    if not messages:
        return datetime.now(tz=UTC).strftime("%B %d, %Y")
    latest = max(m.timestamp for m in messages)
    try:
        dt = datetime.fromisoformat(latest)
    except ValueError:
        return datetime.now(tz=UTC).strftime("%B %d, %Y")
    return dt.strftime("%B %d, %Y")


async def _verify_and_fix_briefing(
    briefing_text: str,
    messages_summary: str,
    triage_data: dict[str, Any],
    extracted_data: list[dict[str, Any]],
    *,
    llm: LLMClient,
) -> str:
    """Verify briefing against source data. Regenerate once if issues found."""
    verify_prompt = f"""Verify this briefing against the source data below.

BRIEFING TO VERIFY:
{briefing_text}

EXTRACTED FACTS (primary source of truth):
{json.dumps(extracted_data, indent=2)}

ORIGINAL MESSAGES (for cross-checking):
{messages_summary}

TRIAGE DATA:
{json.dumps(triage_data, indent=2)}

Check every factual claim. Be strict — flag any hallucination, wrong status, or wrong count."""

    result = await llm.call(
        system=BRIEFING_VERIFY_SYSTEM,
        user_prompt=verify_prompt,
        tool=BRIEFING_VERIFY_TOOL,
        model=BRIEFING_MODEL,
    )

    if result.get("passed", True):
        logger.info("briefing_verification_passed")
        return briefing_text

    issues = result.get("issues", [])
    logger.info("briefing_verification_failed", issue_count=len(issues))

    # Regenerate with feedback
    feedback_lines = [f"- {i['claim']}: {i['issue']}. Fix: {i['fix']}" for i in issues]
    feedback = "\n".join(feedback_lines)

    regen_prompt = f"""VERIFIER FOUND ISSUES — regenerate the briefing fixing these problems:
{feedback}

EXTRACTED FACTS (primary source of truth):
{json.dumps(extracted_data, indent=2)}

ORIGINAL MESSAGES (for cross-checking):
{messages_summary}

TRIAGE DATA:
{json.dumps(triage_data, indent=2)}

Fix ALL issues listed above. Do not invent any new details."""

    regen_result = await llm.call(
        system=BRIEFING_SYSTEM,
        user_prompt=regen_prompt,
        tool=BRIEFING_TOOL,
        model=BRIEFING_MODEL,
    )
    return str(regen_result["briefing"])


async def _generate_briefing(
    classifications: list[ClassifiedItem],
    drafts: list[DraftResponse],
    flags: list[Flag],
    messages: list[NormalizedMessage],
    extracted_threads: list[ExtractedThread],
    *,
    llm: LLMClient,
) -> str:
    data: dict[str, Any] = {
        "classifications": [c.model_dump(mode="json") for c in classifications],
        "drafts": [d.model_dump(mode="json") for d in drafts],
        "flags": [f.model_dump(mode="json") for f in flags],
    }

    extracted_data = [t.model_dump(mode="json") for t in extracted_threads]
    briefing_date = _derive_date_from_messages(messages)
    messages_summary = _build_messages_summary(messages)

    user_prompt = f"""Generate daily briefing from triage results.

EXTRACTED FACTS (primary source of truth for names, numbers, dates):
{json.dumps(extracted_data, indent=2)}

ORIGINAL MESSAGES (for name verification):
{messages_summary}

TRIAGE DATA:
{json.dumps(data, indent=2)}

ANTI-HALLUCINATION RULES:
- Every person name MUST appear in the extracted people_mentioned. Do NOT invent names.
- Every number MUST appear in extracted monetary_amounts or facts. If absent, omit.
- Every status MUST match the extracted latest_status. Do not invert outcomes.
- Every deadline MUST appear in extracted deadlines. Do not invent times.
- Every item MUST have [Source: #ids] with message IDs from the extraction.
- NEVER say a message is incomplete or cuts off. All messages are complete.
- If a scheduling conflict was resolved, show the final confirmed schedule.
- Count items in each section and put the correct count in the header.

Start with "# Daily Briefing — {briefing_date}".
Sections: ## Today's Schedule, ## Needs Your Decision, ## Flags & Alerts, \
## Delegated, ## FYI.
End with ## Top 3 Priorities."""

    result = await llm.call(
        system=BRIEFING_SYSTEM,
        user_prompt=user_prompt,
        tool=BRIEFING_TOOL,
        model=BRIEFING_MODEL,
    )
    briefing_text = str(result["briefing"])

    # Verify briefing against source data and regenerate if issues found
    briefing_text = await _verify_and_fix_briefing(
        briefing_text, messages_summary, data, extracted_data, llm=llm
    )

    return _ensure_blank_lines_before_headers(briefing_text)


def _collect_flags(classifications: list[ClassifiedItem]) -> list[Flag]:
    flags: list[Flag] = []
    for c in classifications:
        flags.extend(c.flags)
    return flags


async def _run_retry_loop(
    classifications: list[ClassifiedItem],
    drafts: list[DraftResponse],
    messages: list[NormalizedMessage],
    extracted_threads: list[ExtractedThread],
    people: list[Person],
    history_summary: str,
    *,
    llm: LLMClient,
) -> tuple[list[ClassifiedItem], list[DraftResponse], list[Any]]:
    """Run verification + retry loop. Returns updated classifications, drafts, verification."""
    retry_counts: dict[str, dict[str, int]] = {}
    verification: list[Any] = []
    ext_map = {t.thread_id: t for t in extracted_threads}

    for attempt in range(3):
        logger.info("verification_pass", attempt=attempt)
        verification, retry_items = await verify(
            classifications,
            drafts,
            messages,
            extracted_threads,
            people,
            llm=llm,
            model=VERIFICATION_MODEL,
        )

        failures = [v for v in verification if not v.passed]
        if not failures:
            logger.info("verification_passed")
            break

        had_retries = False

        # Use retry_items from verifier if available (preferred — has specific guidance)
        if retry_items:
            for item in retry_items:
                tid = item.get("thread_id", "unknown")
                retry_counts.setdefault(tid, {"s3": 0, "s4": 0})
                guidance = item.get("guidance", "")

                if (
                    item.get("stage") == "classifier"
                    and retry_counts[tid]["s3"] < MAX_RETRIES_PER_STAGE
                ):
                    retry_counts[tid]["s3"] += 1
                    had_retries = True
                    ext_thread = ext_map.get(tid)
                    if ext_thread:
                        logger.info("retry_s3", thread_id=tid, guidance=guidance)
                        updated = await classify_single(
                            ext_thread,
                            people,
                            feedback=guidance,
                            history_summary=history_summary,
                            llm=llm,
                            model=CLASSIFICATION_MODEL,
                        )
                        classifications = [
                            updated if c.thread_id == tid else c for c in classifications
                        ]
                        if updated.requires_response:
                            for mid in updated.message_ids:
                                new_draft = await draft_single(
                                    mid,
                                    classifications,
                                    messages,
                                    extracted_threads,
                                    feedback="Classification updated, redraft accordingly.",
                                    llm=llm,
                                    model=DRAFTING_MODEL,
                                )
                                drafts = [new_draft if d.message_id == mid else d for d in drafts]

                elif (
                    item.get("stage") == "drafter"
                    and retry_counts[tid]["s4"] < MAX_RETRIES_PER_STAGE
                ):
                    retry_counts[tid]["s4"] += 1
                    had_retries = True
                    thread_class = next((c for c in classifications if c.thread_id == tid), None)
                    if thread_class:
                        for mid in thread_class.message_ids:
                            logger.info("retry_s4", message_id=mid, guidance=guidance)
                            new_draft = await draft_single(
                                mid,
                                classifications,
                                messages,
                                extracted_threads,
                                feedback=guidance,
                                llm=llm,
                                model=DRAFTING_MODEL,
                            )
                            drafts = [new_draft if d.message_id == mid else d for d in drafts]
        else:
            # Fallback: use issue_type from verification results
            for failure in failures:
                key = str(failure.thread_id or failure.message_id or "unknown")
                retry_counts.setdefault(key, {"s3": 0, "s4": 0})

                if failure.issue_type in (
                    VerificationIssueType.CLASSIFICATION,
                    VerificationIssueType.DELEGATION,
                    VerificationIssueType.TRAP_MISSED,
                    VerificationIssueType.NAME_ACCURACY,
                    VerificationIssueType.GROUNDING,
                    VerificationIssueType.COMPLETENESS,
                ):
                    if retry_counts[key]["s3"] < MAX_RETRIES_PER_STAGE:
                        retry_counts[key]["s3"] += 1
                        had_retries = True
                        ext_thread = ext_map.get(failure.thread_id or "")
                        if ext_thread:
                            logger.info("retry_s3", thread_id=failure.thread_id)
                            updated = await classify_single(
                                ext_thread,
                                people,
                                feedback=failure.suggested_fix,
                                history_summary=history_summary,
                                llm=llm,
                                model=CLASSIFICATION_MODEL,
                            )
                            classifications = [
                                updated if c.thread_id == failure.thread_id else c
                                for c in classifications
                            ]

                elif failure.issue_type in (
                    VerificationIssueType.TONE,
                    VerificationIssueType.CROSS_CONTAMINATION,
                ):
                    tone_mid = failure.message_id
                    if tone_mid is not None and retry_counts[key]["s4"] < MAX_RETRIES_PER_STAGE:
                        retry_counts[key]["s4"] += 1
                        had_retries = True
                        logger.info("retry_s4", message_id=tone_mid)
                        new_draft = await draft_single(
                            tone_mid,
                            classifications,
                            messages,
                            extracted_threads,
                            feedback=failure.suggested_fix,
                            llm=llm,
                            model=DRAFTING_MODEL,
                        )
                        drafts = [new_draft if d.message_id == tone_mid else d for d in drafts]

        if not had_retries:
            break

    return classifications, drafts, verification


async def run_pipeline(
    raw_messages: list[dict[str, object]],
    *,
    llm: LLMClient,
    storage: Storage,
) -> PipelineResult:
    """Run full 5-stage pipeline with extraction pass and retry logic."""
    logger.info("pipeline_start", message_count=len(raw_messages))

    # S1: Normalize
    logger.info("stage_start", stage="S1_normalize")
    messages, initial_people = normalize_messages(raw_messages)

    # Derive date from messages (latest timestamp) instead of wall clock
    today = _derive_pipeline_date(messages)

    # Load context
    registry = await storage.load_people()
    registry = merge_people(registry, initial_people)
    history = await storage.load_recent_history(HISTORY_DAYS)
    history_summary = generate_history_summary(history)

    # S2: Correlate
    logger.info("stage_start", stage="S2_correlate")
    threads = await correlate(messages, history_summary, llm=llm, model=CORRELATION_MODEL)

    # S2.5: Extract facts
    logger.info("stage_start", stage="S2_5_extract")
    extracted_threads = await extract(threads, messages, llm=llm, model=EXTRACTION_MODEL)

    # S3: Classify (using extracted facts, not raw messages)
    logger.info("stage_start", stage="S3_classify")
    classifications, new_people = await classify(
        extracted_threads, registry, history_summary, llm=llm, model=CLASSIFICATION_MODEL
    )
    registry = merge_people(registry, new_people)

    # S4: Draft
    logger.info("stage_start", stage="S4_draft")
    drafts = await draft_responses(
        classifications, messages, extracted_threads, llm=llm, model=DRAFTING_MODEL
    )

    # S5: Verify + retry
    logger.info("stage_start", stage="S5_verify")
    classifications, drafts, verification = await _run_retry_loop(
        classifications,
        drafts,
        messages,
        extracted_threads,
        registry,
        history_summary,
        llm=llm,
    )

    # Collect flags and generate briefing
    all_flags = _collect_flags(classifications)
    logger.info("stage_start", stage="briefing")
    briefing = await _generate_briefing(
        classifications, drafts, all_flags, messages, extracted_threads, llm=llm
    )

    result = PipelineResult(
        date=today,
        messages_processed=len(messages),
        threads=threads,
        classifications=classifications,
        flags=all_flags,
        drafts=drafts,
        verification=verification,
        briefing=briefing,
        people_discovered=registry,
    )

    # Persist
    await storage.save_people(registry)
    await storage.save_history(result)
    logger.info("pipeline_end", classifications=len(classifications), flags=len(all_flags))

    return result
