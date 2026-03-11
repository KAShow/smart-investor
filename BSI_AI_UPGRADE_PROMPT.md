# Bahrain Smart Investor AI — ترقية شاملة للمستثمر الذكي

## السياق

هذا المشروع هو نظام استشارات استثمارية مدعوم بالذكاء الاصطناعي يحلل جدوى أفكار الوساطة التجارية في البحرين. يعمل بـ 6 وكلاء متخصصين + وكيل تجميع (Synthesizer) بنمط Diamond Structure. مبني بـ Python/Flask + SQLite + Tailwind CSS. يدعم حالياً OpenAI و Google Gemini فقط.

المطلوب: تنفيذ 4 ترقيات رئيسية بالترتيب التالي.

---

## المهمة 1: إضافة Anthropic/Claude كمزود ذكاء اصطناعي

### المتطلبات

- أضف `anthropic` Python SDK كـ dependency
- أنشئ provider جديد `ClaudeProvider` بنفس interface المزودين الحاليين (OpenAI, Gemini)
- النماذج المدعومة:
  - `claude-sonnet-4-20250514` — للوكلاء الستة (أسرع وأرخص)
  - `claude-sonnet-4-20250514` — للـ Synthesizer (الحكم النهائي)
- الـ Synthesizer يجب أن يستخدم Claude افتراضياً حتى لو المستخدم اختار مزود آخر للوكلاء — أضف خيار `synthesizer_provider` منفصل في الإعدادات
- تأكد من دعم:
  - Streaming (SSE) لمتابعة التقدم لحظة بلحظة
  - Async calls عبر `asyncio` للتوازي
  - Retry logic عبر `tenacity` مثل المزودين الآخرين
  - Error handling موحد مع باقي المزودين
- أضف `ANTHROPIC_API_KEY` في ملف الإعدادات/البيئة
- حدّث واجهة اختيار المزود في الـ frontend لتشمل Claude مع أيقونة مناسبة

### الاختبار

- تأكد إن كل وكيل يشتغل مع Claude بشكل مستقل
- تأكد إن الـ streaming يعمل بدون انقطاع
- تأكد إن الـ fallback يشتغل (لو Claude فشل، يرجع للمزود البديل)

---

## المهمة 2: إضافة مصادر البيانات الجديدة

### البنية المطلوبة

أنشئ module جديد `data_sources/` يحتوي على ملف لكل مصدر بيانات. كل مصدر يطبّق interface موحد:

```python
class DataSourceBase:
    """Interface موحد لجميع مصادر البيانات"""

    async def fetch(self, sector: str) -> dict:
        """جلب البيانات حسب القطاع"""
        raise NotImplementedError

    def get_cache_key(self, sector: str) -> str:
        """مفتاح التخزين المؤقت"""
        raise NotImplementedError

    @property
    def source_name(self) -> str:
        """اسم المصدر للتوثيق"""
        raise NotImplementedError

    @property
    def reliability_score(self) -> float:
        """درجة موثوقية المصدر من 0 إلى 1"""
        raise NotImplementedError
```

### المصادر المطلوبة

#### 2.1 — Sijilat.io API (الأولوية القصوى)

- **الملف**: `data_sources/sijilat.py`
- **الـ Endpoint**: `https://sijilat.io/api/` (تحقق من التوثيق الفعلي)
- **البيانات المطلوبة لكل قطاع**:
  - عدد الشركات المسجلة في القطاع حالياً
  - عدد التسجيلات الجديدة آخر 12 شهر (معدل نمو السوق)
  - عدد السجلات الملغاة آخر 12 شهر (معدل الخروج)
  - توزيع الشركات حسب الحجم (فردي، صغير، متوسط، كبير)
  - توزيع الملكية (بحريني / أجنبي)
- **الوكلاء المستفيدون**: CompetitiveAgent (أساسي)، MarketLogicAgent (ثانوي)
- **Fallback**: لو الـ API غير متاح، استخدم آخر بيانات مخزنة مؤقتاً مع تحذير بتاريخ آخر تحديث
- **Cache**: 24 ساعة

#### 2.2 — Central Bank of Bahrain API

