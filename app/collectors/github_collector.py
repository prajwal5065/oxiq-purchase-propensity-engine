"""GitHub Collector - repository count, stars, recent commit activity,
languages, and AI/ML-flagged projects for a company's GitHub presence.

Unlike Search/Website/Tech, this needs no API key - GitHub's REST API is
usable unauthenticated (60 requests/hour). `github_token`, if set, just
raises that ceiling; its absence is not a reason to run in stub mode the
way a missing Tavily/Anthropic key is. Still gated behind
`enable_live_github` for consistency with every other collector defaulting
to stub mode until explicitly turned on.

There's no reliable public mapping from a company domain to a GitHub
org/user login, so this collector guesses (the part before the first '.'
in the domain) and treats a 404 on that guess as a legitimate NO_RESULTS -
"this company doesn't have a discoverable GitHub org under this name" is a
real, useful answer, not a failure.
"""
from app.collectors.base import BaseCollector
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.signal import SignalSource
from app.schemas.signal import CollectorResult, CollectorStatus, RawSignal

logger = get_logger(__name__)

# A repo whose name/description/topics contain any of these is flagged as
# an AI/ML project - a stronger "digital maturity" / "org readiness" signal
# than an ordinary repo.
AI_KEYWORDS = {
    "ai", "ml", "machine-learning", "llm", "gpt", "genai",
    "artificial-intelligence", "neural", "nlp", "deep-learning",
}

MAX_REPOS = 10


class GitHubCollector(BaseCollector):
    def __init__(self) -> None:
        self.settings = get_settings()

    async def collect(self, company_domain: str) -> CollectorResult:
        if not self.settings.enable_live_github:
            logger.info("github_collector.stub_mode", domain=company_domain)
            return CollectorResult(
                company_domain=company_domain,
                source=SignalSource.GITHUB,
                signals=[],
                is_live=False,
                errors=["Live GitHub collection disabled (ENABLE_LIVE_GITHUB=false) - ran in stub mode"],
                status=CollectorStatus.NOT_CONFIGURED,
            )

        signals: list[RawSignal] = []
        errors: list[str] = []
        login_guess = company_domain.split(".")[0]

        try:
            import httpx

            headers = {"Accept": "application/vnd.github+json"}
            if self.settings.github_token:
                headers["Authorization"] = f"Bearer {self.settings.github_token}"

            async with httpx.AsyncClient(
                base_url=self.settings.github_api_base, headers=headers, timeout=15.0
            ) as client:
                account = await self._resolve_account(client, login_guess, errors)
                if account is None:
                    return CollectorResult(
                        company_domain=company_domain,
                        source=SignalSource.GITHUB,
                        signals=[],
                        is_live=True,
                        errors=errors,
                    )

                repos = await self._fetch_repos(client, account["login"], account["kind"], errors)
                signals.extend(self._build_signals(account, repos))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"github_client_init: {exc}")

        return CollectorResult(
            company_domain=company_domain,
            source=SignalSource.GITHUB,
            signals=signals,
            is_live=True,
            errors=errors,
        )

    async def _resolve_account(self, client, login: str, errors: list[str]) -> dict | None:
        """Try org first (companies are more often orgs than users), then
        user. A 404 on both is a legitimate empty result, not an error."""
        for kind, path in (("org", f"/orgs/{login}"), ("user", f"/users/{login}")):
            try:
                response = await client.get(path)
                if response.status_code == 200:
                    data = response.json()
                    return {"login": data.get("login", login), "kind": kind, "html_url": data.get("html_url")}
                if response.status_code == 404:
                    continue
                if response.status_code in (403, 429):
                    errors.append(f"{path}: {response.status_code} rate limited or blocked")
                    return None
                errors.append(f"{path}: unexpected status {response.status_code}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{path}: {exc}")
        return None

    async def _fetch_repos(self, client, login: str, kind: str, errors: list[str]) -> list[dict]:
        path = f"/orgs/{login}/repos" if kind == "org" else f"/users/{login}/repos"
        try:
            response = await client.get(path, params={"sort": "pushed", "per_page": MAX_REPOS})
            if response.status_code == 200:
                return response.json()
            errors.append(f"{path}: unexpected status {response.status_code}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path}: {exc}")
        return []

    def _build_signals(self, account: dict, repos: list[dict]) -> list[RawSignal]:
        if not repos:
            return []

        signals: list[RawSignal] = []
        total_stars = sum(r.get("stargazers_count", 0) for r in repos)
        languages = sorted({r["language"] for r in repos if r.get("language")})

        signals.append(
            RawSignal(
                source=SignalSource.GITHUB,
                category="engineering_activity",
                payload={
                    "login": account["login"],
                    "repo_count": len(repos),
                    "total_stars": total_stars,
                    "most_recent_push": repos[0].get("pushed_at") if repos else None,
                },
                url=account.get("html_url"),
            )
        )

        if languages:
            signals.append(
                RawSignal(
                    source=SignalSource.GITHUB,
                    category="languages",
                    payload={"languages": languages},
                    url=account.get("html_url"),
                )
            )

        for repo in repos:
            haystack = " ".join(
                filter(None, [repo.get("name", ""), repo.get("description", ""), " ".join(repo.get("topics", []) or [])])
            ).lower()
            if any(keyword in haystack for keyword in AI_KEYWORDS):
                signals.append(
                    RawSignal(
                        source=SignalSource.GITHUB,
                        category="ai_projects",
                        payload={
                            "name": repo.get("name"),
                            "description": repo.get("description"),
                            "stars": repo.get("stargazers_count", 0),
                        },
                        url=repo.get("html_url"),
                    )
                )

        return signals
