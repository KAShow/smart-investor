"""Bahrain Bourse - Listed companies and market data."""

import logging
from .base import DataSourceBase
from .sector_mapping import SECTOR_MAP

logger = logging.getLogger(__name__)

# Embedded Bahrain Bourse data (from bahrainbourse.com)
BOURSE_SECTORS = {
    "Financials": {
        "name_ar": "القطاع المالي",
        "listed_companies": 12,
        "major_companies": ["بنك البحرين الوطني", "بنك البحرين والكويت", "مجموعة GFH", "بنك الإثمار"],
        "market_cap_approx": "8.5 مليار د.ب",
    },
    "Industrials": {
        "name_ar": "القطاع الصناعي",
        "listed_companies": 5,
        "major_companies": ["ألبا (ألمنيوم البحرين)", "بتلكو"],
        "market_cap_approx": "3.2 مليار د.ب",
    },
    "Consumer Non-Cyclicals": {
        "name_ar": "السلع الاستهلاكية",
        "listed_companies": 4,
        "major_companies": ["دلمون للدواجن", "البحرين للمواد الغذائية"],
        "market_cap_approx": "0.3 مليار د.ب",
    },
    "Real Estate": {
        "name_ar": "العقارات",
        "listed_companies": 5,
        "major_companies": ["ديار المحرق", "مرفأ البحرين", "منشآت"],
        "market_cap_approx": "1.2 مليار د.ب",
    },
    "Healthcare": {
        "name_ar": "الرعاية الصحية",
        "listed_companies": 1,
        "major_companies": ["المستشفى الأهلي"],
        "market_cap_approx": "0.05 مليار د.ب",
    },
    "Technology": {
        "name_ar": "التقنية",
        "listed_companies": 1,
        "major_companies": ["بتلكو"],
        "market_cap_approx": "0.8 مليار د.ب",
    },
}

BOURSE_OVERVIEW = {
    "total_listed": 42,
    "market_cap_total": "13+ مليار د.ب",
    "index_name": "Bahrain All Share Index",
    "foreign_ownership_allowed": True,
    "trading_hours": "9:30 - 13:00 (أحد - خميس)",
}


class BahrainBourseSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "bahrain_bourse"

    @property
    def reliability_score(self) -> float:
        return 0.85

    @property
    def cache_ttl_seconds(self) -> int:
        return 24 * 3600  # 1 day

    async def fetch(self, sector: str) -> dict:
        mapping = SECTOR_MAP.get(sector, {})
        bourse_sector = mapping.get("bourse_sector")

        sector_data = None
        if bourse_sector and bourse_sector in BOURSE_SECTORS:
            sector_data = BOURSE_SECTORS[bourse_sector]

        return {
            "source": self.source_name,
            "reliability": self.reliability_score,
            "overview": BOURSE_OVERVIEW,
            "sector_data": sector_data,
            "sector_name": bourse_sector,
            "data_points": 3 if sector_data else 1,
            "note": "بيانات من بورصة البحرين (bahrainbourse.com)",
        }