- **الملف**: `data_sources/cbb.py`
- **الـ Endpoint**: `https://cbb.gov.bh/openapi/ExchangeRate` + endpoints أخرى
- **البيانات المطلوبة**:
  - أسعار الصرف الحالية (BHD/USD, BHD/EUR, BHD/SAR)
  - سعر الفائدة الأساسي (Base Rate)
  - حجم التسهيلات الائتمانية للقطاع الخاص
  - معدل القروض المتعثرة (NPL ratio)
- **الوكلاء المستفيدون**: FinancialAgent (أساسي)
- **Cache**: 6 ساعات لأسعار الصرف، 7 أيام للبيانات الأخرى

#### 2.3 — World Bank API

- **الملف**: `data_sources/worldbank.py`
- **الـ Endpoint**: `https://api.worldbank.org/v2/country/BHR/indicator/`
- **المؤشرات المطلوبة** (مع كود كل مؤشر):
  - `NY.GDP.MKTP.CD` — الناتج المحلي الإجمالي
  - `NY.GDP.MKTP.KD.ZG` — معدل نمو GDP
  - `FP.CPI.TOTL.ZG` — معدل التضخم
  - `BX.KLT.DINV.WD.GD.ZS` — الاستثمار الأجنبي المباشر (% من GDP)
  - `SL.UEM.TOTL.ZS` — معدل البطالة
  - `IC.BUS.EASE.XQ` — سهولة ممارسة الأعمال
  - `GC.DOD.TOTL.GD.ZS` — الدين الحكومي (% من GDP)
- **الوكلاء المستفيدون**: FinancialAgent، MarketLogicAgent
- **Format**: JSON (`format=json` في الطلب)
- **Cache**: 30 يوم (البيانات سنوية/فصلية)

#### 2.4 — Trading Economics (Web Scraping أو API)

- **الملف**: `data_sources/trading_economics.py`
- **المصدر**: `https://tradingeconomics.com/bahrain/`
- **البيانات المطلوبة حسب القطاع**:
  - GDP from Agriculture / Construction / Manufacturing / Mining / Services / Transport
  - مؤشر أسعار المستهلك حسب الفئة (Housing, Transportation, Food)
  - معدل نمو الائتمان للقطاع الخاص
- **الأهمية**: هذا المصدر الوحيد اللي يوفر GDP مقسم حسب القطاع — ضروري لجعل التحليل sector-specific
- **الوكلاء المستفيدون**: MarketLogicAgent (أساسي)، FinancialAgent
- **ملاحظة**: تحقق من وجود API مجاني أولاً. لو ما فيه، استخدم web scraping مع احترام rate limits
- **Cache**: 7 أيام

#### 2.5 — Bahrain Bourse

- **الملف**: `data_sources/bahrain_bourse.py`
- **المصدر**: `https://bahrainbourse.com/`
- **البيانات المطلوبة**:
  - أداء المؤشر العام (Bahrain All Share Index)
  - أداء القطاعات (Financials, Industrials, Services, إلخ)
  - حجم التداول حسب القطاع
  - الملكية الأجنبية حسب القطاع
- **الوكلاء المستفيدون**: FinancialAgent، CompetitiveAgent
- **Cache**: يوم واحد

#### 2.6 — بيانات تمكين (Tamkeen)

- **الملف**: `data_sources/tamkeen.py`
- **المصدر**: `https://www.tamkeen.bh/` + تقارير منشورة
- **البيانات المطلوبة**:
  - برامج الدعم المتاحة حالياً حسب نوع المشروع
  - نسبة التمويل المتاحة (حتى 50% من المبلغ المطلوب)
  - برنامج دعم الأجور (حتى 36 شهر)
  - برنامج التمكين الرقمي (Digital Enablement Program)
  - برنامج سجلي (Sijili) — للأنشطة المنزلية/الافتراضية (71 نشاط مسموح)
- **الوكلاء المستفيدون**: FinancialAgent (تخفيض التكاليف)، LegalAgent (المتطلبات)
- **ملاحظة**: هذي البيانات ممكن تكون شبه ثابتة — خزّنها كـ structured JSON محلي وحدّثها يدوياً كل شهر مع إمكانية web scraping للتحديثات
- **Cache**: 30 يوم

#### 2.7 — EDB Annual Reports & Sector Data

