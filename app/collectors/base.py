"""Base interface every Signal Collector must implement.

Collectors are independently testable and independently runnable: each one
takes a company domain and returns a CollectorResult, never raising on a
missing API key or a live-call failure - it degrades to stub mode / records
the error in `CollectorResult.errors` instead, so the orchestrator can keep
going with partial data.
"""
from abc import ABC, abstractmethod

from app.schemas.signal import CollectorResult


class BaseCollector(ABC):
    """All collectors are async and side-effect-free beyond their own I/O."""

    @abstractmethod
    async def collect(self, company_domain: str) -> CollectorResult:
        """Fetch and normalize signals for a single company domain."""
        raise NotImplementedError
