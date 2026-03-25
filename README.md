# CEO Communication Triage System

AI-powered system that processes a CEO's daily communications across email, Slack, and WhatsApp — classifies messages, detects traps, delegates to specific people, drafts channel-appropriate responses, and generates an actionable daily briefing.

## Architecture

```
Messages → [S1: Normalize] → [S2: Correlate] → [S2.5: Extract] → [S3: Classify] → [S4: Draft] → [S5: Verify] → Output
                                                                                                        ↑ retry ↓
```

| Stage | Purpose | LLM? |
|-------|---------|------|
| S1: Normalizer | Parse JSON, extract names/roles/mentions/links | No |
| S2: Correlator | Group into threads, find contradictions, latest state | Yes |
| S2.5: Extractor | Extract grounded facts with source quotes from each thread | Yes |
| S3: Classifier | Triage (ignore/delegate/decide), detect traps — uses extracted facts only | Yes |
| S4: Drafter | Channel-appropriate responses (WhatsApp/Slack/Email) | Yes |
| S5: Verifier | 6-category quality checklist, triggers targeted retries | Yes |

### Two-pass architecture (anti-hallucination)

The pipeline uses a two-pass approach to prevent LLM hallucinations:

1. **Pass 1 — Extraction (S2.5):** A dedicated LLM call extracts only facts explicitly stated in messages. Every fact requires a `source_message_id` and `source_quote` (direct quote from message body). No interpretation, no inference.
2. **Pass 2 — Analysis (S3+):** Classifier, Drafter, and Verifier receive pre-extracted facts instead of raw messages. The LLM never sees raw message text and generates output simultaneously — eliminating the opportunity to "fill in" plausible-sounding details.

This structural separation makes hallucinations detectable: if a claim has no corresponding extracted fact, it was fabricated.

### Key decisions

- **Linear pipeline, not multi-agent.** Simpler, debuggable, predictable costs.
- **Protocol-based DI.** `LLMClient` and `Storage` Protocols enable testing with deterministic stubs.
- **Redis persistence.** Tasks, people registry, and history stored in Redis (replaces file-based storage).
- **Async task execution.** Pipeline runs in background, returns UUID for polling.
- **Two-pass extraction + analysis.** Facts extracted with source quotes first; classifier works on extracted facts only — prevents hallucinations structurally.
- **Targeted retries.** S5 verifier retries only failed items on the relevant stage (max 2 per item).
- **Dynamic people discovery.** People extracted from message context, not hardcoded.
- **Structured output via tool-use.** All LLM calls use Anthropic tool-use for JSON schema compliance.

### What it detects

- Phishing emails (suspicious domains, urgency language)
- Contradictions (later messages updating earlier ones)
- Deal changes (terms shifting between messages)
- Schedule conflicts (double-booked time slots)
- Escalations (issues worsening across messages)
- Self-resolving threads

## Environment

- Python >= 3.12, managed with `uv`
- Node.js >= 20
- Redis >= 7
- Anthropic API key (Claude Sonnet)

## Setup & Run

### Redis

```bash
docker compose up -d                 # starts Redis on localhost:6379
```

### Backend

```bash
cd backend
uv sync                              # install deps
cp ../.env.example ../.env           # add your ANTHROPIC_API_KEY
ANTHROPIC_API_KEY=sk-ant-... uv run uvicorn app.server:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                          # starts on http://localhost:3000
```

Open http://localhost:3000 and upload `backend/data/messages.json`.

## Quality Gates

### Backend (from `backend/`)

```bash
uv run ruff check app tests          # linter
uv run ruff format --check app tests # formatter
uv run mypy app                      # type checker (strict mode)
uv run pytest tests -v               # 20 tests (normalizer, pipeline e2e, API)
```

### Frontend (from `frontend/`)

```bash
npm run lint                         # ESLint (strict TypeScript)
npm run typecheck                    # tsc --noEmit
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/process` | Upload messages.json → returns `{task_id, status}` |
| POST | `/api/process-json` | Send messages as JSON body → returns `{task_id, status}` |
| GET | `/api/tasks/{task_id}` | Task state (pending/running/completed/failed + result) |
| GET | `/api/tasks/{task_id}/result` | Pipeline result (when completed) |
| GET | `/api/tasks/{task_id}/briefing` | Daily briefing (when completed) |
| GET | `/api/people` | People registry |
| PUT | `/api/tasks/{task_id}/override/{idx}` | Override classification |

Pipeline runs asynchronously — POST returns a task UUID immediately, poll status via GET.

## Security Constraints

- API keys only via environment variables, never in code
- Phishing detection: suspicious domains, urgency language, credential requests flagged
- CORS: only localhost:3000 allowed
- File upload: validated JSON before processing

## Testing Approach

- **Backend tests use LLM stubs** (`StubLLMClient` via Protocol DI). No real API calls.
- Stubs return realistic structured data matching the tool-use schema.
- Functional tests cover the full pipeline end-to-end.
- API tests exercise FastAPI routes with httpx + stubbed dependencies.

## Limitations

- No streaming/SSE for pipeline progress (frontend polls task status)
- No real-time integrations (Gmail, Slack API, WhatsApp) — JSON upload only
- No authentication on the API
- History summary limited to ~2000 tokens for LLM context

## What I'd improve with more time

1. SSE/WebSocket for real-time stage progress
3. Confidence scores per classification
4. CEO feedback loop (track overrides to improve prompts)
5. Integration APIs (Gmail, Slack, WhatsApp connectors)
6. Comprehensive test suite with edge cases
7. Rate limiting and retry with exponential backoff for API calls

## Project Structure

```
mail-classifier/
├── backend/
│   ├── app/
│   │   ├── config.py            # env-based settings
│   │   ├── llm.py               # LLMClient Protocol + Anthropic impl
│   │   ├── models.py            # Pydantic models
│   │   ├── storage.py           # Storage Protocol + Redis impl
│   │   ├── people.py            # people merge/matching
│   │   ├── history.py           # history summary generation
│   │   ├── server.py            # FastAPI app (async tasks)
│   │   ├── pipeline/
│   │   │   ├── orchestrator.py  # pipeline runner + retry
│   │   │   ├── normalizer.py    # S1
│   │   │   ├── correlator.py    # S2
│   │   │   ├── extractor.py     # S2.5 — fact extraction
│   │   │   ├── classifier.py    # S3
│   │   │   ├── drafter.py       # S4
│   │   │   └── verifier.py      # S5
│   │   └── prompts/             # LLM prompts + tool schemas
│   ├── tests/                   # 20 tests with LLM stubs
│   ├── data/messages.json       # sample data
│   └── pyproject.toml           # uv, ruff, mypy, pytest
├── frontend/
│   └── src/
│       ├── app/page.tsx         # dashboard
│       ├── components/          # Briefing, TriageList, FlagList
│       └── lib/api.ts           # typed API client
├── docker-compose.yml            # Redis
├── CLAUDE.md                    # engineering rules
└── README.md
```
