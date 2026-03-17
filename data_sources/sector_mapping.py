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

# ── مؤشرات WorldBank العامة ──
_DEFAULT_WB_INDICATORS = ["NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG", "SP.POP.TOTL", "SL.UEM.TOTL.ZS"]

# ── Keyword-based maps for dynamic sector resolution ──
# Arabic keyword substring → Trading Economics GDP category
_TE_KEYWORD_MAP = [
    ("صناع", "GDP from Manufacturing"),
    ("تحويل", "GDP from Manufacturing"),
    ("تشييد", "GDP from Construction"),
    ("بناء", "GDP from Construction"),
    ("مالي", "GDP from Financial Intermediation"),
    ("تأمين", "GDP from Financial Intermediation"),
    ("مصرف", "GDP from Financial Intermediation"),
    ("نقل", "GDP from Transport"),
    ("مواصلات", "GDP from Transport"),
    ("تخزين", "GDP from Transport"),
    ("اتصالات", "GDP from Information and Communication"),
    ("معلومات", "GDP from Information and Communication"),
    ("تعليم", "GDP from Education"),
    ("صرف صحي", "GDP from Electricity and Water"),  # before صح
    ("مياه", "GDP from Electricity and Water"),       # before صح
    ("مياة", "GDP from Electricity and Water"),       # before صح
    ("صح", "GDP from Health and Social Work"),
    ("اجتماع", "GDP from Health and Social Work"),
    ("تجار", "GDP from Wholesale and Retail Trade"),
    ("إصلاح", "GDP from Wholesale and Retail Trade"),
    ("فنادق", "GDP from Hotels and Restaurants"),
    ("مطاعم", "GDP from Hotels and Restaurants"),
    ("إقامة", "GDP from Hotels and Restaurants"),
    ("طعام", "GDP from Hotels and Restaurants"),
    ("زراع", "GDP from Agriculture"),
    ("سمك", "GDP from Agriculture"),
    ("تعدين", "GDP from Mining and Quarrying"),
    ("نفط", "GDP from Mining and Quarrying"),
    ("استخراج", "GDP from Mining and Quarrying"),
    ("كهرباء", "GDP from Electricity and Water"),
    ("مياه", "GDP from Electricity and Water"),
    ("مياة", "GDP from Electricity and Water"),
    ("صرف صحي", "GDP from Electricity and Water"),
    ("عقار", "GDP from Real Estate"),
    ("حكوم", "GDP from Public Administration"),
    ("دفاع", "GDP from Public Administration"),
    ("خدمات منزل", "GDP from Domestic Services"),
]

# Arabic keyword → Bahrain Bourse sector
_BOURSE_KEYWORD_MAP = [
    ("مالي", "Financials"), ("بنك", "Financials"), ("تأمين", "Financials"), ("مصرف", "Financials"),
    ("صناع", "Industrials"), ("تحويل", "Industrials"),
    ("نقل", "Industrials"), ("تخزين", "Industrials"),
    ("فنادق", "Hotels & Tourism"), ("سياح", "Hotels & Tourism"), ("إقامة", "Hotels & Tourism"),
    ("عقار", "Real Estate"), ("تشييد", "Real Estate"),
    ("اتصالات", "Technology"), ("معلومات", "Technology"),
    ("تجار", "Consumer Non-Cyclicals"), ("غذ", "Consumer Non-Cyclicals"), ("طعام", "Consumer Non-Cyclicals"),
    ("مياه", None), ("مياة", None), ("صرف صحي", None),  # water/sanitation - no bourse match, before صح
    ("صح", "Healthcare"),
]

# Arabic keyword → Tamkeen programs
_TAMKEEN_KEYWORD_MAP = [
    ("صناع", ["enterprise_support", "export_support", "training"]),
    ("تحويل", ["enterprise_support", "export_support", "training"]),
    ("تقن", ["enterprise_support", "training", "digital_transformation"]),
    ("معلومات", ["enterprise_support", "training", "digital_transformation"]),
    ("اتصالات", ["enterprise_support", "training", "digital_transformation"]),
    ("رقم", ["enterprise_support", "digital_transformation"]),
    ("تصدير", ["enterprise_support", "export_support"]),
    ("تعليم", ["enterprise_support", "training", "national_employment"]),
    ("مالي", ["enterprise_support"]),
    ("نقل", ["enterprise_support", "export_support"]),
    ("مياه", ["enterprise_support", "training"]),
    ("مياة", ["enterprise_support", "training"]),
    ("صرف صحي", ["enterprise_support", "training"]),
    ("صح", ["enterprise_support", "training"]),
]