- **الملف**: `data_sources/edb.py`
- **المصدر**: `https://www.bahrainedb.com/` + التقارير السنوية
- **البيانات المطلوبة**:
  - حجم الاستثمارات حسب القطاع (سنوي)
  - عدد المشاريع الجديدة حسب القطاع
  - الوظائف المتوقعة حسب القطاع
  - القطاعات المستهدفة حالياً (financial services, ICT, manufacturing, logistics, tourism)
- **الوكلاء المستفيدون**: MarketLogicAgent
- **ملاحظة**: خزّن بيانات التقارير السنوية كـ JSON ثابت وحدّثها سنوياً
- **Cache**: 90 يوم

### Sector Mapping

أنشئ ملف `data_sources/sector_mapping.py` يربط القطاعات التسعة في النظام بالتصنيفات المستخدمة في كل مصدر بيانات:

```python
SECTOR_MAP = {
    "restaurants_food": {
        "sijilat_activities": ["مطعم", "مقهى", "خدمات ضيافة", "تموين أغذية"],
        "trading_economics_gdp": "GDP from Services",
        "bahrain_bourse_sector": "Consumer Non-Cyclicals",
        "worldbank_indicators": ["NV.SRV.TOTL.ZS"],  # Services value added
        "edb_sector": "tourism",
        "tamkeen_category": "food_hospitality"
    },
    "real_estate": {
        "sijilat_activities": ["عقارات", "مقاولات", "بناء وتشييد"],
        "trading_economics_gdp": "GDP from Construction",
        "bahrain_bourse_sector": "Real Estate",
        "worldbank_indicators": ["NV.IND.TOTL.ZS"],
        "edb_sector": "manufacturing",
        "tamkeen_category": "construction"
    },
    "ict": {
        "sijilat_activities": ["تقنية معلومات", "اتصالات", "برمجيات"],
        "trading_economics_gdp": "GDP from Services",
        "bahrain_bourse_sector": "Technology",
        "worldbank_indicators": ["IT.NET.USER.ZS"],
        "edb_sector": "ict",
        "tamkeen_category": "technology"
    },
    "financial_services": {
        "sijilat_activities": ["تأمين", "وساطة مالية", "صرافة"],
        "trading_economics_gdp": "GDP from Services",
        "bahrain_bourse_sector": "Financials",
        "worldbank_indicators": ["FS.AST.PRVT.GD.ZS"],
        "edb_sector": "financial_services",
        "tamkeen_category": "financial"
    },
    "manufacturing": {
        "sijilat_activities": ["تصنيع", "مصنع", "إنتاج"],
        "trading_economics_gdp": "GDP from Manufacturing",
        "bahrain_bourse_sector": "Industrials",
        "worldbank_indicators": ["NV.IND.MANF.ZS"],
        "edb_sector": "manufacturing",
        "tamkeen_category": "industrial"
    },
    "healthcare": {
        "sijilat_activities": ["صحة", "طبي", "صيدلة", "أجهزة طبية"],
        "trading_economics_gdp": "GDP from Services",
        "bahrain_bourse_sector": "Consumer Non-Cyclicals",
        "worldbank_indicators": ["SH.XPD.CHEX.GD.ZS"],
        "edb_sector": "other",
        "tamkeen_category": "healthcare"
    },
    "education": {
        "sijilat_activities": ["تعليم", "تدريب", "معهد"],
        "trading_economics_gdp": "GDP from Services",
        "bahrain_bourse_sector": "Consumer Cyclicals",
        "worldbank_indicators": ["SE.XPD.TOTL.GD.ZS"],
        "edb_sector": "other",
        "tamkeen_category": "education"
    },
    "logistics": {
        "sijilat_activities": ["نقل", "شحن", "تخزين", "تخليص جمركي"],
        "trading_economics_gdp": "GDP from Transport",
        "bahrain_bourse_sector": "Industrials",
        "worldbank_indicators": ["IS.SHP.GOOD.TU"],
        "edb_sector": "logistics",
        "tamkeen_category": "logistics"
    },
    "retail": {
        "sijilat_activities": ["تجارة تجزئة", "تجارة جملة", "بيع"],
        "trading_economics_gdp": "GDP from Services",
        "bahrain_bourse_sector": "Consumer Cyclicals",
        "worldbank_indicators": ["NE.TRD.GNFS.ZS"],
        "edb_sector": "other",
        "tamkeen_category": "retail"
    }
}
```

