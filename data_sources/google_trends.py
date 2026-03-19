"""Google Trends - Search interest data for Bahrain market demand signals."""

import asyncio
import logging
import random
from .base import DataSourceBase

logger = logging.getLogger(__name__)

# Arabic keyword → Google Trends search terms (English + Arabic)
_GT_KEYWORD_MAP = [
    ("تشييد", ["construction Bahrain", "مقاولات البحرين", "بناء البحرين"]),
    ("بناء", ["construction Bahrain", "building materials Bahrain"]),
    ("مالي", ["banking Bahrain", "insurance Bahrain", "بنوك البحرين"]),
    ("تأمين", ["insurance Bahrain", "تأمين البحرين"]),
    ("صناع", ["manufacturing Bahrain", "factory Bahrain"]),
    ("تحويل", ["manufacturing Bahrain", "صناعة البحرين"]),
    ("نقل", ["logistics Bahrain", "shipping Bahrain", "شحن البحرين"]),
    ("تخزين", ["warehouse Bahrain", "logistics Bahrain"]),
    ("اتصالات", ["IT Bahrain", "telecom Bahrain"]),
    ("معلومات", ["software Bahrain", "IT services Bahrain"]),
    ("تعليم", ["education Bahrain", "school Bahrain", "تعليم البحرين"]),
    ("صح", ["healthcare Bahrain", "hospital Bahrain", "مستشفى البحرين"]),
    ("تجار", ["retail Bahrain", "wholesale Bahrain", "سوبرماركت البحرين"]),
    ("فنادق", ["hotels Bahrain", "tourism Bahrain", "فنادق البحرين"]),
    ("إقامة", ["hotels Bahrain", "tourism Bahrain"]),
    ("طعام", ["restaurant Bahrain", "food delivery Bahrain", "مطاعم البحرين"]),
    ("عقار", ["real estate Bahrain", "عقارات البحرين", "شقق البحرين"]),
    ("زراع", ["farming Bahrain", "agriculture Bahrain"]),
    ("نفط", ["oil gas Bahrain", "energy Bahrain"]),
    ("مياه", ["water treatment Bahrain"]),
    ("كهرباء", ["electricity Bahrain", "solar energy Bahrain"]),
]

_DEFAULT_KEYWORDS = ["business Bahrain", "investment Bahrain", "استثمار البحرين"]

_MAX_RETRIES = 3
_RETRY_DELAYS = [3, 7, 15]  # seconds


def _match_keywords(name_ar):
    for keyword, terms in _GT_KEYWORD_MAP:
        if keyword in name_ar:
            return terms
    return _DEFAULT_KEYWORDS


def _fetch_trends_sync(search_terms):
    """Synchronous pytrends fetch — runs in a separate thread."""
    from pytrends.request import TrendReq

    pytrends = TrendReq(hl='ar', tz=180, timeout=(10, 25))

    pytrends.build_payload(
        search_terms[:5],
        cat=0,
        timeframe='today 12-m',
        geo='BH',
    )

    # Interest over time
    iot = pytrends.interest_over_time()
    trend_data = {}
    if not iot.empty:
        for term in search_terms[:5]:
            if term in iot.columns:
                values = iot[term].tolist()
                avg = sum(values) / len(values) if values else 0
                recent = sum(values[-4:]) / 4 if len(values) >= 4 else avg
                old = sum(values[:4]) / 4 if len(values) >= 4 else avg
                trend = "rising" if recent > old * 1.1 else ("declining" if recent < old * 0.9 else "stable")
                trend_data[term] = {
                    "avg_interest": round(avg, 1),
                    "recent_interest": round(recent, 1),
                    "trend": trend,
                }

    # Related queries
    related = {}
    try:
        rq = pytrends.related_queries()
        for term in search_terms[:3]:
            if term in rq and rq[term].get("rising") is not None:
                rising = rq[term]["rising"]
                if rising is not None and not rising.empty:
                    related[term] = rising["query"].tolist()[:5]
    except Exception:
        pass

    return trend_data, related


class GoogleTrendsSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "google_trends"

    @property
    def reliability_score(self) -> float:
        return 0.65

    @property
    def cache_ttl_seconds(self) -> int:
        return 7 * 24 * 3600  # 7 days

    async def fetch(self, sector: str) -> dict:
        # 1. Check DB cache first
        try:
            from database import get_data_cache, save_data_cache
            cached = get_data_cache(self.source_name, sector)
            if cached:
                logger.info("Google Trends: using DB cache")
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

        search_terms = _match_keywords(name_ar)

        # 3. Retry with exponential backoff in separate thread
        last_error = None
        for attempt in range(_MAX_RETRIES):
            try:
                trend_data, related = await asyncio.to_thread(
                    _fetch_trends_sync, search_terms
                )

                result = {
                    "source": self.source_name,
                    "reliability": self.reliability_score,
                    "search_terms": search_terms,
                    "trends": trend_data,
                    "related_queries": related,
                    "data_points": len(trend_data),
                    "is_live": True,
                    "note": "بيانات اتجاهات البحث من Google Trends (12 شهر أخيرة، البحرين)",
                }

                # Save to DB cache on success
                if len(trend_data) > 0:
                    try:
                        from database import save_data_cache
                        save_data_cache(self.source_name, sector, result, self.cache_ttl_seconds)
                    except Exception:
                        pass

                return result

            except ImportError:
                logger.info("pytrends not installed - skipping retries")
                break
            except Exception as e:
                last_error = e
                delay = _RETRY_DELAYS[attempt] + random.uniform(0, 2)
                logger.warning(
                    f"Google Trends attempt {attempt + 1}/{_MAX_RETRIES} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(delay)

        logger.warning(f"Google Trends: all {_MAX_RETRIES} attempts failed. Last error: {last_error}")

        # 4. Fallback
        return {
            "source": self.source_name,
            "reliability": 0.3,
            "search_terms": search_terms,
            "trends": {},
            "related_queries": {},
            "data_points": 0,
            "is_live": False,
            "note": "لم يتم جلب بيانات Google Trends (pytrends غير مثبت أو فشل الاتصال)",
        }
