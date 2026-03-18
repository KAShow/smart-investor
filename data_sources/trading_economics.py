"""Trading Economics - Macro indicators (optional, requires paid API key)."""

import os
import logging
import aiohttp
from .base import DataSourceBase
from .sector_mapping import SECTOR_MAP, get_sector_mapping

logger = logging.getLogger(__name__)

# Embedded fallback data (free snapshot from tradingeconomics.com)
BAHRAIN_MACRO = {
    "gdp": {"value": "43.6 مليار دولار", "year": 2023},
    "gdp_growth": {"value": "2.7%", "year": 2023},
    "gdp_per_capita": {"value": "29,000 دولار", "year": 2023},
    "inflation": {"value": "1.0%", "year": 2024},
    "unemployment": {"value": "5.0%", "year": 2023},
    "population": {"value": "1.5 مليون", "year": 2024},
    "interest_rate": {"value": "6.0%", "year": 2024},
    "trade_balance": {"value": "-1.2 مليار دولار", "year": 2023},
    "government_debt_gdp": {"value": "123%", "year": 2023},
    "current_account_gdp": {"value": "5.7%", "year": 2023},
}

SECTOR_GDP_BREAKDOWN = {
    "GDP from Services": {"value": "59%", "note": "القطاع الأكبر"},
    "GDP from Financial Intermediation": {"value": "16.5%", "note": "مركز مالي إقليمي"},
    "GDP from Manufacturing": {"value": "14%", "note": "ألمنيوم وبتروكيماويات"},
    "GDP from Construction": {"value": "6%", "note": "مشاريع بنية تحتية"},
    "GDP from Transport": {"value": "4%", "note": "شامل الاتصالات"},
    "GDP from Public Administration": {"value": "10%", "note": "شامل صحة وتعليم"},
    "GDP from Wholesale and Retail Trade": {"value": "5%", "note": "تجارة داخلية"},
    "GDP from Education": {"value": "2%", "note": ""},
}


class TradingEconomicsSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "trading_economics"

    @property
    def reliability_score(self) -> float:
        return 0.85

    @property
    def cache_ttl_seconds(self) -> int:
        return 7 * 24 * 3600  # 7 days

    async def fetch(self, sector: str) -> dict:
        api_key = os.environ.get("TRADING_ECONOMICS_API_KEY", "")
        enabled = os.environ.get("TRADING_ECONOMICS_ENABLED", "false").lower() == "true"

        mapping = get_sector_mapping(sector)
        te_sector = mapping.get("trading_economics_sector", "")

        # If API is available, try live data
        if enabled and api_key:
            try:
                return await self._fetch_live(api_key, te_sector)
            except Exception as e:
                logger.warning(f"Trading Economics live fetch failed, using embedded: {e}")

        # Fallback to embedded data
        sector_gdp = SECTOR_GDP_BREAKDOWN.get(te_sector, {})

        return {
            "source": self.source_name,
            "reliability": 0.7,  # Lower for embedded
            "macro": BAHRAIN_MACRO,
            "sector_gdp": {
                "sector_name": te_sector,
                "contribution": sector_gdp.get("value", "غير متوفر"),
                "note": sector_gdp.get("note", ""),
            },
            "gdp_breakdown": SECTOR_GDP_BREAKDOWN,
            "data_points": len(BAHRAIN_MACRO) + 1,
            "is_live": False,
            "note": "بيانات ماكرو اقتصادية تقديرية — يمكن تفعيل بيانات حية من Trading Economics",
        }

    async def _fetch_live(self, api_key: str, sector: str) -> dict:
        """Fetch live data from Trading Economics API."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            url = f"https://api.tradingeconomics.com/country/bahrain?c={api_key}&f=json"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    indicators = {}
                    for item in data:
                        cat = item.get("Category", "")
                        indicators[cat] = {
                            "value": item.get("LatestValue"),
                            "date": item.get("LatestValueDate"),
                            "unit": item.get("Unit"),
                        }
                    return {
                        "source": self.source_name,
                        "reliability": self.reliability_score,
                        "indicators": indicators,
                        "data_points": len(indicators),
                        "is_live": True,
                    }
                raise Exception(f"API returned {resp.status}")
