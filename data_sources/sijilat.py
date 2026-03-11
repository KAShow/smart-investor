"""Sijilat.io - Bahrain Commercial Registry data (optional, may require API key)."""

import os
import logging
import aiohttp
from .base import DataSourceBase
from .sector_mapping import SECTOR_MAP

logger = logging.getLogger(__name__)


class SijilatSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "sijilat"

    @property
    def reliability_score(self) -> float:
        return 0.7

    @property
    def cache_ttl_seconds(self) -> int:
        return 24 * 3600  # 24 hours

    async def fetch(self, sector: str) -> dict:
        api_key = os.environ.get("SIJILAT_API_KEY", "")
        enabled = os.environ.get("SIJILAT_ENABLED", "false").lower() == "true"

        mapping = SECTOR_MAP.get(sector, {})
        activities = mapping.get("sijilat_activities", [])

        # If API is not enabled, return embedded estimate data
        if not enabled or not api_key:
            return self._get_embedded_data(sector, activities)

        results = {}
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                for activity in activities[:3]:  # Limit to avoid rate limits
                    try:
                        url = f"https://api.sijilat.io/v1/search?q={activity}&country=BH"
                        headers = {"Authorization": f"Bearer {api_key}"}
                        async with session.get(url, headers=headers) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                count = data.get("total", data.get("count", 0))
                                results[activity] = {
                                    "registered_count": count,
                                    "sample": data.get("results", [])[:3],
                                }
                            else:
                                logger.warning(f"Sijilat API returned {resp.status} for '{activity}'")
                    except Exception as e:
                        logger.warning(f"Sijilat fetch failed for '{activity}': {e}")

        except Exception as e:
            logger.error(f"Sijilat session error: {e}")

        if not results:
            return self._get_embedded_data(sector, activities)

        total_companies = sum(r.get("registered_count", 0) for r in results.values())
        return {
            "source": self.source_name,
            "reliability": self.reliability_score,
            "activities": results,
            "total_registered": total_companies,
            "search_terms": activities,
            "data_points": len(results),
            "is_live": True,
        }

    def _get_embedded_data(self, sector: str, activities: list) -> dict:
        """Fallback embedded estimates based on Bahrain market knowledge."""
        estimates = {
            "food_hospitality": {"total_estimate": 3500, "active_estimate": 2800, "annual_new": 200},
            "real_estate": {"total_estimate": 1800, "active_estimate": 1200, "annual_new": 120},
            "technology": {"total_estimate": 800, "active_estimate": 600, "annual_new": 100},
            "finance": {"total_estimate": 400, "active_estimate": 350, "annual_new": 30},
            "manufacturing": {"total_estimate": 600, "active_estimate": 450, "annual_new": 40},
            "health": {"total_estimate": 900, "active_estimate": 700, "annual_new": 60},
            "education": {"total_estimate": 500, "active_estimate": 400, "annual_new": 35},
            "transport": {"total_estimate": 700, "active_estimate": 500, "annual_new": 50},
            "retail": {"total_estimate": 5000, "active_estimate": 3800, "annual_new": 300},
        }

        sector_data = estimates.get(sector, {"total_estimate": 500, "active_estimate": 350, "annual_new": 30})

        return {
            "source": self.source_name,
            "reliability": 0.5,  # Lower reliability for estimates
            "activities": {a: {"registered_count": "تقديري"} for a in activities},
            "total_registered": sector_data["total_estimate"],
            "active_companies": sector_data["active_estimate"],
            "annual_new_registrations": sector_data["annual_new"],
            "search_terms": activities,
            "data_points": 3,
            "is_live": False,
            "note": "بيانات تقديرية — يمكن الحصول على بيانات دقيقة من sijilat.bh",
        }
