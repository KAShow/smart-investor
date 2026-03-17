"""Mapping between application sectors and external data source classifications."""

SECTOR_MAP = {
    "food_hospitality": {
        "worldbank_indicators": ["NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG", "SP.POP.TOTL", "NE.TRD.GNFS.ZS"],
        "cbb_relevant": True,
        "sijilat_activities": ["مطعم", "مقهى", "كافيتيريا", "تموين", "مخبز", "حلويات", "توريد أغذية"],
        "trading_economics_sector": "GDP from Services",
        "bourse_sector": "Consumer Non-Cyclicals",
        "tamkeen_programs": ["enterprise_support", "training", "business_development"],
        "edb_focus": ["tourism", "food_processing"],
    },
    "real_estate": {
        "worldbank_indicators": ["NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG", "SP.POP.TOTL", "BX.KLT.DINV.CD.WD"],
        "cbb_relevant": True,
        "sijilat_activities": ["عقارات", "مقاولات", "بناء", "تشييد", "مواد بناء", "تطوير عقاري"],
        "trading_economics_sector": "GDP from Construction",
        "bourse_sector": "Real Estate",
        "tamkeen_programs": ["enterprise_support", "business_development"],
        "edb_focus": ["real_estate", "construction"],
    },
    "technology": {
        "worldbank_indicators": ["NY.GDP.MKTP.KD.ZG", "IT.NET.USER.ZS", "IT.CEL.SETS.P2", "GB.XPD.RSDV.GD.ZS"],
        "cbb_relevant": False,
        "sijilat_activities": ["برمجيات", "تقنية معلومات", "اتصالات", "حلول رقمية", "تطبيقات", "استشارات تقنية"],
        "trading_economics_sector": "GDP from Information and Communication",
        "bourse_sector": "Technology",
        "tamkeen_programs": ["enterprise_support", "training", "digital_transformation"],
        "edb_focus": ["ict", "fintech", "digital"],
    },
    "finance": {
        "worldbank_indicators": ["NY.GDP.MKTP.KD.ZG", "FM.LBL.BMNY.GD.ZS", "FP.CPI.TOTL.ZG", "BX.KLT.DINV.CD.WD"],
        "cbb_relevant": True,
        "sijilat_activities": ["خدمات مالية", "تأمين", "صرافة", "وساطة مالية", "استثمار"],
        "trading_economics_sector": "GDP from Financial Intermediation",
        "bourse_sector": "Financials",
        "tamkeen_programs": ["enterprise_support"],
        "edb_focus": ["financial_services", "islamic_finance", "fintech"],
    },
    "manufacturing": {
        "worldbank_indicators": ["NY.GDP.MKTP.KD.ZG", "NV.IND.MANF.ZS", "NE.TRD.GNFS.ZS", "BX.KLT.DINV.CD.WD"],
        "cbb_relevant": False,
        "sijilat_activities": ["مصنع", "تصنيع", "إنتاج", "تعبئة", "تغليف"],
        "trading_economics_sector": "GDP from Manufacturing",
        "bourse_sector": "Industrials",
        "tamkeen_programs": ["enterprise_support", "export_support", "training"],
        "edb_focus": ["manufacturing", "logistics"],
    },
    "health": {
        "worldbank_indicators": ["NY.GDP.MKTP.KD.ZG", "SH.XPD.CHEX.GD.ZS", "SP.POP.TOTL", "SH.MED.PHYS.ZS"],
        "cbb_relevant": False,
        "sijilat_activities": ["مستشفى", "عيادة", "صيدلية", "أجهزة طبية", "مستلزمات طبية", "رعاية صحية"],
        "trading_economics_sector": "GDP from Health and Social Work",
        "bourse_sector": "Healthcare",
        "tamkeen_programs": ["enterprise_support", "training"],
        "edb_focus": ["healthcare"],
    },
    "education": {
        "worldbank_indicators": ["NY.GDP.MKTP.KD.ZG", "SE.XPD.TOTL.GD.ZS", "SP.POP.TOTL", "SL.UEM.TOTL.ZS"],
        "cbb_relevant": False,
        "sijilat_activities": ["مدرسة", "معهد", "تدريب", "تعليم", "حضانة", "دورات"],
        "trading_economics_sector": "GDP from Education",
        "bourse_sector": None,
        "tamkeen_programs": ["enterprise_support", "training", "national_employment"],
        "edb_focus": ["education"],
    },
    "transport": {
        "worldbank_indicators": ["NY.GDP.MKTP.KD.ZG", "IS.SHP.GOOD.TU", "NE.TRD.GNFS.ZS", "BX.KLT.DINV.CD.WD"],
        "cbb_relevant": False,
        "sijilat_activities": ["نقل", "شحن", "لوجستيات", "تخزين", "تخليص جمركي", "توصيل"],
        "trading_economics_sector": "GDP from Transport",
        "bourse_sector": "Industrials",
        "tamkeen_programs": ["enterprise_support", "export_support"],
        "edb_focus": ["logistics", "transport"],
    },
    "retail": {
        "worldbank_indicators": ["NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG", "NE.TRD.GNFS.ZS", "SP.POP.TOTL"],
        "cbb_relevant": True,
        "sijilat_activities": ["تجارة تجزئة", "تجارة جملة", "سوبرماركت", "متجر", "توزيع", "استيراد"],
        "trading_economics_sector": "GDP from Wholesale and Retail Trade",
        "bourse_sector": "Consumer Non-Cyclicals",
        "tamkeen_programs": ["enterprise_support", "training", "export_support"],
        "edb_focus": ["retail", "ecommerce"],
    },
    "ai_applications": {
        "worldbank_indicators": ["NY.GDP.MKTP.KD.ZG", "IT.NET.USER.ZS", "IT.CEL.SETS.P2", "GB.XPD.RSDV.GD.ZS"],
        "cbb_relevant": False,
        "sijilat_activities": ["ذكاء اصطناعي", "تعلم آلي", "تحليل بيانات", "أتمتة", "روبوتات", "برمجيات ذكية"],
        "trading_economics_sector": "GDP from Services",
        "bourse_sector": "Technology",
        "tamkeen_programs": ["enterprise_support", "training", "digital_transformation"],
        "edb_focus": ["ict", "fintech", "digital"],
    },
}

# مؤشرات WorldBank العامة لأي قطاع غير معرّف
_DEFAULT_WB_INDICATORS = ["NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG", "SP.POP.TOTL", "SL.UEM.TOTL.ZS"]


def get_sector_mapping(sector_key):
    """إرجاع mapping القطاع - ثابت إذا موجود، أو مولّد ديناميكياً."""
    if sector_key in SECTOR_MAP:
        return SECTOR_MAP[sector_key]

    # توليد mapping ديناميكي للقطاعات المجلوبة من API
    try:
        from bahrain_data import get_sectors
        sectors = get_sectors()
        sector_info = sectors.get(sector_key, {})
        sijilat_terms = sector_info.get("sijilat_terms", [])
        if not sijilat_terms:
            # توليد من اسم القطاع
            name_ar = sector_info.get("name_ar", "")
            sijilat_terms = [w for w in name_ar.split() if len(w) > 2][:5]
    except Exception:
        sijilat_terms = []

    return {
        "worldbank_indicators": _DEFAULT_WB_INDICATORS,
        "cbb_relevant": False,
        "sijilat_activities": sijilat_terms,
        "trading_economics_sector": "GDP from Services",
        "bourse_sector": None,
        "tamkeen_programs": ["enterprise_support", "training"],
        "edb_focus": [],
    }
