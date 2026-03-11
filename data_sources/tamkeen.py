"""Tamkeen (Labour Fund) - Support programs and training data."""

import logging
from .base import DataSourceBase
from .sector_mapping import SECTOR_MAP

logger = logging.getLogger(__name__)

# Tamkeen programs data (semi-static, updated from tamkeen.bh periodically)
TAMKEEN_PROGRAMS = {
    "enterprise_support": {
        "name_ar": "دعم المؤسسات",
        "description": "دعم مالي للمؤسسات الصغيرة والمتوسطة يغطي حتى 50% من تكاليف التطوير",
        "max_support": "50,000 د.ب",
        "coverage": "حتى 50% من التكاليف المؤهلة",
        "eligible": "مؤسسات بحرينية مسجلة في سجلات وزارة الصناعة",
        "duration": "12-24 شهر",
    },
    "training": {
        "name_ar": "برامج التدريب",
        "description": "دعم تدريب وتأهيل الموظفين البحرينيين",
        "max_support": "مختلف حسب البرنامج",
        "coverage": "حتى 100% من تكاليف التدريب للبحرينيين",
        "eligible": "مؤسسات توظف بحرينيين",
    },
    "business_development": {
        "name_ar": "تطوير الأعمال",
        "description": "استشارات وخدمات تطوير أعمال مدعومة",
        "max_support": "يختلف",
        "coverage": "دعم استشاري + مالي",
    },
    "digital_transformation": {
        "name_ar": "التحول الرقمي",
        "description": "دعم رقمنة الأعمال وتبني التقنيات الحديثة",
        "max_support": "10,000-30,000 د.ب",
        "coverage": "حتى 80% من تكاليف الرقمنة",
    },
    "export_support": {
        "name_ar": "دعم التصدير",
        "description": "دعم المؤسسات الراغبة في التصدير لأسواق جديدة",
        "max_support": "يختلف",
        "coverage": "دعم مشاركة في معارض + استشارات تصدير",
    },
    "national_employment": {
        "name_ar": "دعم التوظيف الوطني",
        "description": "دعم رواتب الموظفين البحرينيين الجدد",
        "max_support": "70% من الراتب لمدة 3 سنوات",
        "coverage": "دعم تدريجي متناقص",
    },
}

# Sijilli (سجلي) - virtual commercial registration
SIJILLI_DATA = {
    "name_ar": "سجلي (التسجيل التجاري الافتراضي)",
    "total_activities": 71,
    "description": "نظام تسجيل تجاري افتراضي يسمح بممارسة 71 نشاطاً تجارياً من المنزل بدون حاجة لعنوان تجاري",
    "annual_fee": "50 د.ب",
    "requirements": ["بطاقة هوية بحرينية أو إقامة سارية", "لا يشترط عنوان تجاري", "تسجيل إلكتروني عبر sijilat.bh"],
    "benefits": ["تكلفة منخفضة جداً", "لا حاجة لمكتب", "إجراءات إلكترونية بالكامل", "مناسب للوساطة التجارية"],
    "sample_activities": [
        "وساطة تجارية",
        "تسويق إلكتروني",
        "استشارات أعمال",
        "تجارة إلكترونية",
        "خدمات تقنية معلومات",
        "تصميم جرافيك",
        "كتابة محتوى",
    ],
}


class TamkeenSource(DataSourceBase):

    @property
    def source_name(self) -> str:
        return "tamkeen"

    @property
    def reliability_score(self) -> float:
        return 0.8

    @property
    def cache_ttl_seconds(self) -> int:
        return 30 * 24 * 3600  # 30 days (semi-static)

    async def fetch(self, sector: str) -> dict:
        mapping = SECTOR_MAP.get(sector, {})
        relevant_programs = mapping.get("tamkeen_programs", ["enterprise_support"])

        programs = {}
        for prog_key in relevant_programs:
            if prog_key in TAMKEEN_PROGRAMS:
                programs[prog_key] = TAMKEEN_PROGRAMS[prog_key]

        return {
            "source": self.source_name,
            "reliability": self.reliability_score,
            "programs": programs,
            "sijilli": SIJILLI_DATA,
            "data_points": len(programs) + 1,
            "note": "بيانات من tamkeen.bh — يُنصح بالتحقق من أحدث الشروط والمتطلبات",
        }
