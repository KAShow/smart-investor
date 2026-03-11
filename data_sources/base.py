"""Base class for all data sources."""

import abc
import hashlib
import logging

logger = logging.getLogger(__name__)


class DataSourceBase(abc.ABC):
    """Abstract base class for data sources."""

    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this data source."""

    @property
    @abc.abstractmethod
    def reliability_score(self) -> float:
        """Reliability score 0.0-1.0 (1.0 = most reliable)."""

    @property
    def cache_ttl_seconds(self) -> int:
        """Cache time-to-live in seconds. Default: 7 days."""
        return 7 * 24 * 3600

    @abc.abstractmethod
    async def fetch(self, sector: str) -> dict:
        """Fetch data for a given sector. Returns dict with data or empty dict on failure."""

    def get_cache_key(self, sector: str) -> str:
        """Generate a unique cache key for this source + sector."""
        raw = f"{self.source_name}:{sector}"
        return hashlib.md5(raw.encode()).hexdigest()
