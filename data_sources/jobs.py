"""Job Market Source - Uses DuckDuckGo search to find job postings in Bahrain by sector."""

import asyncio
import logging
import random
import re
import time
from .base import DataSourceBase

logger = logging.getLogger(__name__)

# Arabic keyword → job search queries
_JOB_KEYWORD_MAP = [
    ("تشييد", ["construction jobs Bahrain", "وظائف مقاولات البحرين", "civil engineer Bahrain"]),
    ("بناء", ["construction jobs Bahrain", "مقاولات البحرين"]),
    ("مالي", ["banking jobs Bahrain", "finance jobs Bahrain", "وظائف بنوك البحرين"]),
    ("تأمين", ["insurance jobs Bahrain", "وظائف تأمين البحرين"]),
    ("صناع", ["manufacturing jobs Bahrain", "factory jobs Bahrain"]),
    ("تحويل", ["manufacturing jobs Bahrain", "industrial jobs Bahrain"]),
    ("نقل", ["logistics jobs Bahrain", "transport jobs Bahrain", "وظائف شحن البحرين"]),
    ("تخزين", ["warehouse jobs Bahrain", "logistics jobs Bahrain"]),
    ("اتصالات", ["IT jobs Bahrain", "telecom jobs Bahrain"]),
    ("معلومات", ["software developer Bahrain", "IT jobs Bahrain", "وظائف تقنية البحرين"]),
    ("تعليم", ["teaching jobs Bahrain", "education jobs Bahrain", "وظائف تعليم البحرين"]),
    ("صح", ["healthcare jobs Bahrain", "nursing jobs Bahrain", "وظائف طبية البحرين"]),
    ("تجار", ["retail jobs Bahrain", "sales jobs Bahrain"]),
    ("فنادق", ["hotel jobs Bahrain", "hospitality jobs Bahrain"]),
    ("إقامة", ["hotel jobs Bahrain", "hospitality Bahrain"]),
    ("طعام", ["restaurant jobs Bahrain", "chef jobs Bahrain", "وظائف مطاعم البحرين"]),
    ("عقار", ["real estate jobs Bahrain", "property jobs Bahrain"]),
    ("نفط", ["oil gas jobs Bahrain", "petroleum engineer Bahrain"]),
]

_DEFAULT_QUERIES = ["jobs Bahrain", "وظائف البحرين"]

_MAX_RETRIES = 3
_RETRY_DELAYS = [2, 5, 10]  # seconds
_QUERY_DELAY = 1.5  # delay between DuckDuckGo queries


def _match_queries(name_ar):
    for keyword, queries in _JOB_KEYWORD_MAP:
        if keyword in name_ar:
            return queries
    return _DEFAULT_QUERIES


def _fetch_jobs_sync(queries):
    """Synchronous DuckDuckGo fetch — runs in a separate thread."""
    from duckduckgo_search import DDGS

    all_results = []
    companies_found = set()
    job_titles = []

    with DDGS() as ddgs:
        for i, query in enumerate(queries[:2]):
            if i > 0:
                time.sleep(_QUERY_DELAY)
            try:
                results = list(ddgs.text(query, max_results=10))
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"DuckDuckGo search failed for '{query}': {e}")

    # Parse results for insights
    for r in all_results:
        title = r.get("title", "")
        link = r.get("link", "")

        if any(site in link for site in ["linkedin.com", "indeed.com", "bayt.com", "naukrigulf.com", "gulftalent.com"]):
            parts = re.split(r'\s*[-–|]\s*', title)
            if len(parts) >= 2:
                company = parts[-1].strip()
                if 2 < len(company) < 50:
                    companies_found.add(company)
            job_titles.append(parts[0].strip() if parts else title)

    return all_results, list(set(job_titles))[:10], list(companies_found)[:10]


class JobMarketSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "job_market"

    @property
    def reliability_score(self) -> float:
        return 0.6

    @property
    def cache_ttl_seconds(self) -> int:
        return 3 * 24 * 3600  # 3 days

    async def fetch(self, sector: str) -> dict:
        # 1. Check DB cache first
        try:
            from database import get_data_cache, save_data_cache
            cached = get_data_cache(self.source_name, sector)
            if cached:
                logger.info("Job Market: using DB cache")
                return cached
        except Exception:
            pass

        # 2. Get sector Arabic name for keyword matching
        name_ar = ""
        try:
            from bahrain_data import get_sectors
            sectors = get_sectors()
            info = sectors.get(sector, {})
            name_ar = info.get("name_ar", "")
        except Exception:
            pass

        queries = _match_queries(name_ar)

        # 3. Retry with exponential backoff in separate thread
        last_error = None
        for attempt in range(_MAX_RETRIES):
            try:
                all_results, job_titles, companies = await asyncio.to_thread(
                    _fetch_jobs_sync, queries
                )

                total_results = len(all_results)
                demand_signal = "high" if total_results > 15 else ("medium" if total_results > 5 else "low")

                result = {
                    "source": self.source_name,
                    "reliability": self.reliability_score,
                    "search_queries": queries,
                    "total_results": total_results,
                    "demand_signal": demand_signal,
                    "sample_job_titles": job_titles,
                    "hiring_companies": companies,
                    "data_points": max(1, total_results // 5),
                    "is_live": True,
                    "note": "مؤشرات سوق العمل من نتائج بحث DuckDuckGo (LinkedIn, Indeed, Bayt, إلخ)",
                }

                # Save to DB cache on success
                if total_results > 0:
                    try:
                        from database import save_data_cache
                        save_data_cache(self.source_name, sector, result, self.cache_ttl_seconds)
                    except Exception:
                        pass

                return result

            except ImportError:
                logger.info("duckduckgo_search not installed - skipping retries")
                break
            except Exception as e:
                last_error = e
                delay = _RETRY_DELAYS[attempt] + random.uniform(0, 1)
                logger.warning(
                    f"Job Market attempt {attempt + 1}/{_MAX_RETRIES} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(delay)

        logger.warning(f"Job Market: all {_MAX_RETRIES} attempts failed. Last error: {last_error}")

        # 4. Fallback
        return {
            "source": self.source_name,
            "reliability": 0.3,
            "search_queries": queries,
            "total_results": 0,
            "demand_signal": "unknown",
            "sample_job_titles": [],
            "hiring_companies": [],
            "data_points": 0,
            "is_live": False,
            "note": "لم يتم جلب بيانات سوق العمل (فشل البحث)",
        }
