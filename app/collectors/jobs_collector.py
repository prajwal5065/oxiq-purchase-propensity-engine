"""Jobs Collector - active job postings from a company's public applicant-
tracking-system (ATS) board, as hiring-intent evidence.

An open requisition is a direct, first-party signal that a company is
actively investing in a function *right now* - closer to ground truth than
a news article's characterization of hiring activity. This collector's
only job is to put grounded, per-posting raw text in front of the Evidence
Extractor so the existing Need/Urgency/Capacity scorers and Decision
Intelligence (Buying Intent, Why Now, Decision Engine) have something to
match against - it does not score anything itself.

Two free, unauthenticated providers, same pluggable-provider shape as
`CompanyProfileCollector` (app/collectors/company_profile_collector.py):

- `GreenhouseProvider` reads `GET /v1/boards/{slug}/jobs` from Greenhouse's
  public boards API.
- `LeverProvider` reads `GET /v0/postings/{slug}?mode=json` from Lever's
  public postings API.

There's no reliable public mapping from a company domain to its ATS board
slug, so both providers guess (the part before the first '.' in the
domain) - same approach and same rationale as GitHubCollector's org/user
guess. A 404 on a guessed slug is a legitimate "this company doesn't
publish a board under this name" NO_RESULTS, not a failure: missing job
data must never be reported as negative evidence (no open reqs is not the
same claim as "this company isn't hiring," and the Buying Intent /
Disqualification guardrails already know not to conflate "found nothing"
with "couldn't look").

Each posting is tagged with one of six hiring-category buckets (AI/ML,
Engineering, Data, Cloud/DevOps, Security, General) via keyword matching
against title/department/description - this is data *tagging*, not
scoring; the category rides on the RawSignal so downstream evidence
retains it (see EvidenceNormalizer's URL-matched category inheritance),
while the actual pillar/buying-intent/decision scoring is still done
entirely by the existing keyword-matching scorers and Decision
Intelligence engines against the extracted evidence text.
"""
import asyncio
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.collectors.base import BaseCollector
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.signal import SignalSource
from app.schemas.signal import CollectorResult, CollectorStatus, RawSignal

logger = get_logger(__name__)

MAX_JOBS_PER_PROVIDER = 50
MAX_DESCRIPTION_SNIPPET_CHARS = 500

# Checked in this order against "title department description_snippet"
# lowercased - first match wins, so more specific role families are
# listed before the general_hiring catch-all every posting qualifies for.
_HIRING_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    (
        "security_hiring",
        [
            "security engineer", "security analyst", "application security",
            "infosec", "cybersecurity", "penetration tester", "soc analyst",
            "security architect", "security operations",
        ],
    ),
    (
        "ai_ml_hiring",
        [
            "machine learning engineer", "ml engineer", "ai engineer",
            "artificial intelligence engineer", "nlp engineer", "data scientist",
            "ai researcher", "llm engineer", "computer vision engineer",
            "deep learning", "applied scientist",
        ],
    ),
    (
        "cloud_devops_hiring",
        [
            "devops engineer", "site reliability engineer", "sre",
            "cloud engineer", "platform engineer", "infrastructure engineer",
            "cloud architect", "kubernetes engineer",
        ],
    ),
    (
        "data_hiring",
        [
            "data engineer", "data analyst", "analytics engineer",
            "data platform engineer", "etl developer", "data warehouse engineer",
        ],
    ),
    (
        "engineering_hiring",
        [
            "software engineer", "backend engineer", "frontend engineer",
            "full stack engineer", "full-stack engineer", "engineering manager",
            "staff engineer", "principal engineer", "mobile engineer",
            "software developer",
        ],
    ),
]
GENERAL_HIRING_CATEGORY = "general_hiring"

_TAG_RE = re.compile(r"<[^>]+>")


def classify_hiring_category(title: str, department: str, description_snippet: str) -> str:
    haystack = f"{title} {department} {description_snippet}".lower()
    for category, keywords in _HIRING_CATEGORY_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return category
    return GENERAL_HIRING_CATEGORY


def _strip_html(html: str) -> str:
    return _TAG_RE.sub(" ", html)


@dataclass
class JobPosting:
    """One normalized posting, independent of which ATS it came from."""

    title: str
    department: str | None
    location: str | None
    posted_at: datetime | None
    url: str
    description_snippet: str


@dataclass
class ProviderOutput:
    signals: list[RawSignal] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class JobsBoardProvider(ABC):
    """One ATS's public, unauthenticated job-board API.

    Every provider must degrade gracefully: a missing board (404), a rate
    limit, or a timeout all return a ProviderOutput describing what
    happened rather than raising, so one provider's failure never takes
    the other down with it (see `JobsCollector.collect`) and a 404 in
    particular is recorded with *no* error - it's a legitimate empty
    result, not a problem.
    """

    name: str

    @abstractmethod
    async def fetch(self, board_slug: str, timeout_seconds: float) -> ProviderOutput:
        raise NotImplementedError

    def _build_signals(self, postings: list[JobPosting]) -> list[RawSignal]:
        signals: list[RawSignal] = []
        for posting in postings[:MAX_JOBS_PER_PROVIDER]:
            category = classify_hiring_category(posting.title, posting.department or "", posting.description_snippet)
            signals.append(
                RawSignal(
                    source=SignalSource.JOBS,
                    category=category,
                    payload={
                        "title": posting.title,
                        "department": posting.department,
                        "location": posting.location,
                        "posted_at": posting.posted_at.isoformat() if posting.posted_at else None,
                        "provider": self.name,
                        "description_snippet": posting.description_snippet,
                    },
                    url=posting.url,
                )
            )
        return signals


