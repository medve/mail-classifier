# AGENTS.md

## Purpose

CEO Communication Triage System — AI-powered pipeline that processes daily messages (email, Slack, WhatsApp), classifies them, detects traps, delegates to specific people, and generates a CEO briefing.

## Project structure

```
mail-classifier/
├── backend/
│   ├── app/
│   │   ├── config.py            # settings from env
│   │   ├── llm.py               # LLMClient Protocol + Anthropic impl
│   │   ├── models.py            # Pydantic models (data contracts)
│   │   ├── people.py            # people registry persistence
│   │   ├── history.py           # daily results persistence
│   │   ├── server.py            # FastAPI app
│   │   ├── pipeline/
│   │   │   ├── orchestrator.py  # pipeline runner + retry logic
│   │   │   ├── normalizer.py    # S1: deterministic message parsing
│   │   │   ├── correlator.py    # S2: thread grouping + contradictions
│   │   │   ├── classifier.py    # S3: triage + trap detection
│   │   │   ├── drafter.py       # S4: channel-appropriate responses
│   │   │   └── verifier.py      # S5: quality gate
│   │   └── prompts/             # LLM prompts + tool schemas per stage
│   ├── tests/
│   │   ├── conftest.py          # StubLLMClient + fixtures
│   │   ├── test_normalizer.py
│   │   ├── test_pipeline.py     # end-to-end pipeline with stubbed LLM
│   │   └── test_api.py          # FastAPI functional tests
│   ├── data/
│   │   └── messages.json        # sample data
│   └── pyproject.toml           # uv, ruff, mypy, pytest config
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js app router
│   │   ├── components/          # React components
│   │   └── lib/                 # API client, types
│   ├── package.json
│   └── tsconfig.json
├── AGENTS.md
├── README.md
└── .env.example
```

## Core engineering principles

- Keep code simple and direct.
- Use composition over inheritance.
- Prefer functions over classes unless state is needed or classes bring significant simplification (Pydantic models are fine).
- Avoid premature abstractions; duplicate first, extract later.
- Keep modules loosely coupled with explicit dependency boundaries.
- Flat structure: no nested packages unless clearly justified.

## Python rules

- Minimum Python version: 3.12. Use modern syntax (union types with `|`, match statements where helpful).
- Use `uv` for all Python tooling. Never use pip directly.
- All endpoint handlers and pipeline stages are async.
- No synchronous blocking calls inside async functions. Use `asyncio.to_thread()` for unavoidable sync I/O.
- Use `Protocol` for dependency injection (especially LLM client). This enables testing with stubs.
- All LLM interactions go through a `LLMClient` Protocol, never call Anthropic SDK directly in pipeline stages.
- Pydantic models for all data contracts. No raw dicts crossing module boundaries.

## TypeScript/Frontend rules

- Strict TypeScript (`"strict": true` in tsconfig).
- Prefer functions and hooks over class components.
- All API types defined in `lib/api.ts`, matching backend Pydantic models.
- No `any` types. Use `unknown` + type guards where needed.
- Components are pure functions; state lives in page-level hooks.

## Testing policy

- Prefer functional tests over unit tests. Optimize for meaningful behavioral coverage, not coverage percentage.
- Backend tests:
  - Pipeline tests are end-to-end with stubbed LLM (using Protocol stubs).
  - API tests exercise FastAPI routes with `httpx.AsyncClient` and stubbed dependencies.
  - Tests must not call real LLM APIs. All LLM calls are replaced with deterministic stubs via DI.
  - Stubs return realistic structured data matching the tool-use schema.
- Frontend tests:
  - Component tests with React Testing Library.
  - API integration tests with MSW (Mock Service Worker) or fetch stubs.
- Test files live in `tests/` directories (backend: `backend/tests/`, frontend: `frontend/__tests__/`).
- Every new feature must include tests. A task is not done until tests pass.

## Linting and quality gates

### Backend (run from `backend/`)

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest tests
```

### Frontend (run from `frontend/`)

```bash
npm run lint
npm run typecheck
npm run test
```

### Rules

- All quality gates must pass with zero failures before any task is considered done.
- If linters fail, fix the code. Do not disable rules.
- If tests fail, fix the code or the test. Do not skip tests.
- Run checks after every change.

## Ruff config

- Line length: 100.
- Select: ALL minus rules that conflict with formatter or are too noisy (see pyproject.toml).
- Strict mode: treat all warnings as errors.

## Mypy config

- `strict = true`
- `warn_return_any = true`
- `disallow_untyped_defs = true`

## Security constraints

- Never store API keys in code. Use environment variables only.
- Phishing detection: flag suspicious domains, urgency language, credential requests.
- No user-provided data interpolated into LLM prompts without sanitization.
- CORS: only allow configured origins.
- File upload: validate JSON schema before processing.

## Architecture: 5-stage pipeline

```
Messages → [S1: Normalize] → [S2: Correlate] → [S3: Classify] → [S4: Draft] → [S5: Verify] → Output
```

- S1 (Normalizer): deterministic, no LLM. Pure functions.
- S2 (Correlator): single LLM call with all messages. Groups into threads.
- S3 (Classifier): LLM. Classifies as ignore/delegate/decide. Detects traps.
- S4 (Drafter): LLM. Drafts channel-appropriate responses.
- S5 (Verifier): LLM. 7-point quality checklist. Routes failures to targeted retries.
- Retry: max 2 per stage per message. Only retry failed items, not the full pipeline.

## Data constraints

- System must work on any message data, not just the sample. No hardcoded message IDs, sender names, or domain-specific rules.
- People are discovered dynamically from message context.
- Trap detection uses pattern-based heuristics in prompts, not hardcoded checks.

## Logging

- Use `structlog` for structured logging.
- Log pipeline stage entry/exit with timing.
- Log LLM call model, token usage, and duration.
- Log all errors with context.

## Definition of done

For every task:
- Code follows flat structure and function-first approach.
- Protocol-based DI is used for external dependencies (LLM, file I/O).
- Functional tests cover success + failure paths with stubs.
- All linters pass: `ruff check`, `ruff format --check`, `mypy`.
- All tests pass: `pytest`.
- No sync blocking calls in async functions.
- README is updated if public interface changes.
