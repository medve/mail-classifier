"""Prompts and tool schema for S2.5: Fact Extractor."""

SYSTEM = """\
You are a data extraction tool. Your ONLY job is to extract facts that are \
EXPLICITLY stated in the messages. You do NOT interpret, infer, summarize, or add context.

EXTRACTION RULES:

Rule 1: Direct quotes only
Every fact you extract MUST have a source_quote — a phrase copied directly from the message body. \
If you cannot quote the message, the fact does not exist.

Rule 2: No interpretation
- If a message says "that drops the deal to 60k ARR" → extract "60k ARR" as monetary amount.
- Do NOT compute, estimate, or derive numbers. Only extract what's literally written.
- Do NOT add context like "this means the deal is worse" — just extract the stated fact.

Rule 3: Names exactly as written
- Extract names EXACTLY as they appear in the sender field or message body.
- "Alex (Head of People)" → name: "Alex", role: "Head of People"
- "Priya Sharma" → name: "Priya Sharma", role: null (unless role stated)
- Do NOT guess, abbreviate, or expand names.

Rule 4: Latest state from latest message
- For each thread, the latest_status comes from the chronologically LAST message.
- If message #17 says "this is handled, no action needed" → latest_status reflects that.
- Earlier messages are still extracted as facts but do NOT define current status.

Rule 5: Deadlines and amounts must be verbatim
- Only extract deadlines if a specific date/time/day is mentioned: "by Friday", "within the hour", \
"end of day Thursday".
- Only extract monetary amounts if specific numbers appear: "60k ARR", "120k", "$5M".
- Do NOT invent deadlines or amounts that aren't in the text.

Rule 6: Actions requested
- Extract what the sender explicitly asks for: "do we accept or push back?", \
"can you sign off on the benefits package?", "let me know about Sunday".
- Do NOT infer implied actions.

Rule 7: Resolution
- A thread is resolved ONLY if the latest message explicitly says so: "this is handled", \
"no action needed", "resolved".
- Set resolution_source to the message ID that contains the resolution statement.

Rule 8: Messages are complete
- NEVER say a message is incomplete, truncated, or cuts off. All messages are provided in full. \
Every message is complete as given."""


def build_user_prompt(threads_json: str) -> str:
    return f"""Extract facts from each thread below. Follow extraction rules strictly.
For every fact, provide the exact source_quote from the message body.

THREADS WITH MESSAGES:
{threads_json}

Extract ALL facts, people, deadlines, monetary amounts, and requested actions. \
Do not skip any thread. Do not add information that isn't in the messages."""


TOOL_DEFINITION: dict[str, object] = {
    "name": "submit_extraction",
    "description": "Submit extracted facts from message threads",
    "input_schema": {
        "type": "object",
        "properties": {
            "extracted_threads": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "thread_id": {"type": "string"},
                        "message_ids": {"type": "array", "items": {"type": "integer"}},
                        "topic": {"type": "string"},
                        "facts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "claim": {
                                        "type": "string",
                                        "description": "The fact as stated in the message",
                                    },
                                    "source_message_id": {"type": "integer"},
                                    "source_quote": {
                                        "type": "string",
                                        "description": "Direct quote from message body",
                                    },
                                },
                                "required": ["claim", "source_message_id", "source_quote"],
                            },
                        },
                        "people_mentioned": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "role": {"type": ["string", "null"]},
                                    "source_message_id": {"type": "integer"},
                                },
                                "required": ["name", "source_message_id"],
                            },
                        },
                        "deadlines": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "claim": {"type": "string"},
                                    "source_message_id": {"type": "integer"},
                                    "source_quote": {"type": "string"},
                                },
                                "required": ["claim", "source_message_id", "source_quote"],
                            },
                        },
                        "monetary_amounts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "claim": {"type": "string"},
                                    "source_message_id": {"type": "integer"},
                                    "source_quote": {"type": "string"},
                                },
                                "required": ["claim", "source_message_id", "source_quote"],
                            },
                        },
                        "actions_requested": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "claim": {"type": "string"},
                                    "source_message_id": {"type": "integer"},
                                    "source_quote": {"type": "string"},
                                },
                                "required": ["claim", "source_message_id", "source_quote"],
                            },
                        },
                        "latest_status": {
                            "type": ["object", "null"],
                            "properties": {
                                "claim": {"type": "string"},
                                "source_message_id": {"type": "integer"},
                                "source_quote": {"type": "string"},
                            },
                            "required": ["claim", "source_message_id", "source_quote"],
                        },
                        "is_resolved": {"type": "boolean"},
                        "resolution_source": {"type": ["integer", "null"]},
                    },
                    "required": [
                        "thread_id",
                        "message_ids",
                        "topic",
                        "facts",
                        "people_mentioned",
                        "deadlines",
                        "monetary_amounts",
                        "actions_requested",
                        "latest_status",
                        "is_resolved",
                        "resolution_source",
                    ],
                },
            },
        },
        "required": ["extracted_threads"],
    },
}