### Data Aggregator

أنشئ `data_sources/aggregator.py` — المنسق المركزي:

```python
class DataAggregator:
    """يجمع البيانات من جميع المصادر ويوزعها على الوكلاء"""

    async def fetch_all(self, sector: str) -> dict:
        """
        يجلب من جميع المصادر بالتوازي.
        لو مصدر فشل، يسجل التحذير ويكمل بالباقي.
        يرجع dict فيه:
        - data: البيانات مجمعة حسب المصدر
        - metadata: تاريخ الجلب، المصادر الناجحة/الفاشلة
        - warnings: أي تحذيرات (بيانات قديمة، مصادر غير متاحة)
        """
        pass

    def get_agent_data(self, sector: str, agent_type: str) -> dict:
        """
        يرجع البيانات المخصصة لوكيل معين.
        كل وكيل يستلم فقط البيانات المتعلقة بتخصصه.
        """
        pass
```

### Caching Strategy

- استخدم جدول جديد في SQLite: `data_cache`
- الأعمدة: `source_name`, `sector`, `cache_key`, `data_json`, `fetched_at`, `expires_at`
- عند الطلب: تحقق من الـ cache أولاً → لو منتهي أو غير موجود → fetch جديد
- لو الـ fetch فشل والـ cache موجود (حتى لو منتهي) → استخدم الـ cache مع تحذير

---

## المهمة 3: نظام Validation (طبقتين)

### الطبقة 1: Agent-Level Validation

كل وكيل من الستة يجب أن يُرجع مع تحليله الحقول التالية إضافةً للتحليل الحالي:

```json
{
  "analysis": "... التحليل الحالي ...",
  "validation": {
    "confidence_score": 7.5,
    "confidence_reasoning": "بيانات Sijilat أظهرت 340 شركة مسجلة لكن لا توجد بيانات عن حجم الإيرادات",
    "data_sources_used": [
      {"name": "Sijilat.io", "data_points": 3, "freshness": "2026-03-10"},
      {"name": "data.gov.bh", "data_points": 5, "freshness": "2026-01-15"}
    ],
    "assumptions": [
      "افتراض أن معدل نمو القطاع سيستمر بنفس الوتيرة",
      "افتراض عدم دخول منافس كبير جديد خلال 12 شهر"
    ],
    "data_gaps": [
      "لا تتوفر بيانات عن حجم السوق الفعلي بالدينار",
      "لا تتوفر بيانات عن هوامش ربح الشركات القائمة"
    ]
  }
}
```

#### قواعد حساب Confidence Score

عدّل system prompt كل وكيل ليشمل التعليمات التالية:

```
## قواعد تحديد Confidence Score

أعطِ confidence score من 1 إلى 10 بناءً على:

- 9-10: بيانات حقيقية كافية ومحدثة + خبرة واضحة بالسوق البحريني + لا افتراضات جوهرية
- 7-8: بيانات حقيقية متوفرة لكن غير كاملة + افتراض أو اثنين بسيطين
- 5-6: بيانات جزئية فقط + عدة افتراضات مهمة + بعض الجوانب غير مغطاة
- 3-4: بيانات قليلة جداً + التحليل يعتمد بشكل أساسي على افتراضات عامة
- 1-2: لا بيانات متاحة تقريباً + التحليل نظري بالكامل

لا تبالغ في الـ confidence. إذا لم تجد بيانات كافية، أعطِ score منخفض بصراحة.
يجب أن يكون confidence_reasoning جملة أو جملتين تشرح السبب الرئيسي.
```

### الطبقة 2: Cross-Validation في الـ Synthesizer

عدّل system prompt الـ Synthesizer ليشمل:

