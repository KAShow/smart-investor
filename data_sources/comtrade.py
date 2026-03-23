"""UN Comtrade - International trade data for Bahrain (embedded data)."""

import logging
from .base import DataSourceBase

logger = logging.getLogger(__name__)

# Bahrain trade data (source: UN Comtrade / ITC Trade Map, 2023)
BAHRAIN_TRADE = {
    "total_imports_2023": {"value_usd": 15_557_000_000, "year": 2023},
    "total_exports_2023": {"value_usd": 22_800_000_000, "year": 2023},
    "trade_balance_2023": {"value_usd": 7_243_000_000, "surplus": True},
    "top_import_partners": [
        {"country": "الصين", "share_pct": 14.3},
        {"country": "الاتحاد الأوروبي", "share_pct": 14.3},
        {"country": "أستراليا", "share_pct": 9.6},
        {"country": "السعودية", "share_pct": 8.5},
        {"country": "الإمارات", "share_pct": 7.2},
        {"country": "اليابان", "share_pct": 5.1},
        {"country": "الهند", "share_pct": 4.8},
        {"country": "الولايات المتحدة", "share_pct": 3.9},
    ],
    "top_export_partners": [
        {"country": "السعودية", "share_pct": 18.2},
        {"country": "الإمارات", "share_pct": 12.5},
        {"country": "الولايات المتحدة", "share_pct": 8.1},
        {"country": "اليابان", "share_pct": 5.9},
        {"country": "الهند", "share_pct": 5.4},
    ],
    "top_import_sectors": [
        {"sector": "آلات ومعدات", "share_pct": 15.2, "value_usd": 2_365_000_000},
        {"sector": "معادن أساسية (ألمنيوم/حديد)", "share_pct": 12.8, "value_usd": 1_991_000_000},
        {"sector": "سيارات ومركبات", "share_pct": 9.4, "value_usd": 1_462_000_000},
        {"sector": "منتجات كيميائية", "share_pct": 8.1, "value_usd": 1_260_000_000},
        {"sector": "مواد غذائية", "share_pct": 7.6, "value_usd": 1_182_000_000},
        {"sector": "إلكترونيات وأجهزة", "share_pct": 6.9, "value_usd": 1_073_000_000},
        {"sector": "مواد بناء", "share_pct": 5.3, "value_usd": 825_000_000},
        {"sector": "منسوجات وملابس", "share_pct": 3.8, "value_usd": 591_000_000},
    ],
    "top_export_sectors": [
        {"sector": "ألمنيوم ومنتجاته", "share_pct": 25.3, "value_usd": 5_768_000_000},
        {"sector": "نفط ومشتقاته", "share_pct": 22.1, "value_usd": 5_039_000_000},
        {"sector": "منتجات بتروكيماوية", "share_pct": 12.5, "value_usd": 2_850_000_000},
        {"sector": "حديد وصلب", "share_pct": 8.2, "value_usd": 1_870_000_000},
        {"sector": "خدمات مالية (إعادة تصدير)", "share_pct": 6.4, "value_usd": 1_459_000_000},
    ],
}

# Maps project sectors to relevant import/export trade categories
SECTOR_TRADE_RELEVANCE = {
    "construction": {"import_sectors": ["مواد بناء", "معادن أساسية"], "export_sectors": ["حديد وصلب"]},
    "food_hospitality": {"import_sectors": ["مواد غذائية"], "export_sectors": []},
    "technology": {"import_sectors": ["إلكترونيات وأجهزة", "آلات ومعدات"], "export_sectors": []},
    "manufacturing": {"import_sectors": ["آلات ومعدات", "معادن أساسية"], "export_sectors": ["ألمنيوم ومنتجاته", "حديد وصلب"]},
    "retail": {"import_sectors": ["منسوجات وملابس", "إلكترونيات وأجهزة", "مواد غذائية"], "export_sectors": []},
    "transport": {"import_sectors": ["سيارات ومركبات"], "export_sectors": []},
    "health": {"import_sectors": ["منتجات كيميائية"], "export_sectors": []},
}


class ComtradeSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "comtrade"

    @property
    def reliability_score(self) -> float:
        return 0.80

    @property
    def cache_ttl_seconds(self) -> int:
        return 30 * 24 * 3600  # 30 days

    async def fetch(self, sector: str) -> dict:
        relevance = SECTOR_TRADE_RELEVANCE.get(sector, {})
        relevant_import_names = relevance.get("import_sectors", [])
        relevant_export_names = relevance.get("export_sectors", [])

        # Filter import sectors by relevance (partial match to handle parenthetical names)
        filtered_imports = [
            s for s in BAHRAIN_TRADE["top_import_sectors"]
            if any(name in s["sector"] for name in relevant_import_names)
        ] if relevant_import_names else BAHRAIN_TRADE["top_import_sectors"]

        # Filter export sectors by relevance
        filtered_exports = [
            s for s in BAHRAIN_TRADE["top_export_sectors"]
            if any(name in s["sector"] for name in relevant_export_names)
        ] if relevant_export_names else BAHRAIN_TRADE["top_export_sectors"]

        data_points = (
            1  # total_imports
            + 1  # total_exports
            + 1  # trade_balance
            + len(BAHRAIN_TRADE["top_import_partners"])
            + len(BAHRAIN_TRADE["top_export_partners"])
            + len(filtered_imports)
            + len(filtered_exports)
        )

        return {
            "source": self.source_name,
            "reliability": self.reliability_score,
            "total_imports_2023": BAHRAIN_TRADE["total_imports_2023"],
            "total_exports_2023": BAHRAIN_TRADE["total_exports_2023"],
            "trade_balance_2023": BAHRAIN_TRADE["trade_balance_2023"],
            "top_import_partners": BAHRAIN_TRADE["top_import_partners"],
            "top_export_partners": BAHRAIN_TRADE["top_export_partners"],
            "sector_relevant_imports": filtered_imports,
            "sector_relevant_exports": filtered_exports,
            "data_points": data_points,
        }
