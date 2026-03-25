"""Shared fixtures — LLM stubs, storage stubs, sample data, test client."""

import json
from pathlib import Path
from typing import Any

import pytest
from app.llm import LLMClient
from app.models import Person, PipelineResult, TaskState
from app.storage import Storage

SAMPLE_DATA_PATH = Path(__file__).parent.parent / "data" / "messages.json"


class StubLLMClient:
    """Deterministic LLM stub for testing. Returns realistic structured data."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def call(
        self,
        *,
        system: str,
        user_prompt: str,
        tool: dict[str, Any],
        model: str,
        max_tokens: int = 8192,
    ) -> dict[str, Any]:
        self.calls.append({"system": system, "tool": tool["name"], "model": model})
        handlers: dict[str, Any] = {
            "submit_threads": self._threads_response,
            "submit_extraction": self._extraction_response,
            "submit_classifications": self._classifications_response,
            "submit_drafts": self._drafts_response,
            "submit_verification": self._verification_response,
            "submit_briefing": self._briefing_response,
            "submit_briefing_verification": self._briefing_verify_response,
        }
        handler = handlers.get(tool["name"])
        return handler() if handler else {}

    def _threads_response(self) -> dict[str, Any]:
        return {
            "threads": [
                {
                    "id": "thread-1",
                    "message_ids": [1, 18],
                    "topic": "Series B investor meeting",
                    "latest_state": "Sarah offered 10am Thursday instead of 2pm",
                    "latest_message_id": 18,
                    "is_resolved": False,
                    "contradictions": [],
                    "superseded_message_ids": [],
                },
                {
                    "id": "thread-2",
                    "message_ids": [2, 9, 16],
                    "topic": "API migration and payment issues",
                    "latest_state": "Payment service has live failures, needs rollback decision",
                    "latest_message_id": 16,
                    "is_resolved": False,
                    "contradictions": [
                        {
                            "earlier_message_id": 2,
                            "later_message_id": 16,
                            "description": "Escalated from 60% progress to live failures",
                            "field": "status",
                        }
                    ],
                    "superseded_message_ids": [2, 9],
                },
                {
                    "id": "thread-3",
                    "message_ids": [3, 10],
                    "topic": "Board deck review",
                    "latest_state": "Keep original Thursday slot, finance has numbers",
                    "latest_message_id": 10,
                    "is_resolved": True,
                    "contradictions": [
                        {
                            "earlier_message_id": 3,
                            "later_message_id": 10,
                            "description": "Push request cancelled",
                            "field": "schedule",
                        }
                    ],
                    "superseded_message_ids": [3],
                },
                {
                    "id": "thread-4",
                    "message_ids": [4],
                    "topic": "Security alert",
                    "latest_state": "Suspicious login email from seczure-verify.com",
                    "latest_message_id": 4,
                    "is_resolved": False,
                    "contradictions": [],
                    "superseded_message_ids": [],
                },
                {
                    "id": "thread-5",
                    "message_ids": [5, 6, 17],
                    "topic": "Horizon project",
                    "latest_state": "Lisa and David aligned on 10-week timeline, handled",
                    "latest_message_id": 17,
                    "is_resolved": True,
                    "contradictions": [],
                    "superseded_message_ids": [6],
                },
                {
                    "id": "thread-6",
                    "message_ids": [7],
                    "topic": "Sunday dinner with Mum",
                    "latest_state": "Mum asking about Sunday dinner",
                    "latest_message_id": 7,
                    "is_resolved": False,
                    "contradictions": [],
                    "superseded_message_ids": [],
                },
                {
                    "id": "thread-7",
                    "message_ids": [8],
                    "topic": "VP Engineering hiring",
                    "latest_state": "4 candidates shortlisted, Rachel recommends A and C",
                    "latest_message_id": 8,
                    "is_resolved": False,
                    "contradictions": [],
                    "superseded_message_ids": [],
                },
                {
                    "id": "thread-8",
                    "message_ids": [11],
                    "topic": "Tech newsletter",
                    "latest_state": "Weekly AI newsletter",
                    "latest_message_id": 11,
                    "is_resolved": False,
                    "contradictions": [],
                    "superseded_message_ids": [],
                },
                {
                    "id": "thread-9",
                    "message_ids": [12, 19],
                    "topic": "Northwind deal",
                    "latest_state": "Deal terms changed from 120k/2yr to 60k/1yr",
                    "latest_message_id": 19,
                    "is_resolved": False,
                    "contradictions": [
                        {
                            "earlier_message_id": 12,
                            "later_message_id": 19,
                            "description": "Deal terms changed",
                            "field": "price",
                        }
                    ],
                    "superseded_message_ids": [12],
                },
                {
                    "id": "thread-10",
                    "message_ids": [13],
                    "topic": "Hybrid policy and benefits",
                    "latest_state": "Benefits sign-off by Friday, hybrid policy grumbling",
                    "latest_message_id": 13,
                    "is_resolved": False,
                    "contradictions": [],
                    "superseded_message_ids": [],
                },
                {
                    "id": "thread-11",
                    "message_ids": [14],
                    "topic": "Marketing Q2 plan",
                    "latest_state": "Q2 plan finalized, no action needed",
                    "latest_message_id": 14,
                    "is_resolved": False,
                    "contradictions": [],
                    "superseded_message_ids": [],
                },
                {
                    "id": "thread-12",
                    "message_ids": [15, 20],
                    "topic": "Thursday leadership sync",
                    "latest_state": "Moved to 3pm in small meeting room",
                    "latest_message_id": 20,
                    "is_resolved": True,
                    "contradictions": [
                        {
                            "earlier_message_id": 15,
                            "later_message_id": 20,
                            "description": "Time and room changed",
                            "field": "schedule",
                        }
                    ],
                    "superseded_message_ids": [15],
                },
            ]
        }

    def _extraction_response(self) -> dict[str, Any]:
        return {
            "extracted_threads": [
                {
                    "thread_id": "thread-1",
                    "message_ids": [1, 18],
                    "topic": "Series B investor meeting",
                    "facts": [
                        {
                            "claim": "Sarah Chen wants to discuss Series B timeline",
                            "source_message_id": 1,
                            "source_quote": "discuss the Series B timeline and valuation",
                        },
                        {
                            "claim": "Sarah proposed 10am Thursday instead of 2pm",
                            "source_message_id": 18,
                            "source_quote": "Could we move to 10am instead?",
                        },
                    ],
                    "people_mentioned": [
                        {"name": "Sarah Chen", "role": None, "source_message_id": 1},
                    ],
                    "deadlines": [
                        {
                            "claim": "Revenue projections needed by Wednesday",
                            "source_message_id": 1,
                            "source_quote": "revenue projections by Wednesday",
                        },
                    ],
                    "monetary_amounts": [],
                    "actions_requested": [
                        {
                            "claim": "Confirm 10am Thursday meeting time",
                            "source_message_id": 18,
                            "source_quote": "Could we move to 10am instead?",
                        },
                    ],
                    "latest_status": {
                        "claim": "Sarah proposed moving to 10am Thursday",
                        "source_message_id": 18,
                        "source_quote": "Could we move to 10am instead?",
                    },
                    "is_resolved": False,
                    "resolution_source": None,
                },
                {
                    "thread_id": "thread-2",
                    "message_ids": [2, 9, 16],
                    "topic": "API migration and payment issues",
                    "facts": [
                        {
                            "claim": "API migration 60% complete, target Friday",
                            "source_message_id": 2,
                            "source_quote": "migration is 60% complete, targeting Friday",
                        },
                        {
                            "claim": "Dependency issue pushing timeline to next Wednesday",
                            "source_message_id": 9,
                            "source_quote": "dependency issue that's pushing our timeline to next Wednesday",
                        },
                        {
                            "claim": "Payment service failures, 3% of checkouts failing",
                            "source_message_id": 16,
                            "source_quote": "3% of our checkouts are failing",
                        },
                        {
                            "claim": "Tom proposes rollback or hotfix options",
                            "source_message_id": 16,
                            "source_quote": "rollback the migration (safer, but we lose 2 weeks) or deploy a targeted hotfix",
                        },
                        {
                            "claim": "Tom needs answer within the hour",
                            "source_message_id": 16,
                            "source_quote": "Need your call on this within the hour",
                        },
                    ],
                    "people_mentioned": [
                        {"name": "Tom Bradley", "role": None, "source_message_id": 2},
                    ],
                    "deadlines": [
                        {
                            "claim": "Decision needed within the hour",
                            "source_message_id": 16,
                            "source_quote": "Need your call on this within the hour",
                        },
                    ],
                    "monetary_amounts": [],
                    "actions_requested": [
                        {
                            "claim": "Choose rollback or hotfix for payment failures",
                            "source_message_id": 16,
                            "source_quote": "rollback the migration (safer, but we lose 2 weeks) or deploy a targeted hotfix",
                        },
                    ],
                    "latest_status": {
                        "claim": "Live payment failures, 3% of checkouts failing, needs rollback/hotfix decision",
                        "source_message_id": 16,
                        "source_quote": "3% of our checkouts are failing",
                    },
                    "is_resolved": False,
                    "resolution_source": None,
                },
                {
                    "thread_id": "thread-3",
                    "message_ids": [3, 10],
                    "topic": "Board deck review",
                    "facts": [
                        {
                            "claim": "Board deck keep original Thursday slot",
                            "source_message_id": 10,
                            "source_quote": "keep the original Thursday slot",
                        },
                    ],
                    "people_mentioned": [
                        {"name": "James", "role": "COO", "source_message_id": 10},
                    ],
                    "deadlines": [],
                    "monetary_amounts": [],
                    "actions_requested": [],
                    "latest_status": {
                        "claim": "Keeping original Thursday slot, finance has numbers",
                        "source_message_id": 10,
                        "source_quote": "keep the original Thursday slot",
                    },
                    "is_resolved": True,
                    "resolution_source": 10,
                },
                {
                    "thread_id": "thread-4",
                    "message_ids": [4],
                    "topic": "Security alert",
                    "facts": [
                        {
                            "claim": "Email from seczure-verify.com requesting login verification",
                            "source_message_id": 4,
                            "source_quote": "unusual login activity",
                        },
                    ],
                    "people_mentioned": [],
                    "deadlines": [],
                    "monetary_amounts": [],
                    "actions_requested": [],
                    "latest_status": {
                        "claim": "Suspicious email from seczure-verify.com",
                        "source_message_id": 4,
                        "source_quote": "unusual login activity",
                    },
                    "is_resolved": False,
                    "resolution_source": None,
                },
                {
                    "thread_id": "thread-5",
                    "message_ids": [5, 6, 17],
                    "topic": "Horizon project",
                    "facts": [
                        {
                            "claim": "David says issue is resolved, no action needed",
                            "source_message_id": 17,
                            "source_quote": "this is handled — no action needed from you anymore",
                        },
                    ],
                    "people_mentioned": [
                        {"name": "David Morrison", "role": None, "source_message_id": 17},
                        {"name": "Lisa Park", "role": None, "source_message_id": 5},
                    ],
                    "deadlines": [],
                    "monetary_amounts": [],
                    "actions_requested": [],
                    "latest_status": {
                        "claim": "Handled, no action needed",
                        "source_message_id": 17,
                        "source_quote": "this is handled — no action needed from you anymore",
                    },
                    "is_resolved": True,
                    "resolution_source": 17,
                },
                {
                    "thread_id": "thread-6",
                    "message_ids": [7],
                    "topic": "Sunday dinner with Mum",
                    "facts": [
                        {
                            "claim": "Mum asking about Sunday dinner",
                            "source_message_id": 7,
                            "source_quote": "Are you still coming for Sunday dinner?",
                        },
                    ],
                    "people_mentioned": [
                        {"name": "Mum", "role": None, "source_message_id": 7},
                    ],
                    "deadlines": [],
                    "monetary_amounts": [],
                    "actions_requested": [
                        {
                            "claim": "Confirm Sunday dinner attendance and wine preference",
                            "source_message_id": 7,
                            "source_quote": "Are you still coming for Sunday dinner?",
                        },
                    ],
                    "latest_status": {
                        "claim": "Mum asking about Sunday dinner",
                        "source_message_id": 7,
                        "source_quote": "Are you still coming for Sunday dinner?",
                    },
                    "is_resolved": False,
                    "resolution_source": None,
                },
                {
                    "thread_id": "thread-7",
                    "message_ids": [8],
                    "topic": "VP Engineering hiring",
                    "facts": [
                        {
                            "claim": "4 candidates shortlisted, Rachel recommends A and C",
                            "source_message_id": 8,
                            "source_quote": "narrowed down to 4 candidates",
                        },
                    ],
                    "people_mentioned": [
                        {"name": "Rachel Kim", "role": None, "source_message_id": 8},
                    ],
                    "deadlines": [],
                    "monetary_amounts": [],
                    "actions_requested": [
                        {
                            "claim": "Schedule intro calls with top candidates",
                            "source_message_id": 8,
                            "source_quote": "set up 30-min intro calls",
                        },
                    ],
                    "latest_status": {
                        "claim": "4 candidates shortlisted, recommends A and C",
                        "source_message_id": 8,
                        "source_quote": "narrowed down to 4 candidates",
                    },
                    "is_resolved": False,
                    "resolution_source": None,
                },
                {
                    "thread_id": "thread-8",
                    "message_ids": [11],
                    "topic": "Tech newsletter",
                    "facts": [
                        {
                            "claim": "Weekly AI newsletter",
                            "source_message_id": 11,
                            "source_quote": "This Week in AI",
                        },
                    ],
                    "people_mentioned": [],
                    "deadlines": [],
                    "monetary_amounts": [],
                    "actions_requested": [],
                    "latest_status": {
                        "claim": "Newsletter, no action needed",
                        "source_message_id": 11,
                        "source_quote": "This Week in AI",
                    },
                    "is_resolved": False,
                    "resolution_source": None,
                },
                {
                    "thread_id": "thread-9",
                    "message_ids": [12, 19],
                    "topic": "Northwind deal",
                    "facts": [
                        {
                            "claim": "Northwind initially offered 120k/2yr contract",
                            "source_message_id": 12,
                            "source_quote": "120k over two years",
                        },
                        {
                            "claim": "Northwind reduced to 1-year, dropping deal to 60k ARR",
                            "source_message_id": 19,
                            "source_quote": "that drops the deal to 60k ARR",
                        },
                    ],
                    "people_mentioned": [
                        {"name": "Priya Sharma", "role": None, "source_message_id": 12},
                    ],
                    "deadlines": [],
                    "monetary_amounts": [
                        {
                            "claim": "Original deal: 120k over two years",
                            "source_message_id": 12,
                            "source_quote": "120k over two years",
                        },
                        {
                            "claim": "Revised deal: 60k ARR",
                            "source_message_id": 19,
                            "source_quote": "that drops the deal to 60k ARR",
                        },
                    ],
                    "actions_requested": [
                        {
                            "claim": "Decide: accept 60k or push back",
                            "source_message_id": 19,
                            "source_quote": "do we accept or push back?",
                        },
                    ],
                    "latest_status": {
                        "claim": "Deal terms reduced from 120k/2yr to 60k/1yr, awaiting decision",
                        "source_message_id": 19,
                        "source_quote": "that drops the deal to 60k ARR",
                    },
                    "is_resolved": False,
                    "resolution_source": None,
                },
                {
                    "thread_id": "thread-10",
                    "message_ids": [13],
                    "topic": "Benefits sign-off and hybrid policy",
                    "facts": [
                        {
                            "claim": "Benefits package needs sign-off by Friday",
                            "source_message_id": 13,
                            "source_quote": "sign off on the benefits package by Friday",
                        },
                        {
                            "claim": "Grumbling about hybrid policy",
                            "source_message_id": 13,
                            "source_quote": "grumbling about the new hybrid policy",
                        },
                    ],
                    "people_mentioned": [
                        {
                            "name": "Alex",
                            "role": "Head of People",
                            "source_message_id": 13,
                        },
                    ],
                    "deadlines": [
                        {
                            "claim": "Benefits sign-off deadline Friday",
                            "source_message_id": 13,
                            "source_quote": "sign off on the benefits package by Friday",
                        },
                    ],
                    "monetary_amounts": [],
                    "actions_requested": [
                        {
                            "claim": "Sign off on benefits package",
                            "source_message_id": 13,
                            "source_quote": "sign off on the benefits package by Friday",
                        },
                    ],
                    "latest_status": {
                        "claim": "Benefits sign-off needed by Friday, hybrid policy concerns",
                        "source_message_id": 13,
                        "source_quote": "sign off on the benefits package by Friday",
                    },
                    "is_resolved": False,
                    "resolution_source": None,
                },
                {
                    "thread_id": "thread-11",
                    "message_ids": [14],
                    "topic": "Marketing Q2 plan",
                    "facts": [
                        {
                            "claim": "Q2 marketing plan finalized",
                            "source_message_id": 14,
                            "source_quote": "Q2 marketing plan",
                        },
                    ],
                    "people_mentioned": [
                        {"name": "Mark Stevens", "role": None, "source_message_id": 14},
                    ],
                    "deadlines": [],
                    "monetary_amounts": [],
                    "actions_requested": [],
                    "latest_status": {
                        "claim": "Q2 plan finalized, no action needed",
                        "source_message_id": 14,
                        "source_quote": "Q2 marketing plan",
                    },
                    "is_resolved": False,
                    "resolution_source": None,
                },
                {
                    "thread_id": "thread-12",
                    "message_ids": [15, 20],
                    "topic": "Thursday leadership sync",
                    "facts": [
                        {
                            "claim": "Leadership sync moved to 3pm in small meeting room",
                            "source_message_id": 20,
                            "source_quote": "moved to 3pm in the small meeting room",
                        },
                    ],
                    "people_mentioned": [
                        {"name": "Laura Singh", "role": None, "source_message_id": 15},
                    ],
                    "deadlines": [],
                    "monetary_amounts": [],
                    "actions_requested": [],
                    "latest_status": {
                        "claim": "Leadership sync at 3pm in small meeting room",
                        "source_message_id": 20,
                        "source_quote": "moved to 3pm in the small meeting room",
                    },
                    "is_resolved": True,
                    "resolution_source": 20,
                },
            ]
        }

    def _classifications_response(self) -> dict[str, Any]:
        return {
            "classifications": [
                {
                    "thread_id": "thread-1",
                    "message_ids": [1, 18],
                    "source_message_ids": [1, 18],
                    "category": "decide",
                    "reasoning": "Investor meeting timing and revenue projections need CEO",
                    "flags": [
                        {
                            "type": "schedule_conflict",
                            "description": "Thursday 2pm clashes with leadership sync",
                            "severity": "high",
                            "related_message_ids": [1, 15, 18],
                            "recommendation": "Accept Sarah's 10am offer",
                        }
                    ],
                    "delegate_to": None,
                    "urgency": "critical",
                    "requires_response": True,
                    "topic_summary": "Series B meeting with Meridian Ventures",
                },
                {
                    "thread_id": "thread-2",
                    "message_ids": [2, 9, 16],
                    "source_message_ids": [2, 9, 16],
                    "category": "decide",
                    "reasoning": "Live payment failures affecting 3% of users, needs immediate decision",
                    "flags": [
                        {
                            "type": "escalation",
                            "description": "API migration escalated to live transaction failures",
                            "severity": "critical",
                            "related_message_ids": [2, 9, 16],
                            "recommendation": "Recommend rollback for safety",
                        }
                    ],
                    "delegate_to": None,
                    "urgency": "critical",
                    "requires_response": True,
                    "topic_summary": "Payment service failures — rollback vs hotfix decision",
                },
                {
                    "thread_id": "thread-4",
                    "message_ids": [4],
                    "source_message_ids": [4],
                    "category": "ignore",
                    "reasoning": "Phishing email — seczure-verify.com is not a real security service",
                    "flags": [
                        {
                            "type": "phishing",
                            "description": "Suspicious domain seczure-verify.com, urgency language",
                            "severity": "high",
                            "related_message_ids": [4],
                            "recommendation": "Do not click. Report to IT security.",
                        }
                    ],
                    "delegate_to": None,
                    "urgency": "low",
                    "requires_response": False,
                    "topic_summary": "Phishing attempt — fake security alert",
                },
                {
                    "thread_id": "thread-5",
                    "message_ids": [5, 6, 17],
                    "source_message_ids": [5, 6, 17],
                    "category": "ignore",
                    "reasoning": "David and Lisa aligned, issue self-resolved",
                    "flags": [
                        {
                            "type": "info_resolved",
                            "description": "Horizon timeline concern resolved internally",
                            "severity": "low",
                            "related_message_ids": [6, 17],
                        }
                    ],
                    "delegate_to": None,
                    "urgency": "low",
                    "requires_response": False,
                    "topic_summary": "Horizon project — timeline concern resolved",
                },
                {
                    "thread_id": "thread-7",
                    "message_ids": [8],
                    "source_message_ids": [8],
                    "category": "delegate",
                    "reasoning": "Rachel can set up interviews, CEO review later",
                    "flags": [],
                    "delegate_to": {"name": "Rachel Kim", "role": "Recruiter"},
                    "urgency": "medium",
                    "requires_response": True,
                    "topic_summary": "VP Engineering candidate interviews",
                },
                {
                    "thread_id": "thread-8",
                    "message_ids": [11],
                    "source_message_ids": [11],
                    "category": "ignore",
                    "reasoning": "Newsletter, no action needed",
                    "flags": [],
                    "delegate_to": None,
                    "urgency": "low",
                    "requires_response": False,
                    "topic_summary": "Tech newsletter",
                },
                {
                    "thread_id": "thread-9",
                    "message_ids": [12, 19],
                    "source_message_ids": [12, 19],
                    "category": "decide",
                    "reasoning": "Deal terms changed significantly, CEO must decide",
                    "flags": [
                        {
                            "type": "deal_change",
                            "description": "Northwind dropped from 120k/2yr to 60k/1yr",
                            "severity": "high",
                            "related_message_ids": [12, 19],
                            "recommendation": "Push back on 1yr, offer 18-month compromise",
                        }
                    ],
                    "delegate_to": None,
                    "urgency": "high",
                    "requires_response": True,
                    "topic_summary": "Northwind deal terms changed — accept or push back",
                },
                {
                    "thread_id": "thread-10",
                    "message_ids": [13],
                    "source_message_ids": [13],
                    "category": "decide",
                    "reasoning": "Benefits sign-off deadline Friday, hybrid policy needs CEO attention",
                    "flags": [
                        {
                            "type": "deadline",
                            "description": "Benefits package sign-off by Friday or lose rate",
                            "severity": "high",
                            "related_message_ids": [13],
                        }
                    ],
                    "delegate_to": None,
                    "urgency": "high",
                    "requires_response": True,
                    "topic_summary": "Benefits sign-off + hybrid policy concerns",
                },
                {
                    "thread_id": "thread-3",
                    "message_ids": [3, 10],
                    "source_message_ids": [3, 10],
                    "category": "delegate",
                    "reasoning": "James handling board deck, just needs confirmation",
                    "flags": [],
                    "delegate_to": {"name": "Laura Singh", "role": "Admin"},
                    "urgency": "medium",
                    "requires_response": True,
                    "topic_summary": "Board deck review — keep Thursday slot",
                },
                {
                    "thread_id": "thread-6",
                    "message_ids": [7],
                    "source_message_ids": [7],
                    "category": "decide",
                    "reasoning": "Personal message, CEO should respond directly",
                    "flags": [],
                    "delegate_to": None,
                    "urgency": "low",
                    "requires_response": True,
                    "topic_summary": "Sunday dinner with family",
                },
                {
                    "thread_id": "thread-11",
                    "message_ids": [14],
                    "source_message_ids": [14],
                    "category": "ignore",
                    "reasoning": "FYI only, no action needed",
                    "flags": [],
                    "delegate_to": None,
                    "urgency": "low",
                    "requires_response": False,
                    "topic_summary": "Marketing Q2 plan — FYI",
                },
                {
                    "thread_id": "thread-12",
                    "message_ids": [15, 20],
                    "source_message_ids": [15, 20],
                    "category": "delegate",
                    "reasoning": "Laura handling scheduling, just acknowledge",
                    "flags": [
                        {
                            "type": "schedule_conflict",
                            "description": "Leadership sync moved from 2pm to 3pm",
                            "severity": "medium",
                            "related_message_ids": [15, 20],
                        }
                    ],
                    "delegate_to": {"name": "Laura Singh", "role": "Admin"},
                    "urgency": "low",
                    "requires_response": False,
                    "topic_summary": "Thursday leadership sync — room and time change",
                },
            ],
            "new_people": [],
        }

    def _drafts_response(self) -> dict[str, Any]:
        return {
            "drafts": [
                {
                    "message_id": 18,
                    "channel": "whatsapp",
                    "draft_response": "Hey Sarah, 10am Thursday works perfectly. I'll have the revenue projections over by Wednesday.",
                    "tone_notes": "casual whatsapp",
                },
                {
                    "message_id": 16,
                    "channel": "slack",
                    "draft_response": "Let's go with the rollback. Safer for users and we can make up the time. @tom.bradley kick off the rollback now.",
                    "tone_notes": "direct slack",
                },
                {
                    "message_id": 8,
                    "channel": "email",
                    "draft_response": "Hi Rachel,\n\nThanks for the shortlist. Let's set up 30-min intros with Candidate A and C next week. I'm free Tuesday and Wednesday afternoons.\n\nBest,\n[Name]",
                    "tone_notes": "professional email",
                    "subject": "Re: Candidate shortlist for VP Engineering role",
                },
                {
                    "message_id": 19,
                    "channel": "slack",
                    "draft_response": "Good work landing Northwind, Priya. On the revised terms — 60k/1yr is a big drop from 120k/2yr. Push back on the term length, see if they'll do 18 months. I'll join the call if needed.",
                    "tone_notes": "direct slack",
                },
                {
                    "message_id": 13,
                    "channel": "whatsapp",
                    "draft_response": "Hey Alex, I'll sign off on benefits today — send me the doc. Let's grab 15 mins tomorrow to talk through the hybrid concerns.",
                    "tone_notes": "casual whatsapp",
                },
                {
                    "message_id": 10,
                    "channel": "whatsapp",
                    "draft_response": "Perfect, Thursday works. Yes 2pm with Sarah is confirmed — actually she suggested 10am, let me sort it.",
                    "tone_notes": "casual whatsapp",
                },
                {
                    "message_id": 7,
                    "channel": "whatsapp",
                    "draft_response": "Yes still on for Sunday! Will bring the wine. Tell dad I can't wait for the lasagne 😊",
                    "tone_notes": "casual family whatsapp",
                },
            ]
        }

    def _verification_response(self) -> dict[str, Any]:
        return {
            "overall_pass": True,
            "results": [
                {"passed": True, "issues": [], "suggested_fix": "", "issue_type": "other"},
            ],
            "retry_items": [],
        }

    def _briefing_response(self) -> dict[str, Any]:
        return {
            "briefing": "# Daily Briefing — March 18, 2026\n\nTotal: 20 messages | 3 DECIDE | 1 FLAG | 2 DELEGATED | 6 FYI\n\n## Needs Your Decision (3 items)\n\n- **Payment failures**: 3% checkout failures. Recommend rollback. | Contact: Tom Bradley [Source: #16]\n- **Northwind deal**: Terms changed from 120k/2yr to 60k/1yr. Push back. | Contact: Priya Sharma [Source: #12, #19]\n- **Benefits sign-off**: Deadline Friday. | Contact: Alex (Head of People) [Source: #13]\n\n## Flags & Alerts\n\n- [High] **Phishing**: Suspicious email from seczure-verify.com — do not click. [Source: #4]\n\n## Delegated (2 items)\n\n- **VP Eng interviews** → Rachel Kim | Status: Shortlist ready [Source: #8]\n- **Board deck** → James | Status: Resolved — keeping Thursday slot [Source: #3, #10]\n\n## FYI (3 items)\n\n- [Resolved] **Horizon project**: Timeline resolved internally. [Source: #5, #6, #17]\n- **Marketing Q2 plan**: On track, no action needed. [Source: #14]\n- **Sunday dinner**: Mum asking about Sunday — needs response. [Source: #7]\n\n## Top 3 Priorities\n\n1. Payment rollback decision needed within the hour.\n2. Northwind deal terms — respond by end of day.\n3. Benefits package sign-off by Friday."
        }

    def _briefing_verify_response(self) -> dict[str, Any]:
        return {"passed": True, "issues": []}


# Verify StubLLMClient satisfies Protocol at module level
_stub_check: LLMClient = StubLLMClient()


@pytest.fixture
def stub_llm() -> StubLLMClient:
    return StubLLMClient()


@pytest.fixture
def sample_messages() -> list[dict[str, object]]:
    return json.loads(SAMPLE_DATA_PATH.read_text())  # type: ignore[return-value]


class StubStorage:
    """In-memory storage stub for testing."""

    def __init__(self) -> None:
        self.people: list[Person] = []
        self.history: dict[str, PipelineResult] = {}
        self.tasks: dict[str, TaskState] = {}

    async def save_task(self, state: TaskState) -> None:
        self.tasks[state.task_id] = state

    async def load_task(self, task_id: str) -> TaskState | None:
        return self.tasks.get(task_id)

    async def load_people(self) -> list[Person]:
        return self.people

    async def save_people(self, people: list[Person]) -> None:
        self.people = people

    async def save_history(self, result: PipelineResult) -> None:
        self.history[result.date] = result

    async def load_history(self, date_str: str) -> PipelineResult | None:
        return self.history.get(date_str)

    async def load_recent_history(self, days: int) -> list[PipelineResult]:
        return []


_storage_stub_check: Storage = StubStorage()


@pytest.fixture
def stub_storage() -> StubStorage:
    return StubStorage()