```
## تعليمات Cross-Validation

قبل إصدار الحكم النهائي، نفّذ الخطوات التالية:

### 1. فحص التناقضات
افحص كل زوج من التحليلات الستة بحثاً عن تناقضات:
- هل الوكيل المالي يقول "ربحية ممتازة" بينما وكيل المنافسة يقول "أسعار تحت ضغط"؟
- هل وكيل الطلب يقول "سوق مشبع" بينما المحلل القانوني يقول "حواجز دخول منخفضة"؟
- هل الوكيل التقني يقول "تنفيذ بسيط" بينما الوكيل المالي يقول "تكاليف تشغيل مرتفعة"؟

لكل تناقض: اشرحه وحدد أي وكيل أقرب للصواب بناءً على confidence scores والبيانات المتاحة.

### 2. الوزن بناءً على Confidence
لا تعامل جميع التحليلات بنفس الوزن:
- وكيل بـ confidence 9 يأخذ وزن أعلى بكثير من وكيل بـ confidence 4
- لو وكيل أساسي (مثل المالي أو المنافسة) عنده confidence أقل من 5، نبّه المستخدم إن التحليل يحتاج مراجعة بشرية

### 3. إبراز فجوات البيانات
اجمع كل data_gaps من الوكلاء الستة في قسم موحد. رتبها حسب الأهمية.
أخبر المستخدم: "التحليل يفتقر للبيانات التالية — الحصول عليها سيحسن دقة التقييم بشكل كبير."

### 4. هيكل الحكم النهائي
```

```json
{
  "final_verdict": {
    "score": 7.2,
    "label": "فرصة واعدة",
    "summary": "...",
    "weighted_breakdown": {
      "market_demand": {"score": 8, "weight": 0.9, "confidence": 8},
      "financial": {"score": 7, "weight": 0.7, "confidence": 6},
      "competition": {"score": 6, "weight": 1.0, "confidence": 9},
      "legal": {"score": 8, "weight": 0.8, "confidence": 7},
      "technical": {"score": 7, "weight": 0.6, "confidence": 5},
      "brokerage_model": {"score": 7, "weight": 0.7, "confidence": 6}
    },
    "contradictions_found": [
      {
        "agents": ["FinancialAgent", "CompetitiveAgent"],
        "description": "الوكيل المالي يتوقع هامش ربح 25% لكن وكيل المنافسة يشير لضغط أسعار شديد",
        "resolution": "الأرجح أن الهامش سيكون أقل (15-18%) في أول سنتين بسبب المنافسة"
      }
    ],
    "critical_data_gaps": [
      "حجم السوق الفعلي بالدينار غير متوفر — يُنصح بإجراء مسح ميداني",
      "لا توجد بيانات عن رضا العملاء عن الخدمات الحالية"
    ],
    "overall_confidence": 7.1,
    "recommendation": "..."
  }
}
```

---

## المهمة 4: تحديث الوكلاء لاستخدام البيانات الجديدة

### 4.1 — MarketLogicAgent (محلل الطلب)

أضف في الـ system prompt:

```
## بيانات إضافية متاحة لك

ستتلقى مع طلب التحليل البيانات التالية:
- **GDP القطاعي** من Trading Economics: نمو الناتج المحلي للقطاع المحدد
- **بيانات الاستثمار** من EDB: حجم الاستثمارات والمشاريع الجديدة في القطاع
- **عدد الشركات المسجلة** من Sijilat: كمؤشر على حجم النشاط في السوق
- **بيانات الاستيراد/التصدير** من data.gov.bh: لتقييم حركة التجارة في القطاع

استخدم هذه البيانات لتقديم أرقام حقيقية بدلاً من التقديرات العامة.
عند ذكر أي رقم، اذكر مصدره. إذا لم تتوفر بيانات، صرّح بذلك ولا تختلق أرقاماً.
```

### 4.2 — FinancialAgent (المحلل المالي)

أضف في الـ system prompt:

```
## بيانات إضافية متاحة لك

- **سعر الفائدة** من CBB: لحساب تكلفة التمويل الفعلية
- **أسعار الصرف** من CBB: للتكاليف المستوردة
- **برامج تمكين المتاحة**: دعم الأجور (حتى 36 شهر)، منح المشاريع (حتى 50% من التكلفة)
- **بيانات الدين الحكومي والتضخم** من World Bank: للسياق الاقتصادي العام
- **أداء البورصة القطاعي**: كمؤشر على صحة القطاع المالية

عند حساب نقطة التعادل وتكاليف التشغيل:
- استخدم سعر الفائدة الفعلي من CBB بدلاً من تقدير
- احسب تأثير دعم تمكين على التكاليف (أضف سيناريو "مع دعم تمكين" و"بدون")
- استخدم معدل التضخم الفعلي لتعديل التوقعات المالية
```

