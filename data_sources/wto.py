"""WTO / Trade Agreements - Bahrain trade agreements and tariff data (embedded data)."""

import logging
from .base import DataSourceBase

logger = logging.getLogger(__name__)

BAHRAIN_TRADE_AGREEMENTS = {
    "wto_member_since": "1995-01-01",
    "trade_agreements": [
        {"name": "اتفاقية التجارة الحرة البحرينية-الأمريكية", "type": "FTA", "partner": "الولايات المتحدة", "year": 2006, "impact": "إلغاء 100% من الرسوم الجمركية على المنتجات الصناعية"},
        {"name": "منطقة التجارة الحرة الخليجية (GAFTA)", "type": "customs_union", "partner": "دول مجلس التعاون", "year": 2003, "impact": "تعريفة خارجية موحدة 5% + إعفاء داخلي كامل"},
        {"name": "اتفاقية منطقة التجارة العربية الكبرى", "type": "FTA", "partner": "22 دولة عربية", "year": 2005, "impact": "إلغاء تدريجي للرسوم على المنتجات العربية"},
        {"name": "اتفاقية EFTA", "type": "FTA", "partner": "سويسرا، النرويج، أيسلندا، ليختنشتاين", "year": 2014, "impact": "تخفيض رسوم جمركية متبادل"},
        {"name": "اتفاقية سنغافورة", "type": "FTA", "partner": "سنغافورة", "year": 2019, "impact": "إلغاء رسوم على معظم السلع"},
    ],
    "tariff_overview": {
        "avg_applied_tariff_pct": 5.0,
        "avg_tariff_agriculture_pct": 5.5,
        "avg_tariff_industrial_pct": 4.8,
        "duty_free_lines_pct": 35.7,
        "vat_rate_pct": 10,
        "vat_effective_date": "2022-01-01",
    },
    "trade_facilitation": {
        "ease_of_trading_rank": 48,
        "time_to_import_days": 4,
        "time_to_export_days": 5,
        "documents_to_import": 4,
        "documents_to_export": 3,
    },
    "bilateral_investment_treaties": 50,
    "double_taxation_agreements": 44,
}

# Sector-specific trade agreement relevance
SECTOR_AGREEMENT_RELEVANCE = {
    "technology": ["اتفاقية التجارة الحرة البحرينية-الأمريكية", "اتفاقية سنغافورة"],
    "manufacturing": ["منطقة التجارة الحرة الخليجية (GAFTA)", "اتفاقية التجارة الحرة البحرينية-الأمريكية", "اتفاقية EFTA"],
    "retail": ["منطقة التجارة الحرة الخليجية (GAFTA)", "اتفاقية منطقة التجارة العربية الكبرى"],
    "food_hospitality": ["منطقة التجارة الحرة الخليجية (GAFTA)", "اتفاقية منطقة التجارة العربية الكبرى"],
    "construction": ["منطقة التجارة الحرة الخليجية (GAFTA)"],
    "health": ["اتفاقية التجارة الحرة البحرينية-الأمريكية", "اتفاقية EFTA"],
    "transport": ["منطقة التجارة الحرة الخليجية (GAFTA)"],
    "finance": ["اتفاقية التجارة الحرة البحرينية-الأمريكية", "اتفاقية سنغافورة"],
}


class WTOSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "wto"

    @property
    def reliability_score(self) -> float:
        return 0.80

    @property
    def cache_ttl_seconds(self) -> int:
        return 90 * 24 * 3600  # 90 days

    async def fetch(self, sector: str) -> dict:
        relevant_agreement_names = SECTOR_AGREEMENT_RELEVANCE.get(sector, [])

        # Filter agreements relevant to the sector
        relevant_agreements = [
            a for a in BAHRAIN_TRADE_AGREEMENTS["trade_agreements"]
            if a["name"] in relevant_agreement_names
        ] if relevant_agreement_names else BAHRAIN_TRADE_AGREEMENTS["trade_agreements"]

        data_points = (
            1  # wto_member_since
            + len(relevant_agreements)
            + len(BAHRAIN_TRADE_AGREEMENTS["tariff_overview"])
            + len(BAHRAIN_TRADE_AGREEMENTS["trade_facilitation"])
            + 2  # bilateral_investment_treaties + double_taxation_agreements
        )

        return {
            "source": self.source_name,
            "reliability": self.reliability_score,
            "wto_member_since": BAHRAIN_TRADE_AGREEMENTS["wto_member_since"],
            "relevant_trade_agreements": relevant_agreements,
            "total_trade_agreements": len(BAHRAIN_TRADE_AGREEMENTS["trade_agreements"]),
            "tariff_overview": BAHRAIN_TRADE_AGREEMENTS["tariff_overview"],
            "trade_facilitation": BAHRAIN_TRADE_AGREEMENTS["trade_facilitation"],
            "bilateral_investment_treaties": BAHRAIN_TRADE_AGREEMENTS["bilateral_investment_treaties"],
            "double_taxation_agreements": BAHRAIN_TRADE_AGREEMENTS["double_taxation_agreements"],
            "data_points": data_points,
        }
