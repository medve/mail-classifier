"""Pydantic models — data contracts for the CEO Communication Triage System."""

from enum import StrEnum

from pydantic import BaseModel, Field


class Channel(StrEnum):
    EMAIL = "email"
    SLACK = "slack"
    WHATSAPP = "whatsapp"


class Category(StrEnum):
    IGNORE = "ignore"
    DELEGATE = "delegate"
    DECIDE = "decide"


class Urgency(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FlagType(StrEnum):
    PHISHING = "phishing"
    ESCALATION = "escalation"
    SCHEDULE_CONFLICT = "schedule_conflict"
    DEAL_CHANGE = "deal_change"
    DEADLINE = "deadline"
    CONTRADICTION = "contradiction"
    INFO_RESOLVED = "info_resolved"
    SECURITY_THREAT = "security_threat"
    RETENTION_RISK = "retention_risk"
    MARKET_OPPORTUNITY = "market_opportunity"
    PATTERN = "pattern"


class VerificationIssueType(StrEnum):
    GROUNDING = "grounding"
    SECURITY = "security"
    TONE = "tone"
    DELEGATION = "delegation"
    COMPLETENESS = "completeness"
    CROSS_CONTAMINATION = "cross_contamination"
    CLASSIFICATION = "classification"
    TRAP_MISSED = "trap_missed"
    INFO_LEAK = "info_leak"
    NAME_ACCURACY = "name_accuracy"
    OTHER = "other"


# --- Input ---


class RawMessage(BaseModel):
    id: int
    channel: str
    timestamp: str
    body: str
    subject: str | None = None
    to: str | None = None
    sender: str = Field(alias="from", default="")
    channel_name: str | None = None

    model_config = {"populate_by_name": True}


class NormalizedMessage(BaseModel):
    id: int
    channel: Channel
    sender_name: str
    sender_email: str | None = None
    sender_role: str | None = None
    is_internal: bool = False
    timestamp: str
    subject: str | None = None
    body: str
    channel_name: str | None = None
    mentions: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)


# --- Correlation ---


class Contradiction(BaseModel):
    earlier_message_id: int
    later_message_id: int
    description: str
    field: str


class Thread(BaseModel):
    id: str
    message_ids: list[int]
    topic: str
    latest_state: str
    is_resolved: bool = False
    latest_message_id: int | None = None
    contradictions: list[Contradiction] = Field(default_factory=list)
    superseded_message_ids: list[int] = Field(default_factory=list)


# --- Classification ---


class ExtractedFact(BaseModel):
    claim: str
    source_message_id: int
    source_quote: str


class ExtractedPerson(BaseModel):
    name: str
    role: str | None = None
    source_message_id: int


class ExtractedThread(BaseModel):
    thread_id: str
    message_ids: list[int]
    topic: str
    facts: list[ExtractedFact] = Field(default_factory=list)
    people_mentioned: list[ExtractedPerson] = Field(default_factory=list)
    deadlines: list[ExtractedFact] = Field(default_factory=list)
    monetary_amounts: list[ExtractedFact] = Field(default_factory=list)
    actions_requested: list[ExtractedFact] = Field(default_factory=list)
    latest_status: ExtractedFact | None = None
    is_resolved: bool = False
    resolution_source: int | None = None


class Flag(BaseModel):
    type: FlagType
    description: str
    severity: Urgency
    related_message_ids: list[int] = Field(default_factory=list)
    recommendation: str = ""
    connected_threads: list[str] = Field(default_factory=list)


class PersonRef(BaseModel):
    name: str
    role: str | None = None


class ClassifiedItem(BaseModel):
    thread_id: str | None = None
    message_ids: list[int]
    category: Category
    reasoning: str
    source_message_ids: list[int] = Field(default_factory=list)
    deadline: str | None = None
    flags: list[Flag] = Field(default_factory=list)
    delegate_to: PersonRef | None = None
    urgency: Urgency = Urgency.LOW
    requires_response: bool = False
    topic_summary: str = ""


# --- Draft ---


class DraftResponse(BaseModel):
    message_id: int
    channel: Channel
    draft_response: str
    tone_notes: str = ""
    subject: str | None = None


# --- Verification ---


class VerificationResult(BaseModel):
    message_id: int | None = None
    thread_id: str | None = None
    passed: bool
    issues: list[str] = Field(default_factory=list)
    suggested_fix: str = ""
    issue_type: VerificationIssueType = VerificationIssueType.OTHER


# --- People ---


class DelegationRecord(BaseModel):
    date: str
    topic: str
    message_ids: list[int] = Field(default_factory=list)
    outcome: str | None = None


class Person(BaseModel):
    id: str
    name: str
    email: str | None = None
    role: str | None = None
    department: str | None = None
    expertise: list[str] = Field(default_factory=list)
    is_internal: bool = True
    first_seen: str = ""
    last_seen: str = ""
    source_messages: list[int] = Field(default_factory=list)
    delegation_history: list[DelegationRecord] = Field(default_factory=list)


# --- Task ---


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# --- Pipeline output ---


class PipelineResult(BaseModel):
    date: str
    messages_processed: int
    threads: list[Thread] = Field(default_factory=list)
    classifications: list[ClassifiedItem] = Field(default_factory=list)
    flags: list[Flag] = Field(default_factory=list)
    drafts: list[DraftResponse] = Field(default_factory=list)
    verification: list[VerificationResult] = Field(default_factory=list)
    briefing: str = ""
    people_discovered: list[Person] = Field(default_factory=list)


# --- API ---


class BriefingResponse(BaseModel):
    briefing: str
    date: str


class TaskState(BaseModel):
    task_id: str
    status: TaskStatus
    error: str | None = None
    result: PipelineResult | None = None
    created_at: str = ""
    updated_at: str = ""


class TaskSubmitted(BaseModel):
    task_id: str
    status: TaskStatus


class OverrideRequest(BaseModel):
    category: Category
    reasoning: str | None = None