### 4.3 — CompetitiveAgent (محلل المنافسة)

أضف في الـ system prompt:

```
## بيانات إضافية متاحة لك

- **بيانات Sijilat** (الأهم): عدد الشركات المسجلة في القطاع، التسجيلات الجديدة، الإلغاءات
- **الملكية الأجنبية** من البورصة: كمؤشر على جاذبية القطاع للمستثمرين الخارجيين

استخدم بيانات Sijilat لتقديم:
- عدد المنافسين الفعلي (ليس تقدير)
- معدل دخول منافسين جدد (تسجيلات جديدة / 12 شهر)
- معدل خروج (إلغاءات / 12 شهر)
- Churn rate = (دخول - خروج) / إجمالي
- إذا معدل الدخول > معدل الخروج بكثير = سوق جذاب لكن يزداد تشبعاً
- إذا معدل الخروج > معدل الدخول = سوق صعب أو يتقلص
```

### 4.4 — LegalAgent (المحلل القانوني)

أضف في الـ system prompt:

```
## بيانات إضافية متاحة لك

- **متطلبات سجلي (Sijili)**: 71 نشاط تجاري يمكن ممارسته بدون عنوان مكتب فعلي
- **برامج تمكين القانونية**: دعم تكاليف التراخيص والتسجيل
- **تصنيف أنشطة Sijilat**: قائمة 350+ نشاط تجاري مع متطلبات كل نشاط

تحقق هل نشاط الوساطة المطلوب ضمن قائمة سجلي (Sijili) أم يحتاج سجل تجاري كامل.
هذا يؤثر بشكل مباشر على التكاليف الأولية.
```

### 4.5 — TechnicalAgent (المحلل التقني)

لا تغييرات كبيرة — يبقى كما هو مع تحديث طفيف:

```
## سياق إضافي

- نسبة مستخدمي الإنترنت في البحرين: 100% (من World Bank)
- تمكين تقدم برنامج التمكين الرقمي (Digital Enablement Program) يغطي تكاليف الحلول التقنية
- أضف في توصياتك: هل المشروع مؤهل لدعم التمكين الرقمي؟
```

### 4.6 — BrokerageModelsAgent (محلل نماذج الوساطة)

```
## بيانات إضافية متاحة لك

- **بيانات Sijilat**: عدد شركات الوساطة المسجلة فعلاً في القطاع ونوع نماذجها
- **بيانات EDB**: هل القطاع مستهدف من الحكومة؟ (هذا يؤثر على جدوى النماذج)

عند مقارنة النماذج الستة، استخدم بيانات السوق الفعلية لتحديد أي نموذج الأنسب.
لا تعطِ مقارنة نظرية — اربط كل نموذج بواقع السوق البحريني.
```

---

## تعليمات تنفيذ عامة

### الأولويات

1. المهمة 3 (Validation) — الأعلى أولوية لأنها تحسّن جودة المخرجات فوراً
2. المهمة 1 (Claude Provider) — لأن الـ Synthesizer يحتاجه
3. المهمة 2 (Data Sources) — الأكبر حجماً، نفّذها source by source
4. المهمة 4 (Agent Prompts) — تعتمد على المهمة 2

### معايير الجودة

- كل مصدر بيانات يجب أن يعمل بشكل مستقل — لو فشل مصدر، باقي النظام يكمل
- لا تكسر أي functionality موجودة — كل التغييرات إضافية
- أضف logging واضح لكل data fetch (نجاح/فشل/cache hit)
- أضف tests لكل data source على الأقل:
  - Test: fetch بنجاح
  - Test: handling لو الـ API غير متاح
  - Test: cache يعمل بشكل صحيح
  - Test: sector mapping صحيح

### ملاحظات مهمة

- بعض الـ APIs قد تحتاج API keys — أضفها في `.env` مع توثيق واضح
- Trading Economics قد لا يوفر API مجاني — ابحث عن بدائل أو استخدم web scraping محترم
- Sijilat.io هو طرف ثالث (ليس حكومي رسمي) — تأكد من شروط الاستخدام
- لو مصدر بيانات يحتاج اشتراك مدفوع، أنشئ الـ module بالكامل لكن اجعله optional مع flag في الإعدادات
