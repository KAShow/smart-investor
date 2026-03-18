"""
خدمة بيانات السوق البحريني - تخزين محلي + فلترة بالقطاع
https://www.data.gov.bh/api/explore/v2.1
"""

import json
import logging
import requests

from database import save_bahrain_data, get_bahrain_data, has_bahrain_data, get_bahrain_data_status

logger = logging.getLogger(__name__)

# ─── تعريف القطاعات الاستثمارية ───

SECTORS = {
    "food_hospitality": {
        "name_ar": "مطاعم وأغذية وضيافة",
        "icon": "🍽️",
        "gdp_keywords": ["إقامة", "طعام", "الغذائية"],
        "cpi_keywords": ["طعام", "مشروبات", "مطاعم", "فنادق"],
        "include_datasets": ["tourism", "tamkeen", "unemployment", "fdi", "labor"],
        "brokerage_context": "وساطة بين الموردين (مزارع، مصانع أغذية، مستوردي مواد غذائية) والمشترين (مطاعم، فنادق، كافيهات، شركات تموين). تشمل المعاملات: توريد مواد خام، معدات مطابخ، خدمات تموين."
    },
    "real_estate": {
        "name_ar": "عقارات وبناء وتشييد",
        "icon": "🏗️",
        "gdp_keywords": ["التشييد", "العقارية", "البناء"],
        "cpi_keywords": ["مسكن", "مياه", "كهرباء", "اثاث"],
        "include_datasets": ["fdi", "unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين مالكي العقارات/المطورين والمشترين/المستأجرين، وكذلك بين مقاولي البناء وأصحاب المشاريع. تشمل المعاملات: بيع وشراء عقارات، تأجير، مقاولات بناء، توريد مواد بناء."
    },
    "technology": {
        "name_ar": "تقنية معلومات واتصالات",
        "icon": "💻",
        "gdp_keywords": ["المعلومات", "الاتصالات"],
        "cpi_keywords": ["الاتصالات"],
        "include_datasets": ["fdi", "unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين مزودي الخدمات التقنية (شركات برمجة، مطورين مستقلين، شركات استضافة) والمشترين (شركات تحتاج حلول تقنية، حكومة، بنوك). تشمل المعاملات: تطوير برمجيات، استشارات تقنية، خدمات سحابية."
    },
    "finance": {
        "name_ar": "خدمات مالية وتأمين",
        "icon": "🏦",
        "gdp_keywords": ["المالية", "التأمين"],
        "cpi_keywords": [],
        "include_datasets": ["fdi", "stock_market", "unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين مقدمي الخدمات المالية (بنوك، شركات تأمين، صناديق استثمار) والعملاء (أفراد، شركات). تشمل المعاملات: وساطة تأمين، وساطة قروض، مقارنة منتجات مالية. ملاحظة: الوساطة المالية تخضع لرقابة مصرف البحرين المركزي."
    },
    "manufacturing": {
        "name_ar": "صناعة وتصنيع",
        "icon": "🏭",
        "gdp_keywords": ["الصناعة التحويلية", "التعدين"],
        "cpi_keywords": [],
        "include_datasets": ["fdi", "imports", "unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين المصانع/المصنعين (محلياً وخليجياً) والمشترين (تجار جملة، موزعين، شركات). تشمل المعاملات: توريد مواد خام، بيع منتجات مصنعة، عقود تصنيع حسب الطلب (OEM)."
    },
    "health": {
        "name_ar": "صحة ورعاية طبية",
        "icon": "🏥",
        "gdp_keywords": ["الصحة", "الاجتماعي"],
        "cpi_keywords": ["الصحة"],
        "include_datasets": ["unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين مزودي الخدمات الصحية (مستشفيات، عيادات، صيدليات، موردي أجهزة طبية) والمشترين (مرضى، شركات تأمين صحي، مؤسسات حكومية). تشمل المعاملات: توريد أجهزة ومستلزمات طبية، حجز مواعيد، خدمات رعاية منزلية."
    },
    "education": {
        "name_ar": "تعليم وتدريب",
        "icon": "🎓",
        "gdp_keywords": ["التعليم"],
        "cpi_keywords": ["التعليم"],
        "include_datasets": ["unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين مقدمي خدمات التعليم والتدريب (مدارس خاصة، معاهد تدريب، مدربين مستقلين) والمشترين (طلاب، أولياء أمور، شركات تبحث عن تدريب موظفيها). تشمل المعاملات: حجز دورات، توظيف مدربين، بيع مناهج تعليمية."
    },
    "transport": {
        "name_ar": "نقل ولوجستيات",
        "icon": "🚚",
        "gdp_keywords": ["النقل", "التخزين"],
        "cpi_keywords": ["النقل"],
        "include_datasets": ["fdi", "imports", "unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين شركات النقل والشحن (محلياً ودولياً) والمشترين (تجار، مصانع، شركات تحتاج خدمات لوجستية). تشمل المعاملات: شحن بضائع، تخزين، تخليص جمركي، نقل بري/بحري/جوي."
    },
    "retail": {
        "name_ar": "تجارة وتجزئة",
        "icon": "🛍️",
        "gdp_keywords": ["التجارة", "تجارة الجملة"],
        "cpi_keywords": ["ملابس", "سلع"],
        "include_datasets": ["imports", "tourism", "unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين تجار الجملة/المستوردين والمشترين (محلات تجزئة، متاجر إلكترونية، موزعين). تشمل المعاملات: توريد بضائع بالجملة، توزيع منتجات، عقود توريد مستمرة."
    },
    "ai_applications": {
        "name_ar": "تطبيقات الذكاء الاصطناعي",
        "icon": "🤖",
        "gdp_keywords": ["المعلومات", "الاتصالات"],
        "cpi_keywords": ["الاتصالات"],
        "include_datasets": ["fdi", "unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين مطوري حلول الذكاء الاصطناعي (شركات AI، مطورين مستقلين، مزودي نماذج تعلم آلي) والمشترين (شركات تحتاج حلول AI، بنوك، حكومة، قطاع صحي). تشمل المعاملات: تطوير وتخصيص نماذج AI، أتمتة عمليات، تحليل بيانات متقدم، حلول معالجة اللغة الطبيعية، رؤية حاسوبية. ملاحظة: البحرين لديها استراتيجية وطنية للذكاء الاصطناعي و Regulatory Sandbox من مصرف البحرين المركزي."
    },
    "security_safety": {
        "name_ar": "أمن وسلامة",
        "icon": "🛡️",
        "gdp_keywords": ["الخدمات", "الإدارية"],
        "cpi_keywords": [],
        "include_datasets": ["fdi", "unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين مزودي خدمات الأمن والسلامة (شركات حراسة، أنظمة مراقبة، أنظمة إنذار، معدات سلامة، استشارات أمنية) والمشترين (شركات، مصانع، مجمعات تجارية، مؤسسات حكومية، منشآت نفطية). تشمل المعاملات: توريد كاميرات مراقبة، أنظمة تحكم بالدخول، خدمات حراسة أمنية، أنظمة إطفاء حريق، استشارات السلامة المهنية، تراخيص أمنية من وزارة الداخلية."
    },
    "tourism_entertainment": {
        "name_ar": "سياحة وترفيه",
        "icon": "🏖️",
        "gdp_keywords": ["إقامة", "الفنادق", "السياحة"],
        "cpi_keywords": ["مطاعم", "فنادق", "ترفيه"],
        "include_datasets": ["tourism", "fdi", "unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين مزودي الخدمات السياحية والترفيهية (فنادق، منتجعات، شركات سياحة، منظمي فعاليات) والمشترين (سياح، شركات تبحث عن تنظيم فعاليات، وكالات سفر). تشمل المعاملات: حجز فنادق، تنظيم رحلات، تنظيم مؤتمرات ومعارض، خدمات ترفيه."
    },
    "energy_environment": {
        "name_ar": "طاقة وبيئة",
        "icon": "⚡",
        "gdp_keywords": ["التعدين", "النفط", "الكهرباء"],
        "cpi_keywords": ["كهرباء", "وقود"],
        "include_datasets": ["fdi", "imports", "unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين مزودي خدمات الطاقة والبيئة (شركات طاقة شمسية، مقاولي كهرباء، شركات إدارة نفايات، استشارات بيئية) والمشترين (مصانع، شركات، مباني تجارية، جهات حكومية). تشمل المعاملات: توريد ألواح شمسية، أنظمة توفير طاقة، خدمات إعادة تدوير، استشارات بيئية، تراخيص بيئية."
    },
    "media_marketing": {
        "name_ar": "إعلام وتسويق",
        "icon": "📢",
        "gdp_keywords": ["المعلومات", "الاتصالات"],
        "cpi_keywords": ["الاتصالات"],
        "include_datasets": ["unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين مزودي خدمات الإعلام والتسويق (وكالات إعلان، مصممين، مصورين، شركات إنتاج محتوى، مؤثرين) والمشترين (شركات تبحث عن تسويق، علامات تجارية، منظمي فعاليات). تشمل المعاملات: حملات إعلانية، تصميم هوية بصرية، إنتاج فيديو، تسويق رقمي، إدارة وسائل التواصل."
    },
    "beauty_wellness": {
        "name_ar": "تجميل وعناية شخصية",
        "icon": "💄",
        "gdp_keywords": ["الخدمات"],
        "cpi_keywords": [],
        "include_datasets": ["unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين مزودي منتجات وخدمات التجميل (موردي مستحضرات تجميل، أجهزة تجميل، مدربي تجميل) والمشترين (صالونات، عيادات تجميل، سبا، متاجر مستحضرات). تشمل المعاملات: توريد مستحضرات تجميل بالجملة، أجهزة ليزر وتجميل، دورات تدريب تجميل."
    },
    "legal_consulting": {
        "name_ar": "خدمات قانونية واستشارية",
        "icon": "⚖️",
        "gdp_keywords": ["الخدمات", "المهنية"],
        "cpi_keywords": [],
        "include_datasets": ["unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين مزودي الخدمات القانونية والاستشارية (مكاتب محاماة، مستشارين ماليين، مدققي حسابات، مستشاري أعمال) والمشترين (شركات، رواد أعمال، مستثمرين أجانب). تشمل المعاملات: استشارات قانونية، تأسيس شركات، تدقيق حسابات، استشارات ضريبية، تراخيص تجارية."
    },
    "agriculture_fishing": {
        "name_ar": "زراعة وصيد",
        "icon": "🌾",
        "gdp_keywords": ["الزراعة", "صيد"],
        "cpi_keywords": ["طعام"],
        "include_datasets": ["imports", "unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين المنتجين الزراعيين والصيادين (مزارع، شركات استزراع سمكي، مزارع دواجن) والمشترين (أسواق مركزية، مطاعم، تجار جملة، مصانع أغذية). تشمل المعاملات: بيع محاصيل بالجملة، توريد أسماك طازجة، بيع منتجات حيوانية، توريد أعلاف ومعدات زراعية."
    },
    "automotive": {
        "name_ar": "سيارات وقطع غيار",
        "icon": "🚗",
        "gdp_keywords": ["التجارة", "النقل"],
        "cpi_keywords": ["النقل"],
        "include_datasets": ["imports", "unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين موردي السيارات وقطع الغيار (وكالات سيارات، مستوردي قطع غيار، ورش صيانة متخصصة) والمشترين (أفراد، شركات تأجير، شركات نقل، ورش صيانة). تشمل المعاملات: بيع سيارات جديدة ومستعملة، توريد قطع غيار بالجملة، خدمات صيانة وإصلاح."
    },
    "construction_materials": {
        "name_ar": "مواد بناء ومقاولات",
        "icon": "🧱",
        "gdp_keywords": ["التشييد", "البناء"],
        "cpi_keywords": ["مسكن"],
        "include_datasets": ["fdi", "imports", "unemployment", "labor", "tamkeen"],
        "brokerage_context": "وساطة بين موردي مواد البناء (مصانع إسمنت، حديد، رخام، مستوردي مواد بناء) والمشترين (مقاولين، شركات تطوير عقاري، أفراد يبنون منازل). تشمل المعاملات: توريد مواد بناء بالجملة، عقود توريد طويلة الأمد، خدمات مقاولات باطن."
    },
}

# ─── ربط أسماء الداتاسيتات بمعرّفات API ───

DATASET_CONFIG = {
    "gdp_growth": {
        "api_id": "2-quarterly-growth-cp-change",
        "params": {"order_by": "year desc, quarter desc", "limit": 50},
        "name": "نمو GDP الفصلي"
    },
    "gdp_annual": {
        "api_id": "04-annually-gva-kp-value",
        "params": {"order_by": "year desc", "limit": 50},
        "name": "GDP السنوي"
    },
    "fdi": {
        "api_id": "03-quarterly-foreign-direct-investments-stocks-in-bhd-millions-",
        "params": {"order_by": "year desc, quarter desc", "limit": 10},
        "name": "الاستثمار الأجنبي المباشر"
    },
    "cpi": {
        "api_id": "06-percentage-change-from-previous-year",
        "params": {"order_by": "year desc, month desc", "limit": 100},
        "name": "مؤشر أسعار المستهلك"
    },
    "unemployment": {
        "api_id": "03-unemployment-yearly",
        "params": {"order_by": "year desc", "limit": 20},
        "name": "البطالة"
    },
    "stock_market": {
        "api_id": "shareholding-companies-in-the-stock-market",
        "params": {"order_by": "year desc", "limit": 5},
        "name": "بورصة البحرين"
    },
    "imports": {
        "api_id": "import-1-2025",
        "params": {"order_by": "import_value_bd desc", "limit": 20},
        "name": "الواردات"
    },
    "tourism": {
        "api_id": "05-inbound-visitors-by-countryregion-of-residence",
        "params": {"order_by": "year desc", "limit": 50},
        "name": "السياحة الوافدة"
    },
    "labor": {
        "api_id": "workers-covered-by-social-insurance-system-private-sector-by-monthly-wage-groups",
        "params": {"order_by": "year desc", "limit": 50},
        "name": "العمالة والأجور"
    },
    "tamkeen": {
        "api_id": "es_table_tamkeen-datasets",
        "params": {"limit": 50},
        "name": "دعم تمكين"
    },
}


# ─── أيقونات القطاعات بالكلمات المفتاحية ───
_ICON_MAP = [
    ("صناع", "🏭"), ("تحويل", "🏭"), ("تشييد", "🏗️"), ("بناء", "🏗️"),
    ("مالي", "🏦"), ("تأمين", "🏦"), ("تعليم", "🎓"),
    ("مياه", "💧"), ("صرف صحي", "💧"), ("نفايات", "💧"),
    ("صحة الإنسان", "🏥"), ("عمل الاجتماعي", "🏥"),
    ("نقل", "🚚"), ("تخزين", "🚚"), ("معلومات", "💻"), ("اتصالات", "💻"),
    ("عقار", "🏠"), ("زراع", "🌾"), ("صيد", "🌾"), ("تعدين", "⛏️"),
    ("نفط", "🛢️"), ("كهرباء", "⚡"), ("غاز", "⚡"), ("تجار", "🛍️"),
    ("إقامة", "🏨"), ("طعام", "🏨"), ("إدار", "🏛️"), ("عام", "🏛️"), ("دفاع", "🏛️"),
    ("ترفي", "🎭"), ("فنون", "🎭"), ("أسر", "🏠"), ("ضرائب", "💰"),
    ("مهني", "💼"), ("علمي", "💼"), ("منظمات", "🌐"), ("هيئات", "🌐"),
]

# صفوف تجميعية يجب استبعادها
_AGGREGATE_KEYWORDS = ["الناتج المحلي", "اجمالي القيمة", "إجمالي الناتج", "Total", "صافي الضرائب"]

# كاش القطاعات المجلوبة من API
_dynamic_sectors_cache = None


# ربط أسماء القطاعات العربية من API بـ slugs إنجليزية واضحة
_SECTOR_SLUG_MAP = {
    "الصناعة التحويلية": "manufacturing",
    "التشييد": "construction",
    "الأنشطة المالية وأنشطة التأمين": "finance_insurance",
    "الأنشطة العقارية": "real_estate",
    "المعلومات والاتصالات": "ict",
    "النقل والتخزين": "transport_storage",
    "التعليم": "education",
    "التعدين واستغلال المحاجر": "mining",
    "تجارة الجملة والتجزئة": "wholesale_retail",
    "الإدارة العامة والدفاع": "public_admin",
    "أنشطة خدمات الإقامة والطعام": "hospitality",
    "الزراعة والحراجة وصيد الأسماك": "agriculture_fishing",
    "إمدادات الكهرباء والغاز": "electricity_gas",
    "الأنشطة المهنية والعلمية والتقنية": "professional_services",
    "الفنون والترفية والتسلية": "arts_entertainment",
    "أنشطة الخدمات الإدارية وخدمات الدعم": "admin_services",
    "أنشطة الخدمات الأخرى": "other_services",
    "أنشطة الأسر باعتبارها جهة مشغله": "household_activities",
    "أنشطة المنظمات والهيئات": "international_orgs",
    "إمدادات المياة": "water_sanitation",
    "إمدادات المياه": "water_sanitation",
    "الأنشطة في مجال صحة": "healthcare",
    "االأنشطة في مجال صحة": "healthcare",
}


def _name_to_slug(name_ar):
    """تحويل اسم القطاع العربي إلى slug إنجليزي."""
    # بحث في الخريطة المعروفة أولاً
    for ar_key, slug in _SECTOR_SLUG_MAP.items():
        if ar_key in name_ar:
            return slug
    # fallback: توليد من الاسم العربي
    import re
    clean = re.sub(r'[\u0610-\u061A\u064B-\u065F]', '', name_ar)
    clean = re.sub(r'[,،\(].*', '', clean).strip()
    words = clean.split()[:3]
    slug = "_".join(words)
    slug = re.sub(r'[^\w]', '_', slug)
    slug = re.sub(r'_+', '_', slug).strip('_')
    return slug or "other"


def _icon_for_sector(name_ar):
    """اختيار أيقونة مناسبة بناءً على اسم القطاع."""
    for keyword, icon in _ICON_MAP:
        if keyword in name_ar:
            return icon
    return "📊"


def _generate_brokerage_context(name_ar):
    """توليد سياق وساطة تلقائي من اسم القطاع."""
    return f"وساطة تجارية في قطاع {name_ar} في مملكة البحرين. يشمل ربط مزودي الخدمات والمنتجات بالمشترين والعملاء في هذا القطاع."


def _generate_sijilat_terms(name_ar):
    """توليد مصطلحات بحث Sijilat من اسم القطاع."""
    import re
    # كلمات توقف عربية بسيطة
    stop = {"و", "في", "من", "إلى", "على", "أو", "ال", "أنشطة", "خدمات", "وأنشطة"}
    clean = re.sub(r'[\u0610-\u061A\u064B-\u065F]', '', name_ar)
    clean = re.sub(r'\(.*?\)', '', clean).strip()
    words = [w for w in clean.split() if w not in stop and len(w) > 2]
    return words[:5]


def fetch_sectors_from_api():
    """جلب قائمة القطاعات الحقيقية من data.gov.bh (بيانات GDP السنوي)."""
    global _dynamic_sectors_cache
    if _dynamic_sectors_cache is not None:
        return _dynamic_sectors_cache

    try:
        url = "https://www.data.gov.bh/api/explore/v2.1/catalog/datasets/04-annually-gva-kp-value/records"
        resp = requests.get(url, params={"limit": 100, "lang": "ar", "order_by": "year desc"}, timeout=15)
        resp.raise_for_status()
        results = resp.json().get("results", [])

        # استخراج أسماء القطاعات الفريدة
        sector_names = set()
        for r in results:
            fields = r.get("record", {}).get("fields", {}) if "record" in r else r
            name = (fields.get("lnsht_lqtsdy_bl_s_r_lthbt")
                    or fields.get("lqt_l_s_r_ljry")
                    or fields.get("sector", ""))
            if name and not any(agg in name for agg in _AGGREGATE_KEYWORDS):
                sector_names.add(name.strip())

        if not sector_names:
            logger.warning("⚠️ لم يتم العثور على قطاعات من API")
            return None

        # بناء dict القطاعات
        sectors = {}
        for name_ar in sorted(sector_names):
            slug = _name_to_slug(name_ar)
            sectors[slug] = {
                "name_ar": name_ar,
                "icon": _icon_for_sector(name_ar),
                "gdp_keywords": [name_ar],
                "cpi_keywords": [],
                "include_datasets": ["fdi", "unemployment", "labor", "tamkeen"],
                "brokerage_context": _generate_brokerage_context(name_ar),
                "sijilat_terms": _generate_sijilat_terms(name_ar),
                "source": "data.gov.bh",
            }

        logger.info(f"✅ تم جلب {len(sectors)} قطاع من data.gov.bh")
        _dynamic_sectors_cache = sectors
        return sectors

    except Exception as e:
        logger.warning(f"⚠️ فشل جلب القطاعات من API: {e}")
        return None


def get_sectors():
    """إرجاع القطاعات - من API أولاً، ثم SECTORS كـ fallback."""
    dynamic = fetch_sectors_from_api()
    if dynamic:
        # دمج: القطاعات الديناميكية + القطاعات اليدوية التي لها تفاصيل إضافية
        merged = dict(dynamic)
        for key, val in SECTORS.items():
            if key not in merged:
                merged[key] = val
            else:
                # إذا القطاع موجود في كلا المصدرين، نُثري الديناميكي بالبيانات اليدوية
                if val.get("cpi_keywords"):
                    merged[key]["cpi_keywords"] = val["cpi_keywords"]
                if val.get("brokerage_context") and "source" not in val:
                    merged[key]["brokerage_context"] = val["brokerage_context"]
        return merged
    return SECTORS


def refresh_sectors_cache():
    """إعادة جلب القطاعات من API (مسح الكاش)."""
    global _dynamic_sectors_cache
    _dynamic_sectors_cache = None
    return get_sectors()


class BahrainDataService:
    BASE_URL = "https://www.data.gov.bh/api/explore/v2.1"

    def __init__(self):
        # مزامنة أولية تلقائية إذا لا توجد بيانات
        if not has_bahrain_data():
            logger.info("🇧🇭 أول تشغيل - جلب بيانات البحرين وتخزينها محلياً...")
            self.sync_all_data()

    # ═══════════════════════════════════════════
    # مزامنة البيانات من API إلى قاعدة البيانات
    # ═══════════════════════════════════════════

    def _fetch_from_api(self, dataset_id, params=None):
        """جلب بيانات مباشرة من data.gov.bh API."""
        try:
            url = f"{self.BASE_URL}/catalog/datasets/{dataset_id}/records"
            default_params = {"limit": 100, "lang": "ar"}
            if params:
                default_params.update(params)
            resp = requests.get(url, params=default_params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            logger.info(f"✅ API: جلب {len(results)} سجل من {dataset_id}")
            return results
        except Exception as e:
            logger.warning(f"⚠️ API: فشل جلب {dataset_id}: {e}")
            return []

    def sync_all_data(self):
        """جلب كل البيانات من data.gov.bh وحفظها في قاعدة البيانات المحلية."""
        logger.info("🔄 بدء مزامنة بيانات البحرين...")
        success_count = 0
        for name, config in DATASET_CONFIG.items():
            try:
                records = self._fetch_from_api(config["api_id"], config["params"])
                if records:
                    save_bahrain_data(name, config["api_id"],
                                     json.dumps(records, ensure_ascii=False), len(records))
                    success_count += 1
                    logger.info(f"  ✅ {config['name']}: {len(records)} سجل")
                else:
                    logger.warning(f"  ⚠️ {config['name']}: لا توجد بيانات")
            except Exception as e:
                logger.warning(f"  ❌ {config['name']}: {e}")
        logger.info(f"🏁 انتهت المزامنة: {success_count}/{len(DATASET_CONFIG)} datasets")
        return success_count

    # ═══════════════════════════════════════════
    # تنسيق البيانات - دوال التحويل لنص مقروء
    # ═══════════════════════════════════════════

    @staticmethod
    def _get_fields(record):
        """استخراج الحقول من سجل API."""
        return record.get("record", {}).get("fields", {}) if "record" in record else record

    def _format_gdp_growth(self, records, keywords=None):
        """تنسيق بيانات نمو GDP - مع فلترة اختيارية بالكلمات المفتاحية."""
        if not records:
            return ""
        latest = {}
        target_year = None
        target_quarter = None
        for r in records:
            fields = self._get_fields(r)
            year = fields.get("year", "")
            quarter = fields.get("quarter", "")
            if target_year is None:
                target_year = year
                target_quarter = quarter
            if year == target_year and quarter == target_quarter:
                sector = fields.get("lqt_l_s_r_ljry") or fields.get("sector_current_prices", "")
                rate = fields.get("growth_rate")
                if sector and rate is not None:
                    if keywords:
                        if any(kw in sector for kw in keywords):
                            latest[sector] = rate
                    else:
                        latest[sector] = rate
        if not latest:
            return ""
        lines = [f"📊 نمو الناتج المحلي الإجمالي - {target_year} الربع {target_quarter}:"]
        for sector, rate in sorted(latest.items(), key=lambda x: abs(x[1]), reverse=True)[:12]:
            sign = "+" if rate > 0 else ""
            lines.append(f"  - {sector}: {sign}{rate:.1f}%")
        return "\n".join(lines)

    def _format_gdp_annual(self, records, keywords=None):
        """تنسيق GDP السنوي."""
        if not records:
            return ""
        latest = {}
        target_year = None
        for r in records:
            fields = self._get_fields(r)
            year = fields.get("year", "")
            if target_year is None and year:
                target_year = year
            if year == target_year:
                sector = (fields.get("lnsht_lqtsdy_bl_s_r_lthbt")
                          or fields.get("lqt_l_s_r_ljry")
                          or fields.get("sector", ""))
                value = (fields.get("value_bd_million")
                         or fields.get("value")
                         or fields.get("kp_value"))
                if sector and value is not None:
                    if keywords:
                        if any(kw in sector for kw in keywords):
                            latest[sector] = value
                    else:
                        latest[sector] = value
        if not latest:
            return ""
        lines = [f"📊 الناتج المحلي بالأسعار الثابتة ({target_year}) بملايين د.ب:"]
        for sector, val in sorted(latest.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, reverse=True)[:10]:
            if isinstance(val, (int, float)):
                lines.append(f"  - {sector}: {val:,.1f}")
            else:
                lines.append(f"  - {sector}: {val}")
        return "\n".join(lines)

    def _format_fdi(self, records):
        """تنسيق FDI."""
        if not records:
            return ""
        lines = ["💰 الاستثمار الأجنبي المباشر (مليون د.ب):"]
        for r in records[:6]:
            fields = self._get_fields(r)
            year = fields.get("year", "")
            quarter = fields.get("quarter", "")
            value = fields.get("values")
            if year and value is not None:
                lines.append(f"  - {year} Q{quarter}: {value:,.1f}")
        return "\n".join(lines) if len(lines) > 1 else ""

    def _format_cpi(self, records, keywords=None):
        """تنسيق CPI/التضخم - مع فلترة اختيارية."""
        if not records:
            return ""
        latest = {}
        target_year = None
        target_month = None
        for r in records:
            fields = self._get_fields(r)
            year = fields.get("year")
            month = fields.get("lshhr") or fields.get("month", "")
            level = fields.get("level")
            if target_year is None and year:
                target_year = year
                target_month = month
            if year == target_year and month == target_month:
                if level in (2, 2.0):
                    category = fields.get("id") or fields.get("coicop_division_group", "")
                    change = fields.get("percentage_change")
                    if category and change is not None:
                        if keywords:
                            if any(kw in category for kw in keywords):
                                latest[category] = change
                        else:
                            latest[category] = change
        if not latest:
            return ""
        lines = [f"📈 مؤشر أسعار المستهلك (التضخم) - {target_year}/{target_month}:"]
        for cat, change in latest.items():
            sign = "+" if isinstance(change, (int, float)) and change > 0 else ""
            if isinstance(change, (int, float)):
                lines.append(f"  - {cat}: {sign}{change:.1f}%")
            else:
                lines.append(f"  - {cat}: {change}")
        return "\n".join(lines)

    def _format_unemployment(self, records):
        """تنسيق البطالة."""
        if not records:
            return ""
        by_year = {}
        for r in records:
            fields = self._get_fields(r)
            year = fields.get("year", "")
            sex = fields.get("ljns") or fields.get("sex", "")
            value = fields.get("value")
            if year and value is not None:
                if year not in by_year:
                    by_year[year] = {}
                by_year[year][sex] = value
        if not by_year:
            return ""
        lines = ["👥 البطالة (العاطلون البحرينيون 15 سنة فأكثر):"]
        for year in sorted(by_year.keys(), reverse=True)[:3]:
            data = by_year[year]
            total = sum(v for v in data.values() if isinstance(v, (int, float)))
            parts = [f"  - {year}: إجمالي {total:,.0f} عاطل"]
            for sex, val in data.items():
                if isinstance(val, (int, float)):
                    parts.append(f"({sex}: {val:,.0f})")
            lines.append(" ".join(parts))
        return "\n".join(lines)

    def _format_stock_market(self, records):
        """تنسيق بورصة البحرين."""
        if not records:
            return ""
        lines = ["🏢 بورصة البحرين:"]
        for r in records[:3]:
            fields = self._get_fields(r)
            year = fields.get("year", "")
            companies = fields.get("no_listed_shareholding_companies_in_bahrain")
            capital = fields.get("paid_up_capital_for_shareholding_companies_in_bahrain_bhd")
            parts = [f"  - {year}:"]
            if companies is not None:
                parts.append(f"{int(companies)} شركة مدرجة")
            if capital is not None:
                parts.append(f"| رأس مال {capital/1e9:,.2f} مليار د.ب")
            lines.append(" ".join(parts))
        return "\n".join(lines) if len(lines) > 1 else ""

    def _format_imports(self, records):
        """تنسيق الواردات."""
        if not records:
            return ""
        lines = ["🏭 أكبر الواردات (بالقيمة - د.ب):"]
        seen = set()
        count = 0
        for r in records:
            fields = self._get_fields(r)
            commodity = fields.get("lsl") or fields.get("commodity", "")
            value = fields.get("import_value_bd")
            country = fields.get("ldwl") or fields.get("country_name", "")
            if commodity and commodity not in seen and value:
                seen.add(commodity)
                lines.append(f"  - {commodity[:50]}: {value:,.0f} د.ب (من {country})")
                count += 1
                if count >= 8:
                    break
        return "\n".join(lines) if count > 0 else ""

    def _format_tourism(self, records):
        """تنسيق السياحة."""
        if not records:
            return ""
        # البيانات: كل سجل = شهر، والأعمدة = مناطق (ksa, europe, asia, etc.)
        skip_keys = {"n", "year", "month", "lshhr"}
        region_names = {
            "ksa": "السعودية", "other_gcc": "دول خليجية أخرى",
            "europe": "أوروبا", "asia": "آسيا",
            "america": "أمريكا", "middle_east": "الشرق الأوسط",
            "other_countries": "دول أخرى"
        }
        # تجميع حسب السنة
        by_year = {}
        for r in records:
            fields = self._get_fields(r)
            year = fields.get("year", "")
            if not year:
                continue
            if year not in by_year:
                by_year[year] = {}
            for key, val in fields.items():
                if key not in skip_keys and isinstance(val, (int, float)):
                    by_year[year][key] = by_year[year].get(key, 0) + val
        if not by_year:
            return ""
        latest_year = sorted(by_year.keys(), reverse=True)[0]
        regions = by_year[latest_year]
        total = sum(regions.values())
        lines = [f"🛫 السياحة الوافدة ({latest_year}):"]
        lines.append(f"  - الإجمالي: {total:,.0f} زائر")
        for key, cnt in sorted(regions.items(), key=lambda x: x[1], reverse=True)[:5]:
            name = region_names.get(key, key)
            lines.append(f"  - {name}: {cnt:,.0f}")
        return "\n".join(lines)

    def _format_labor(self, records):
        """تنسيق العمالة والأجور."""
        if not records:
            return ""
        # البيانات: كل سجل = فئة أجر + جنسية + جنس + عدد (value)
        target_year = None
        wages = {}
        for r in records:
            fields = self._get_fields(r)
            year = fields.get("year", "")
            if target_year is None and year:
                target_year = year
            if year == target_year:
                group = (fields.get("fy_t_l_jr_lshhry_bldynr_lbhryny")
                         or fields.get("monthly_wage_groups_bahraini_dinar", ""))
                value = fields.get("value")
                if group and isinstance(value, (int, float)):
                    wages[group] = wages.get(group, 0) + value
        if not wages:
            return ""
        lines = [f"💼 توزيع العمالة بفئات الأجور الشهرية ({target_year}):"]
        for group, count in wages.items():
            lines.append(f"  - {group} د.ب: {count:,.0f} عامل")
        return "\n".join(lines)

    def _format_tamkeen(self, records):
        """تنسيق تمكين."""
        if not records:
            return ""
        lines = ["🤝 برامج دعم تمكين للمؤسسات:"]
        count = 0
        for r in records[:10]:
            fields = self._get_fields(r)
            parts = []
            for key, val in fields.items():
                if val and key != "n" and not key.startswith("_"):
                    parts.append(f"{val}")
            if parts:
                lines.append(f"  - {' | '.join(parts[:4])}")
                count += 1
                if count >= 8:
                    break
        return "\n".join(lines) if count > 0 else ""

    # ─── ربط اسم الداتاسيت بدالة التنسيق ───

    def _format_dataset(self, dataset_name, records):
        """تنسيق dataset حسب اسمه."""
        formatters = {
            "gdp_growth": lambda r: self._format_gdp_growth(r),
            "gdp_annual": lambda r: self._format_gdp_annual(r),
            "fdi": self._format_fdi,
            "cpi": lambda r: self._format_cpi(r),
            "unemployment": self._format_unemployment,
            "stock_market": self._format_stock_market,
            "imports": self._format_imports,
            "tourism": self._format_tourism,
            "labor": self._format_labor,
            "tamkeen": self._format_tamkeen,
        }
        formatter = formatters.get(dataset_name)
        if formatter:
            return formatter(records)
        return ""

    # ═══════════════════════════════════════════
    # بناء سياق السوق - الدالة الرئيسية
    # ═══════════════════════════════════════════

    def build_market_context(self, sector='food_hospitality'):
        """بناء سياق السوق البحريني حسب القطاع المحدد - من قاعدة البيانات المحلية."""
        sector_config = SECTORS.get(sector)
        if not sector_config:
            sector_config = list(SECTORS.values())[0]
        is_general = sector_config.get('datasets') == 'all'

        logger.info(f"🇧🇭 بناء سياق السوق | القطاع: {sector_config['name_ar']}")

        sections = []

        if is_general:
            # عام: كل البيانات بدون فلترة
            for ds_name in DATASET_CONFIG:
                try:
                    records = get_bahrain_data(ds_name)
                    if records:
                        text = self._format_dataset(ds_name, records)
                        if text:
                            sections.append(text)
                except Exception as e:
                    logger.warning(f"⚠️ فشل تنسيق {ds_name}: {e}")
        else:
            # قطاع محدد: فلترة GDP و CPI بالكلمات المفتاحية
            gdp_keywords = sector_config.get('gdp_keywords', [])
            cpi_keywords = sector_config.get('cpi_keywords', [])

            # GDP مفلتر
            if gdp_keywords:
                gdp_records = get_bahrain_data("gdp_growth")
                if gdp_records:
                    text = self._format_gdp_growth(gdp_records, keywords=gdp_keywords)
                    if text:
                        sections.append(text)

                gdp_annual = get_bahrain_data("gdp_annual")
                if gdp_annual:
                    text = self._format_gdp_annual(gdp_annual, keywords=gdp_keywords)
                    if text:
                        sections.append(text)

            # CPI مفلتر
            if cpi_keywords:
                cpi_records = get_bahrain_data("cpi")
                if cpi_records:
                    text = self._format_cpi(cpi_records, keywords=cpi_keywords)
                    if text:
                        sections.append(text)

            # الداتاسيتات المرتبطة (بدون فلترة)
            for ds_name in sector_config.get('include_datasets', []):
                try:
                    records = get_bahrain_data(ds_name)
                    if records:
                        text = self._format_dataset(ds_name, records)
                        if text:
                            sections.append(text)
                except Exception as e:
                    logger.warning(f"⚠️ فشل تنسيق {ds_name}: {e}")

        if not sections:
            logger.warning("⚠️ لا توجد بيانات بحرينية مخزنة - جرب تحديث البيانات من لوحة التحكم")
            return ""

        sector_label = sector_config['name_ar']
        header = f"═══ بيانات السوق البحريني - {sector_label} (من بوابة البيانات المفتوحة data.gov.bh) ═══"
        footer = "═══ ملاحظة: استخدم هذه البيانات الحقيقية في تحليلك. حلل الفكرة حصرياً في سياق السوق البحريني. عند الاستشهاد بأي رقم أو إحصائية من هذه البيانات، يجب أن تذكر صراحةً أن المصدر هو: بوابة البيانات المفتوحة البحرينية (data.gov.bh). مثال: 'وفقاً لبيانات بوابة البيانات المفتوحة البحرينية (data.gov.bh)، بلغ نمو الناتج المحلي...' ═══"

        context = f"\n\n{header}\n\n" + "\n\n".join(sections) + f"\n\n{footer}"

        # إضافة سياق الوساطة التجارية للقطاع
        brokerage_note = sector_config.get('brokerage_context', '')
        if brokerage_note:
            context += f"\n\n═══ سياق الوساطة التجارية ═══\n{brokerage_note}\n"

        logger.info(f"✅ سياق السوق ({sector_label}): {len(context)} حرف، {len(sections)} أقسام")
        return context

    # ═══════════════════════════════════════════
    # بيانات مهيكلة للعرض المرئي (صفحة احتياج السوق)
    # ═══════════════════════════════════════════

    def get_sector_data(self, sector='food_hospitality'):
        """إرجاع بيانات القطاع بصيغة JSON مهيكلة للعرض في صفحة فرص الوساطة."""
        sector_config = SECTORS.get(sector)
        if not sector_config:
            sector_config = list(SECTORS.values())[0]
        is_general = sector_config.get('datasets') == 'all'

        result = {
            "sector": sector,
            "sector_name": sector_config['name_ar'],
            "icon": sector_config.get('icon', ''),
            "gdp_growth": [],
            "gdp_annual": [],
            "cpi": [],
            "unemployment": [],
            "fdi": [],
            "stock_market": [],
            "imports": [],
            "tourism": [],
            "labor": [],
            "tamkeen": [],
            "last_updated": "",
        }

        # آخر تحديث
        status = get_bahrain_data_status()
        if status:
            dates = [s.get('fetched_at', '') for s in status if s.get('fetched_at')]
            result['last_updated'] = max(dates) if dates else ''

        gdp_keywords = sector_config.get('gdp_keywords', []) if not is_general else []
        cpi_keywords = sector_config.get('cpi_keywords', []) if not is_general else []
        include_datasets = list(DATASET_CONFIG.keys()) if is_general else sector_config.get('include_datasets', [])

        # ─── GDP Growth ───
        records = get_bahrain_data("gdp_growth")
        if records:
            target_year = target_quarter = None
            for r in records:
                f = self._get_fields(r)
                year, quarter = f.get("year", ""), f.get("quarter", "")
                if target_year is None:
                    target_year, target_quarter = year, quarter
                if year == target_year and quarter == target_quarter:
                    s_name = f.get("lqt_l_s_r_ljry") or f.get("sector_current_prices", "")
                    rate = f.get("growth_rate")
                    if s_name and rate is not None:
                        if gdp_keywords and not any(kw in s_name for kw in gdp_keywords):
                            continue
                        result["gdp_growth"].append({
                            "sector": s_name, "rate": round(rate, 2),
                            "year": str(target_year), "quarter": str(target_quarter)
                        })
            result["gdp_growth"].sort(key=lambda x: abs(x["rate"]), reverse=True)

        # ─── GDP Annual ───
        records = get_bahrain_data("gdp_annual")
        if records:
            target_year = None
            for r in records:
                f = self._get_fields(r)
                year = f.get("year", "")
                if target_year is None and year:
                    target_year = year
                if year == target_year:
                    s_name = (f.get("lnsht_lqtsdy_bl_s_r_lthbt")
                              or f.get("lqt_l_s_r_ljry")
                              or f.get("sector", ""))
                    value = (f.get("value_bd_million")
                             or f.get("value")
                             or f.get("kp_value"))
                    if s_name and value is not None:
                        if gdp_keywords and not any(kw in s_name for kw in gdp_keywords):
                            continue
                        result["gdp_annual"].append({
                            "sector": s_name,
                            "value": round(value, 1) if isinstance(value, (int, float)) else value,
                            "year": str(target_year)
                        })
            result["gdp_annual"].sort(key=lambda x: x["value"] if isinstance(x["value"], (int, float)) else 0, reverse=True)

        # ─── CPI ───
        records = get_bahrain_data("cpi")
        if records:
            target_year = target_month = None
            for r in records:
                f = self._get_fields(r)
                year = f.get("year")
                month = f.get("lshhr") or f.get("month", "")
                if target_year is None and year:
                    target_year, target_month = year, month
                if year == target_year and month == target_month:
                    if f.get("level") in (2, 2.0):
                        category = f.get("id") or f.get("coicop_division_group", "")
                        change = f.get("percentage_change")
                        if category and change is not None:
                            if cpi_keywords and not any(kw in category for kw in cpi_keywords):
                                continue
                            result["cpi"].append({
                                "category": category,
                                "change": round(change, 2) if isinstance(change, (int, float)) else change,
                                "year": str(target_year), "month": str(target_month)
                            })

        # ─── Unemployment ───
        if is_general or "unemployment" in include_datasets:
            records = get_bahrain_data("unemployment")
            if records:
                by_year = {}
                for r in records:
                    f = self._get_fields(r)
                    year = f.get("year", "")
                    sex = f.get("ljns") or f.get("sex", "")
                    value = f.get("value")
                    if year and value is not None:
                        if year not in by_year:
                            by_year[year] = {}
                        by_year[year][sex] = value
                for year in sorted(by_year.keys(), reverse=True)[:3]:
                    data = by_year[year]
                    total = sum(v for v in data.values() if isinstance(v, (int, float)))
                    result["unemployment"].append({
                        "year": str(year), "total": total, "breakdown": data
                    })

        # ─── FDI ───
        if is_general or "fdi" in include_datasets:
            records = get_bahrain_data("fdi")
            if records:
                for r in records[:6]:
                    f = self._get_fields(r)
                    year = f.get("year", "")
                    quarter = f.get("quarter", "")
                    value = f.get("values")
                    if year and value is not None:
                        result["fdi"].append({
                            "year": str(year), "quarter": str(quarter),
                            "value": round(value, 1) if isinstance(value, (int, float)) else value
                        })

        # ─── Stock Market ───
        if is_general or "stock_market" in include_datasets:
            records = get_bahrain_data("stock_market")
            if records:
                for r in records[:3]:
                    f = self._get_fields(r)
                    year = f.get("year", "")
                    companies = f.get("no_listed_shareholding_companies_in_bahrain")
                    capital = f.get("paid_up_capital_for_shareholding_companies_in_bahrain_bhd")
                    entry = {"year": str(year)}
                    if companies is not None:
                        entry["companies"] = int(companies)
                    if capital is not None:
                        entry["capital_billion"] = round(capital / 1e9, 2)
                    result["stock_market"].append(entry)

        # ─── Imports ───
        if is_general or "imports" in include_datasets:
            records = get_bahrain_data("imports")
            if records:
                seen = set()
                for r in records:
                    f = self._get_fields(r)
                    commodity = f.get("lsl") or f.get("commodity", "")
                    value = f.get("import_value_bd")
                    country = f.get("ldwl") or f.get("country_name", "")
                    if commodity and commodity not in seen and value:
                        seen.add(commodity)
                        result["imports"].append({
                            "commodity": commodity[:60], "value": value, "country": country
                        })
                        if len(result["imports"]) >= 8:
                            break

        # ─── Tourism ───
        if is_general or "tourism" in include_datasets:
            records = get_bahrain_data("tourism")
            if records:
                skip_keys = {"n", "year", "month", "lshhr"}
                region_names = {
                    "ksa": "السعودية", "other_gcc": "دول خليجية أخرى",
                    "europe": "أوروبا", "asia": "آسيا",
                    "america": "أمريكا", "middle_east": "الشرق الأوسط",
                    "other_countries": "دول أخرى"
                }
                by_year = {}
                for r in records:
                    f = self._get_fields(r)
                    year = f.get("year", "")
                    if not year:
                        continue
                    if year not in by_year:
                        by_year[year] = {}
                    for key, val in f.items():
                        if key not in skip_keys and isinstance(val, (int, float)):
                            by_year[year][key] = by_year[year].get(key, 0) + val
                if by_year:
                    latest_year = sorted(by_year.keys(), reverse=True)[0]
                    regions = by_year[latest_year]
                    total = sum(regions.values())
                    region_list = {region_names.get(k, k): v for k, v in
                                   sorted(regions.items(), key=lambda x: x[1], reverse=True)[:6]}
                    result["tourism"].append({
                        "year": str(latest_year), "total": total, "regions": region_list
                    })

        # ─── Labor ───
        if is_general or "labor" in include_datasets:
            records = get_bahrain_data("labor")
            if records:
                target_year = None
                wages = {}
                for r in records:
                    f = self._get_fields(r)
                    year = f.get("year", "")
                    if target_year is None and year:
                        target_year = year
                    if year == target_year:
                        group = (f.get("fy_t_l_jr_lshhry_bldynr_lbhryny")
                                 or f.get("monthly_wage_groups_bahraini_dinar", ""))
                        value = f.get("value")
                        if group and isinstance(value, (int, float)):
                            wages[group] = wages.get(group, 0) + value
                for group, count in wages.items():
                    result["labor"].append({"wage_group": group, "count": count, "year": str(target_year or "")})

        # ─── Tamkeen ───
        if is_general or "tamkeen" in include_datasets:
            records = get_bahrain_data("tamkeen")
            if records:
                for r in records[:8]:
                    f = self._get_fields(r)
                    parts = []
                    for key, val in f.items():
                        if val and key != "n" and not key.startswith("_"):
                            parts.append(str(val))
                    if parts:
                        result["tamkeen"].append({"info": " | ".join(parts[:4])})

        return result