class GreenhouseProvider(JobsBoardProvider):
    name = "greenhouse"

    async def fetch(self, board_slug: str, timeout_seconds: float) -> ProviderOutput:
        settings = get_settings()
        url = f"{settings.greenhouse_api_base}/{board_slug}/jobs"

        try:
            import httpx
        except Exception as exc:  # noqa: BLE001
            return ProviderOutput(errors=[f"{url}: httpx unavailable ({exc})"])

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(url, params={"content": "true"})
        except httpx.TimeoutException:
            return ProviderOutput(errors=[f"{url}: timeout after {timeout_seconds}s"])
        except Exception as exc:  # noqa: BLE001
            return ProviderOutput(errors=[f"{url}: {exc}"])

        if response.status_code == 404:
            return ProviderOutput()  # legitimate "no board under this name" - not an error
        if response.status_code in (403, 429):
            return ProviderOutput(errors=[f"{url}: {response.status_code} rate limited or blocked"])
        if response.status_code != 200:
            return ProviderOutput(errors=[f"{url}: unexpected status {response.status_code}"])

        try:
            jobs = response.json().get("jobs", [])
        except Exception as exc:  # noqa: BLE001
            return ProviderOutput(errors=[f"{url}: invalid JSON response ({exc})"])

        postings = [self._to_posting(job) for job in jobs]
        return ProviderOutput(signals=self._build_signals(postings))

    @staticmethod
    def _to_posting(job: dict) -> JobPosting:
        departments = job.get("departments") or []
        department = departments[0].get("name") if departments else None
        location = (job.get("location") or {}).get("name")

        posted_at = None
        raw_date = job.get("updated_at")
        if raw_date:
            try:
                posted_at = datetime.fromisoformat(raw_date)
            except ValueError:
                posted_at = None

        description = _strip_html(job.get("content") or "").strip()

        return JobPosting(
            title=job.get("title", "Untitled role"),
            department=department,
            location=location,
            posted_at=posted_at,
            url=job.get("absolute_url", ""),
            description_snippet=description[:MAX_DESCRIPTION_SNIPPET_CHARS],
        )


class LeverProvider(JobsBoardProvider):
    name = "lever"

    async def fetch(self, board_slug: str, timeout_seconds: float) -> ProviderOutput:
        settings = get_settings()
        url = f"{settings.lever_api_base}/{board_slug}"

        try:
            import httpx
        except Exception as exc:  # noqa: BLE001
            return ProviderOutput(errors=[f"{url}: httpx unavailable ({exc})"])

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(url, params={"mode": "json"})
        except httpx.TimeoutException:
            return ProviderOutput(errors=[f"{url}: timeout after {timeout_seconds}s"])
        except Exception as exc:  # noqa: BLE001
            return ProviderOutput(errors=[f"{url}: {exc}"])

        if response.status_code == 404:
            return ProviderOutput()  # legitimate "no board under this name" - not an error
        if response.status_code in (403, 429):
            return ProviderOutput(errors=[f"{url}: {response.status_code} rate limited or blocked"])
        if response.status_code != 200:
            return ProviderOutput(errors=[f"{url}: unexpected status {response.status_code}"])

        try:
            jobs = response.json()
        except Exception as exc:  # noqa: BLE001
            return ProviderOutput(errors=[f"{url}: invalid JSON response ({exc})"])

        if not isinstance(jobs, list):
            return ProviderOutput(errors=[f"{url}: unexpected response shape"])

        postings = [self._to_posting(job) for job in jobs]
        return ProviderOutput(signals=self._build_signals(postings))

    @staticmethod
    def _to_posting(job: dict) -> JobPosting:
        categories = job.get("categories") or {}
        department = categories.get("team")
        location = categories.get("location")

        posted_at = None
        raw_ms = job.get("createdAt")
        if isinstance(raw_ms, (int, float)):
            try:
                posted_at = datetime.fromtimestamp(raw_ms / 1000, tz=UTC)
            except (ValueError, OverflowError, OSError):
                posted_at = None

        description = job.get("descriptionPlain") or _strip_html(job.get("description") or "")

        return JobPosting(
            title=job.get("text", "Untitled role"),
            department=department,
            location=location,
            posted_at=posted_at,
            url=job.get("hostedUrl", ""),
            description_snippet=description.strip()[:MAX_DESCRIPTION_SNIPPET_CHARS],
        )


PROVIDERS: list[type[JobsBoardProvider]] = [GreenhouseProvider, LeverProvider]


class JobsCollector(BaseCollector):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.providers = [provider_cls() for provider_cls in PROVIDERS]

    async def collect(self, company_domain: str) -> CollectorResult:
        if not self.settings.enable_live_jobs:
            logger.info("jobs_collector.stub_mode", domain=company_domain)
            return CollectorResult(
                company_domain=company_domain,
                source=SignalSource.JOBS,
                signals=[],
                is_live=False,
                errors=["Live jobs collection disabled (ENABLE_LIVE_JOBS=false) - ran in stub mode"],
                status=CollectorStatus.NOT_CONFIGURED,
            )

        board_slug = company_domain.split(".")[0]
        timeout = float(self.settings.jobs_timeout_seconds)

        outputs = await asyncio.gather(
            *(provider.fetch(board_slug, timeout) for provider in self.providers),
            return_exceptions=True,
        )

        signals: list[RawSignal] = []
        errors: list[str] = []
        for provider, output in zip(self.providers, outputs, strict=True):
            if isinstance(output, BaseException):
                # A provider that raises despite its own try/except (e.g. an
                # import error) still shouldn't sink the others.
                errors.append(f"{provider.name}: {output}")
                continue
            signals.extend(output.signals)
            errors.extend(output.errors)

        return CollectorResult(
            company_domain=company_domain,
            source=SignalSource.JOBS,
            signals=signals,
            is_live=True,
            errors=errors,
        )