# Arabic keyword → EDB focus areas
_EDB_KEYWORD_MAP = [
    ("مالي", ["financial_services", "islamic_finance"]),
    ("مصرف", ["financial_services", "islamic_finance"]),
    ("تأمين", ["financial_services"]),
    ("تقن", ["ict", "fintech", "digital"]),
    ("معلومات", ["ict", "digital"]),
    ("اتصالات", ["ict"]),
    ("صناع", ["manufacturing", "logistics"]),
    ("تحويل", ["manufacturing"]),
    ("سياح", ["tourism"]),
    ("فنادق", ["tourism"]),
    ("إقامة", ["tourism"]),
    ("طعام", ["tourism", "food_processing"]),
    ("مياه", ["energy"]),
    ("مياة", ["energy"]),
    ("صرف صحي", ["energy"]),
    ("صح", ["healthcare"]),
    ("تعليم", ["education"]),
    ("نقل", ["logistics", "transport"]),
    ("تخزين", ["logistics"]),
    ("عقار", ["real_estate", "construction"]),
    ("تشييد", ["real_estate", "construction"]),
    ("نفط", ["energy"]),
    ("تعدين", ["energy"]),
    ("استخراج", ["energy"]),
    ("زراع", ["food_processing"]),
    ("كهرباء", ["energy"]),
    ("مياه", ["energy"]),
]

# Arabic keyword → extra WorldBank indicators (appended to defaults)
_WB_KEYWORD_MAP = [
    ("مياه", []), ("مياة", []), ("صرف صحي", []),  # water/sanitation before صح
    ("صح", ["SH.XPD.CHEX.GD.ZS", "SH.MED.PHYS.ZS"]),
    ("تعليم", ["SE.XPD.TOTL.GD.ZS"]),
    ("صناع", ["NV.IND.MANF.ZS", "NE.TRD.GNFS.ZS"]),
    ("تحويل", ["NV.IND.MANF.ZS"]),
    ("اتصالات", ["IT.NET.USER.ZS", "IT.CEL.SETS.P2"]),
    ("معلومات", ["IT.NET.USER.ZS", "IT.CEL.SETS.P2"]),
    ("تقن", ["IT.NET.USER.ZS", "GB.XPD.RSDV.GD.ZS"]),
    ("مالي", ["FM.LBL.BMNY.GD.ZS", "BX.KLT.DINV.CD.WD"]),
    ("تأمين", ["FM.LBL.BMNY.GD.ZS"]),
    ("نقل", ["IS.SHP.GOOD.TU", "NE.TRD.GNFS.ZS"]),
    ("تجار", ["NE.TRD.GNFS.ZS"]),
    ("عقار", ["BX.KLT.DINV.CD.WD"]),
    ("تشييد", ["BX.KLT.DINV.CD.WD"]),
    ("زراع", ["AG.LND.ARBL.ZS"]),
    ("سياح", ["ST.INT.ARVL"]),
    ("فنادق", ["ST.INT.ARVL"]),
]

