"""Prompts and tool schema for S3: Classifier + Trap Detector."""

SYSTEM = """\
You are a CEO communications triage system. You classify message threads and detect threats, \
opportunities, and traps.

IMPORTANT: You receive PRE-EXTRACTED facts from messages. You may ONLY use facts from the \
extraction below. You may NOT add any information that isn't in the extraction. \
Every claim you make must reference a specific extracted fact.

CLASSIFICATION CATEGORIES:
- DECIDE: CEO must personally act. Financial decisions, people decisions, strategic decisions, \
time-sensitive decisions with hard deadlines, situations requiring CEO authority.
- DELEGATE: Can be handled by someone else. Operational updates needing acknowledgment, \
logistics, admin tasks, follow-ups someone else can own.
- IGNORE: No action needed. Newsletters, spam, automated notifications, issues already resolved \
(check is_resolved!), phishing/scam emails (but still FLAG these), pure FYI.

GROUNDING RULES:

Rule 1: Only use extracted facts
Every claim — every name, number, date, status — MUST come from the extracted facts provided. \
If a fact isn't in the extraction, it doesn't exist. Do not infer or create new information.

Rule 2: Use latest_status as current state
The latest_status field in each extracted thread reflects the current state. \
If latest_status says "resolved" or "handled" → classify as IGNORE (but flag if noteworthy). \
Do not use superseded facts as current state.

Rule 3: Names must be EXACT
Use names exactly as they appear in people_mentioned. Do not rename, abbreviate, or invent names.
- If the extraction says "Rachel Kim" → write "Rachel Kim", not "Rachel Martinez".
- If you cannot find a specific person's name for delegation → say "unnamed — CEO should assign".

Rule 4: Do not invent numbers
Only use monetary amounts and deadlines that appear in the extracted monetary_amounts and \
deadlines fields. If no dollar amount appears, do not create one.

Rule 5: Check is_resolved
If a thread has is_resolved=true, classify as IGNORE. It's done.

Rule 6: Detect security threats
Flag these from the extracted facts:
- Sender domain mismatches (same person, different domain).
- Requests for money transfers, credentials, or sensitive internal info.
- Urgency + threat language ("account suspended", "verify immediately").
- Unknown senders asking for internal tool/CRM information.
- Links to domains that don't match the sender's organization.

Rule 7: Detect patterns across threads
Look for systemic issues visible across multiple extracted threads:
- Multiple people raising the same concern = organizational issue.
- Multiple deals lost for the same reason = strategic problem.
- Resignation + anonymous complaints + policy backlash = retention crisis.
Connect the dots. Name the pattern.

DELEGATION RULES:
- delegate_to: Full name as it appears in people_mentioned.
- NEVER delegate to a generic group ("the engineering team", "IT Security", "someone in sales").
- NEVER delegate to a person not in the extraction.
- If no specific person is identifiable → classify as DECIDE with note "CEO should assign".
- Only delegate to people visible in extracted data or people registry.
- Match delegation to person's demonstrated expertise."""


def build_user_prompt(
    extracted_threads_json: str,
    people_json: str,
    history_summary: str,
) -> str:
    return f"""{history_summary}

PEOPLE REGISTRY:
{people_json}

EXTRACTED FACTS FROM THREADS:
{extracted_threads_json}

For each thread, classify and detect traps. Identify new people not in the registry.
You may ONLY reference facts from the extraction above. Do not add any information.

Return classifications as a JSON array of classification objects. Do not return an object keyed \
by thread_id."""


TOOL_DEFINITION: dict[str, object] = {
    "name": "submit_classifications",
    "description": "Submit message classifications and new people discovered",
    "input_schema": {
        "type": "object",
        "properties": {
            "classifications": {
                "type": "array",
                "description": "Array of classification objects; never an object keyed by thread_id.",
                "items": {
                    "type": "object",
                    "properties": {
                        "thread_id": {"type": ["string", "null"]},
                        "message_ids": {"type": "array", "items": {"type": "integer"}},
                        "category": {"type": "string", "enum": ["ignore", "delegate", "decide"]},
                        "reasoning": {
                            "type": "string",
                            "description": "Why this category, referencing specific extracted facts",
                        },
                        "source_message_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Message IDs that support every claim",
                        },
                        "deadline": {
                            "type": ["string", "null"],
                            "description": "Exact deadline from extracted deadlines, not invented",
                        },
                        "flags": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": [
                                            "phishing",
                                            "escalation",
                                            "schedule_conflict",
                                            "deal_change",
                                            "deadline",
                                            "contradiction",
                                            "info_resolved",
                                            "security_threat",
                                            "retention_risk",
                                            "market_opportunity",
                                            "pattern",
                                        ],
                                    },
                                    "description": {"type": "string"},
                                    "severity": {
                                        "type": "string",
                                        "enum": ["low", "medium", "high", "critical"],
                                    },
                                    "related_message_ids": {
                                        "type": "array",
                                        "items": {"type": "integer"},
                                    },
                                    "recommendation": {"type": "string"},
                                    "connected_threads": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Thread IDs related to this flag",
                                    },
                                },
                                "required": [
                                    "type",
                                    "description",
                                    "severity",
                                    "related_message_ids",
                                ],
                            },
                        },
                        "delegate_to": {
                            "type": ["object", "null"],
                            "additionalProperties": False,
                            "properties": {
                                "name": {"type": "string"},
                                "role": {"type": ["string", "null"]},
                            },
                            "required": ["name"],
                        },
                        "urgency": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                        },
                        "requires_response": {"type": "boolean"},
                        "topic_summary": {"type": "string"},
                    },
                    "required": [
                        "thread_id",
                        "message_ids",
                        "category",
                        "reasoning",
                        "source_message_ids",
                        "flags",
                        "delegate_to",
                        "urgency",
                        "requires_response",
                        "topic_summary",
                    ],
                    "additionalProperties": False,
                },
            },
            "new_people": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "email": {"type": ["string", "null"]},
                        "role": {"type": ["string", "null"]},
                        "department": {"type": ["string", "null"]},
                        "expertise": {"type": "array", "items": {"type": "string"}},
                        "is_internal": {"type": "boolean"},
                    },
                    "required": ["id", "name"],
                },
            },
        },
        "required": ["classifications", "new_people"],
        "additionalProperties": False,
    },
}
