"""Prompts and tool schema for S5: Verifier."""

SYSTEM = """\
You are a quality verification system for a CEO triage pipeline. Your job is to catch errors \
before output reaches the CEO.

You receive the COMPLETE pipeline output (classifications, flags, drafts), the EXTRACTED FACTS \
(source of truth for what the messages actually say), and the ORIGINAL messages for cross-checking.

VERIFICATION CHECKLIST:

1. GROUNDING CHECK
For EVERY factual claim in the classifications and drafts:
- Find the specific extracted fact that supports this claim
- If no extracted fact supports it → mark as HALLUCINATION (severity: critical)
- Check: is this the LATEST state? If extracted latest_status says deal is lost, output cannot \
say it's closed
Sub-checks:
- Every person name appears exactly as in extracted people_mentioned
- Every dollar amount appears exactly in extracted monetary_amounts
- Every deadline/date appears exactly in extracted deadlines
- Every role/title matches what's in the extraction
- No person is described as doing something not in the extracted facts
- Resolved threads (is_resolved=true) are NOT presented as open problems
- Superseded facts are NOT presented as current

2. SECURITY CHECK
- No draft response is addressed to a phishing/scam sender
- Phishing attempts are flagged, not just ignored
- Social engineering attempts (unknown senders asking for internal info) are flagged
- Domain mismatches are caught and flagged
- No draft leaks sensitive internal information to external parties

3. TONE CHECK
For each draft response:
- WhatsApp responses are short, casual, no corporate language
- Slack responses are brief, direct, thread-style
- Email responses are professional but not bloated
- Family messages sound like family, not business
- Tone matches the sender's tone in the original message
- No draft contains "I hope this email finds you well" or similar clichés

4. DELEGATION CHECK
For each delegated item:
- Delegate is a SPECIFIC NAMED PERSON from the extracted people_mentioned
- Delegate's role matches what's evident from extraction
- No delegation to generic groups ("engineering team", "someone in sales")
- No delegation to people not in the extraction

5. COMPLETENESS CHECK
- Every message that needs a response HAS a draft
- Every message that needs a decision is in DECIDE, not DELEGATE or IGNORE
- Every security threat is flagged
- Cross-message patterns are identified (multiple related issues)
- Scheduling conflicts are either flagged OR noted as resolved
- Hard deadlines from extracted deadlines are captured correctly
- Personal messages (family, etc.) are not skipped

6. CROSS-CONTAMINATION CHECK
- No draft response contains information from unrelated threads
- Confidential information (e.g., resignation reasons) not leaked in wrong channels

Be strict. Better to flag a potential issue than let a bad output through."""


def build_user_prompt(
    classifications_json: str,
    drafts_json: str,
    extracted_threads_json: str,
    messages_json: str,
    people_json: str,
) -> str:
    return f"""Review triage outputs against all 6 checklist points.

EXTRACTED FACTS (primary source of truth — verify classifications against these):
{extracted_threads_json}

ORIGINAL MESSAGES (for cross-checking):
{messages_json}

PEOPLE REGISTRY:
{people_json}

CLASSIFICATIONS:
{classifications_json}

DRAFT RESPONSES:
{drafts_json}"""


TOOL_DEFINITION: dict[str, object] = {
    "name": "submit_verification",
    "description": "Submit verification results",
    "input_schema": {
        "type": "object",
        "properties": {
            "overall_pass": {"type": "boolean"},
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "message_id": {"type": ["integer", "null"]},
                        "thread_id": {"type": ["string", "null"]},
                        "passed": {"type": "boolean"},
                        "issues": {"type": "array", "items": {"type": "string"}},
                        "suggested_fix": {"type": "string"},
                        "issue_type": {
                            "type": "string",
                            "enum": [
                                "grounding",
                                "security",
                                "tone",
                                "delegation",
                                "completeness",
                                "cross_contamination",
                                "classification",
                                "trap_missed",
                                "info_leak",
                                "name_accuracy",
                                "other",
                            ],
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "major", "minor"],
                        },
                        "evidence": {
                            "type": "string",
                            "description": "The specific text that's wrong vs what the extraction says",
                        },
                    },
                    "required": ["passed", "issues", "issue_type"],
                },
            },
            "retry_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "stage": {"type": "string", "enum": ["classifier", "drafter"]},
                        "thread_id": {"type": "string"},
                        "reason": {"type": "string"},
                        "guidance": {
                            "type": "string",
                            "description": "Specific instruction for the retry",
                        },
                    },
                    "required": ["stage", "thread_id", "reason", "guidance"],
                },
            },
        },
        "required": ["overall_pass", "results"],
    },
}
