"""Job Market Source - Uses DuckDuckGo search to find job postings in Bahrain by sector."""

import logging
import re
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


def _match_queries(name_ar):
    for keyword, queries in _JOB_KEYWORD_MAP:
        if keyword in name_ar:
            return queries
    return _DEFAULT_QUERIES


class JobMarketSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "job_market"

    @property
    def reliability_score(self) -> float:
        return 0.6  # Indicative search results

    @property
    def cache_ttl_seconds(self) -> int:
        return 3 * 24 * 3600  # 3 days

    async def fetch(self, sector: str) -> dict:
        name_ar = ""
        try:
            from bahrain_data import get_sectors
            sectors = get_sectors()
            info = sectors.get(sector, {})
            name_ar = info.get("name_ar", "")
        except Exception:
            pass

        queries = _match_queries(name_ar)

        try:
            from duckduckgo_search import DDGS

            all_results = []
            companies_found = set()
            job_titles = []

            with DDGS() as ddgs:
                for query in queries[:2]:  # Limit to 2 queries to be fast
                    try:
                        results = list(ddgs.text(query, max_results=10))
                        all_results.extend(results)
                    except Exception as e:
                        logger.warning(f"DuckDuckGo search failed for '{query}': {e}")

            # Parse results for insights
            for r in all_results:
                title = r.get("title", "")
                body = r.get("body", "")
                link = r.get("link", "")

                # Extract company names from job sites
                if any(site in link for site in ["linkedin.com", "indeed.com", "bayt.com", "naukrigulf.com", "gulftalent.com"]):
                    # Try to extract company from title patterns like "Job Title - Company"
                    parts = re.split(r'\s*[-–|]\s*', title)
                    if len(parts) >= 2:
                        company = parts[-1].strip()
                        if len(company) > 2 and len(company) < 50:
                            companies_found.add(company)
                    job_titles.append(parts[0].strip() if parts else title)

            total_results = len(all_results)
            demand_signal = "high" if total_results > 15 else ("medium" if total_results > 5 else "low")

            return {
                "source": self.source_name,
                "reliability": self.reliability_score,
                "search_queries": queries,
                "total_results": total_results,
                "demand_signal": demand_signal,
                "sample_job_titles": list(set(job_titles))[:10],
                "hiring_companies": list(companies_found)[:10],
                "data_points": max(1, total_results // 5),
                "is_live": True,
                "note": "مؤشرات سوق العمل من نتائج بحث DuckDuckGo (LinkedIn, Indeed, Bayt, إلخ)",
            }

        except ImportError:
            logger.info("duckduckgo_search not installed")
        except Exception as e:
            logger.warning(f"Job market fetch failed: {e}")

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