# Arabic keyword → Sijilat activity terms (richer than just splitting the name)
_SIJILAT_KEYWORD_MAP = [
    ("تشييد", ["مقاولات", "بناء", "تشييد", "مواد بناء", "هندسة", "تصميم معماري"]),
    ("بناء", ["مقاولات", "بناء", "تشييد", "مواد بناء"]),
    ("مالي", ["بنك", "تأمين", "صرافة", "استثمار", "خدمات مالية", "وساطة"]),
    ("مصرف", ["بنك", "خدمات مالية", "صرافة"]),
    ("تأمين", ["تأمين", "وساطة تأمين", "إعادة تأمين"]),
    ("صناع", ["مصنع", "تصنيع", "إنتاج", "تعبئة", "تغليف", "صناعات"]),
    ("تحويل", ["مصنع", "تصنيع", "إنتاج"]),
    ("نقل", ["نقل", "شحن", "لوجستيات", "تخزين", "تخليص جمركي", "توصيل"]),
    ("تخزين", ["تخزين", "مستودعات", "لوجستيات"]),
    ("اتصالات", ["اتصالات", "شبكات", "إنترنت", "هاتف"]),
    ("معلومات", ["برمجيات", "تقنية معلومات", "حلول رقمية", "تطبيقات", "استشارات تقنية"]),
    ("تعليم", ["مدرسة", "معهد", "تدريب", "تعليم", "حضانة", "دورات", "جامعة"]),
    ("مياه", ["مياه", "تحلية", "صرف صحي", "معالجة مياه"]),
    ("مياة", ["مياه", "تحلية", "صرف صحي", "معالجة مياه"]),
    ("صرف صحي", ["صرف صحي", "معالجة مياه", "مجاري"]),
    ("صح", ["مستشفى", "عيادة", "صيدلية", "أجهزة طبية", "مستلزمات طبية", "رعاية صحية"]),
    ("تجار", ["تجارة تجزئة", "تجارة جملة", "سوبرماركت", "متجر", "توزيع", "استيراد"]),
    ("عقار", ["عقارات", "تطوير عقاري", "إدارة أملاك", "تثمين"]),
    ("فنادق", ["فندق", "منتجع", "شقق فندقية", "ضيافة"]),
    ("إقامة", ["فندق", "شقق فندقية", "سكن"]),
    ("طعام", ["مطعم", "مقهى", "كافيتيريا", "تموين", "مخبز"]),
    ("مطاعم", ["مطعم", "مقهى", "كافيتيريا", "تموين"]),
    ("زراع", ["مزرعة", "زراعة", "بيوت محمية", "أعلاف", "أسمدة"]),
    ("سمك", ["صيد", "أسماك", "استزراع سمكي"]),
    ("تعدين", ["تعدين", "محاجر", "استخراج"]),
    ("نفط", ["نفط", "غاز", "بتروكيماويات", "طاقة"]),
    ("كهرباء", ["كهرباء", "طاقة", "توليد", "توزيع كهرباء"]),
    ("مياه", ["مياه", "تحلية", "صرف صحي", "معالجة مياه"]),
    ("مياة", ["مياه", "تحلية", "صرف صحي", "معالجة مياه"]),
    ("حكوم", ["خدمات حكومية", "إدارة عامة"]),
    ("دفاع", ["أمن", "حراسة", "سلامة", "أنظمة أمنية"]),
]


def _match_keyword(sector_name_ar, keyword_map, default=None):
    """Find first matching keyword in sector_name_ar and return mapped value."""
    for keyword, value in keyword_map:
        if keyword in sector_name_ar:
            return value
    return default


def get_sector_mapping(sector_key):
    """Return sector mapping - static if available, or intelligently generated."""
    if sector_key in SECTOR_MAP:
        return SECTOR_MAP[sector_key]

    # Get Arabic sector name for keyword matching
    name_ar = ""
    try:
        from bahrain_data import get_sectors
        sectors = get_sectors()
        sector_info = sectors.get(sector_key, {})
        name_ar = sector_info.get("name_ar", "")
    except Exception:
        pass

    # Intelligent keyword-based mapping
    # WorldBank: defaults + sector-specific extras
    extra_wb = _match_keyword(name_ar, _WB_KEYWORD_MAP, [])
    wb_indicators = list(_DEFAULT_WB_INDICATORS)
    for ind in extra_wb:
        if ind not in wb_indicators:
            wb_indicators.append(ind)

    # Sijilat: rich activity terms from keyword map, fallback to name splitting
    sijilat = _match_keyword(name_ar, _SIJILAT_KEYWORD_MAP)
    if not sijilat:
        sijilat = [w for w in name_ar.split() if len(w) > 2][:5]

    return {
        "worldbank_indicators": wb_indicators,
        "cbb_relevant": True,  # interest rates & exchange are relevant for any feasibility study
        "sijilat_activities": sijilat,
        "trading_economics_sector": _match_keyword(name_ar, _TE_KEYWORD_MAP, "GDP from Services"),
        "bourse_sector": _match_keyword(name_ar, _BOURSE_KEYWORD_MAP),
        "tamkeen_programs": _match_keyword(name_ar, _TAMKEEN_KEYWORD_MAP, ["enterprise_support", "training"]),
        "edb_focus": _match_keyword(name_ar, _EDB_KEYWORD_MAP, []),
    }
