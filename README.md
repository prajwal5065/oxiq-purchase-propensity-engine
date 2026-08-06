# OxiQ Purchase Propensity Engine

An AI system that answers one question, with evidence:

> Based on all publicly available evidence, how likely is this company to buy our software within
> the next 3-12 months?

This is not a chatbot, not a lead-gen tool, and not a CRM. It's a scoring engine: collect public
signals about a company, extract grounded evidence from them (never invented facts), score six
explainable pillars, and (in later phases) combine those into a single Purchase Propensity Score
with a sales recommendation.

## Architecture

```
Client -> API -> Orchestrator -> Signal Collection -> Evidence Extraction -> Scoring Agents
       -> Rule Engine -> Purchase Score -> Recommendation Generator -> Database
```

Every collector, extractor, and scoring agent is independently testable and swappable behind a
small interface (`BaseCollector`, `EvidenceExtractor`, `BaseScoringAgent`).

## Build status

| Phase | Scope | Status |
|---|---|---|
| 1 | Project structure | Done |
| 2 | Database (SQLAlchemy models: Company, Signal, Evidence, Score, Recommendation) | Done |
| 3 | Signal Collectors (Search/Tavily, Website/Crawl4AI, Tech/Wappalyzer, News/RSS) | Done |
| 4 | Evidence Extraction Layer (Gemini, source+confidence enforced) | Done |
| 5 | Scoring Agents (Need, Urgency, Capacity, Digital Maturity, Org Readiness, Winnability) | Done |
| 6 | Rule Engine | Not started |
| 7 | Purchase Aggregator | Not started |
| 8 | Recommendation Generator | Not started |
| 9 | Full REST API (rule/aggregate-aware) | Partial - `/analyze`, `/company/{id}`, `/companies`, `/scores/{id}` exist and return pillar scores; aggregate purchase score is phase 6-7 |
| 10 | Frontend Dashboard | Not started |

## Live vs. stub mode

Every external integration reads its credentials from environment variables only (see
`.env.example`) and is gated by a feature flag:

- `ENABLE_LIVE_SEARCH` + `TAVILY_API_KEY` -> Tavily search collector
- `ENABLE_LIVE_CRAWL` -> Crawl4AI website collector
- `ENABLE_LIVE_TECH_DETECTION` -> Wappalyzer tech collector
- `ENABLE_LIVE_LLM` + `GEMINI_API_KEY` -> Gemini evidence extraction
- News (Google News RSS) needs no key and runs live by default

With every flag off, the full pipeline still runs end-to-end (collectors return empty results
instead of raising), which is how this was built and tested in this environment - no live API
calls have been made against Tavily, Crawl4AI, Wappalyzer, or Gemini yet.

## Local development

```bash
cp .env.example .env
docker compose up --build
```

API comes up on `http://localhost:8000`. With Postgres running, apply migrations:

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```

### Tests

```bash
pip install -e ".[dev]"
pytest
```

Tests cover schema validation, scoring-agent keyword logic, and collector stub-mode behavior -
nothing here depends on live network access or real API keys.

## API

- `POST /analyze` - run the pipeline for a domain, return pillar scores
- `GET /company/{id}` - company summary
- `GET /companies` - list companies
- `GET /scores/{id}` - a company's pillar scores
- `GET /health` - liveness check

## Repository layout

```
app/
  core/        settings, logging, celery app
  db/          async SQLAlchemy session/engine
  models/      ORM models
  schemas/     Pydantic request/response/domain schemas
  collectors/  Signal Collection Layer (search, website, tech, news)
  extraction/  Evidence Extraction Layer
  scoring/     Scoring Agents (one file per pillar)
  repositories/ Repository pattern over the ORM
  services/    Orchestration (collectors -> extraction -> scoring)
  api/         FastAPI routers
tests/
  unit/        no network, no DB
  integration/ reserved for DB-backed tests
alembic/       migrations
```
