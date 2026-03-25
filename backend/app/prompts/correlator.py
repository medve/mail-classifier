"""Prompts and tool schema for S2: Correlator."""

SYSTEM = """\
You are a message correlation engine. Your job is to group related messages \
into threads and determine the LATEST STATE of each topic.

TASK:
1. Group messages into THREADS by topic/conversation.
2. For each thread, determine the LATEST STATE — current status based on the most recent message.
3. Mark threads as RESOLVED if the latest message explicitly states the issue is handled.
4. Identify SUPERSEDED messages — earlier messages whose information has been replaced by later updates.
5. Identify CONTRADICTIONS — cases where messages conflict and the conflict is NOT yet resolved.
6. Identify SENDER DOMAIN MISMATCHES — flag if the same person appears to send from different domains.

RULES:
- A message can belong to multiple threads if it covers multiple topics.
- Time ordering is critical. A message at 12:00 overrides a message at 08:00 on the same topic.
- "Resolved" means the latest message explicitly states the issue is handled. Do not assume resolution.
- If someone says "ignore my earlier message" — the earlier message is superseded.
- Track sender email domains. If the same person emails from different domains, flag as domain mismatch.
- Standalone messages get their own single-message thread."""


def build_user_prompt(messages_json: str, history_summary: str) -> str:
    return f"""{history_summary}

Here are today's messages. Group into threads, identify contradictions and superseded messages.

MESSAGES:
{messages_json}

Every message ID must appear in at least one thread."""


TOOL_DEFINITION: dict[str, object] = {
    "name": "submit_threads",
    "description": "Submit the correlated message threads",
    "input_schema": {
        "type": "object",
        "properties": {
            "threads": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Descriptive slug, e.g. 'northwind-deal'",
                        },
                        "message_ids": {"type": "array", "items": {"type": "integer"}},
                        "topic": {"type": "string"},
                        "latest_state": {
                            "type": "string",
                            "description": "Current status based on the LAST message",
                        },
                        "latest_message_id": {
                            "type": "integer",
                            "description": "ID of the most recent message in this thread",
                        },
                        "is_resolved": {
                            "type": "boolean",
                            "description": "True if the latest message explicitly resolves this topic",
                        },
                        "contradictions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "earlier_message_id": {"type": "integer"},
                                    "later_message_id": {"type": "integer"},
                                    "description": {"type": "string"},
                                    "field": {"type": "string"},
                                },
                                "required": [
                                    "earlier_message_id",
                                    "later_message_id",
                                    "description",
                                    "field",
                                ],
                            },
                        },
                        "superseded_message_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                    },
                    "required": [
                        "id",
                        "message_ids",
                        "topic",
                        "latest_state",
                        "latest_message_id",
                        "is_resolved",
                        "contradictions",
                        "superseded_message_ids",
                    ],
                },
            },
            "domain_mismatches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "sender_name": {"type": "string"},
                        "domains": {"type": "array", "items": {"type": "string"}},
                        "message_ids": {"type": "array", "items": {"type": "integer"}},
                        "risk": {"type": "string"},
                    },
                    "required": ["sender_name", "domains", "message_ids", "risk"],
                },
            },
        },
        "required": ["threads"],
    },
}
