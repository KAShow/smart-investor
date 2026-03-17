"""EDB (Economic Development Board) - Annual reports and strategic data."""

import logging
from .base import DataSourceBase
from .sector_mapping import SECTOR_MAP

logger = logging.getLogger(__name__)

# EDB key statistics (from bahrainedb.com annual reports)
EDB_DATA = {
    "overview": {
        "gdp_2023": "43.6 مليار دولار",
        "gdp_growth_2023": "2.7%",
        "population": "1.5 مليون نسمة",
        "workforce": "800,000+",
        "bahraini_workforce_pct": "~25%",
        "ease_of_business_rank": "أفضل 50 عالمياً",
        "economic_freedom_rank": "الأول عربياً (2024)",
        "internet_penetration": "99%+",
        "smartphone_penetration": "95%+",
    },
    "sector_focus": {
        "financial_services": {
            "name_ar": "خدمات مالية",
            "contribution_gdp": "16.5%",
            "companies": "400+ مؤسسة مالية مرخصة",
            "fintech": "50+ شركة فنتك",
            "highlights": ["أول بيئة تجريبية للفنتك في المنطقة", "مركز مالي إسلامي رائد"],
        },
        "ict": {
            "name_ar": "تقنية المعلومات والاتصالات",
            "contribution_gdp": "3.5%",
            "companies": "800+",
            "highlights": ["أعلى نسبة إنترنت في الخليج", "مركز بيانات AWS", "5G coverage"],
        },
        "tourism": {
            "name_ar": "سياحة وضيافة",
            "visitors_2023": "11.2 مليون زائر",
            "hotels": "200+ فندق ومنتجع",
            "highlights": ["جسر الملك فهد (25 مليون عبور سنوياً)", "سباق الفورمولا 1"],
        },
        "manufacturing": {
            "name_ar": "صناعة",
            "contribution_gdp": "14%",
            "highlights": ["ألبا (أكبر مصهر ألمنيوم)", "صناعات بتروكيماوية", "منطقة بحرين الاستثمارية"],
        },
        "logistics": {
            "name_ar": "لوجستيات ونقل",
            "highlights": ["ميناء خليفة بن سلمان", "مطار البحرين الدولي الجديد", "موقع استراتيجي وسط الخليج"],
        },
        "real_estate": {
            "name_ar": "عقارات",
            "highlights": ["مشاريع ضخمة (ديار المحرق، مرفأ البحرين)", "قوانين تملك أجانب"],
        },
        "healthcare": {
            "name_ar": "رعاية صحية",
            "highlights": ["تأمين صحي إلزامي (صحتي)", "سياحة علاجية متنامية"],
        },
        "education": {
            "name_ar": "تعليم",
            "highlights": ["جامعات دولية", "مركز تدريب إقليمي"],
        },
    },
    "investment_incentives": {
        "tax_free": "لا ضريبة دخل شخصية",
        "corporate_tax": "لا ضريبة أرباح (باستثناء النفط والغاز)",
        "vat": "10% ضريبة قيمة مضافة (2024)",
        "free_zones": "منطقة البحرين الاستثمارية (100% ملكية أجنبية)",
        "double_taxation": "50+ اتفاقية تجنب ازدواج ضريبي",
        "company_setup": "يوم واحد لتأسيس شركة (Sijilat)",
    },
}

# Sector-to-EDB mapping
SECTOR_EDB_MAP = {
    "food_hospitality": ["tourism"],
    "real_estate": ["real_estate"],
    "technology": ["ict"],
    "finance": ["financial_services"],
    "manufacturing": ["manufacturing"],
    "health": ["healthcare"],
    "education": ["education"],
    "transport": ["logistics"],
    "retail": ["tourism"],  # Retail benefits from tourism
    "ai_applications": ["ict"],
    "energy_environment": ["manufacturing"],
    "media_entertainment": ["tourism"],
    "agriculture": [],
    "professional_services": ["financial_services"],
    "tourism_travel": ["tourism"],
    "sports_fitness": ["tourism"],
    "beauty_personal": [],
    "automotive": [],
    "security_safety": [],
    "cleaning_maintenance": [],
    "events_weddings": ["tourism"],
    "pet_services": [],
    "printing_packaging": ["manufacturing"],
    "recycling_waste": [],
}


class EDBSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "edb"

    @property
    def reliability_score(self) -> float:
        return 0.8

    @property
    def cache_ttl_seconds(self) -> int:
        return 90 * 24 * 3600  # 90 days (annual reports)

    async def fetch(self, sector: str) -> dict:
        edb_sectors = SECTOR_EDB_MAP.get(sector, [])

        sector_details = {}
        for s in edb_sectors:
            if s in EDB_DATA["sector_focus"]:
                sector_details[s] = EDB_DATA["sector_focus"][s]

        return {
            "source": self.source_name,
            "reliability": self.reliability_score,
            "overview": EDB_DATA["overview"],
            "sector_details": sector_details,
            "investment_incentives": EDB_DATA["investment_incentives"],
            "data_points": 3 + len(sector_details),
            "note": "بيانات من تقارير مجلس التنمية الاقتصادية السنوية (bahrainedb.com)",
        }
