# سجل الإنجازات - المستثمر الذكي البحريني (BSI)

> تم توثيق جميع الأعمال المنجزة عبر جلسات المحادثة من 27 فبراير حتى 11 مارس 2026

---

## نظرة عامة على المشروع

**المستثمر الذكي البحريني (BSI)** — منصة دراسة جدوى مدعومة بالذكاء الاصطناعي لمشاريع الوساطة التجارية في مملكة البحرين.

**البنية المعمارية**: Diamond Architecture
- 6 وكلاء ذكاء اصطناعي متوازيين → مُجمّع (Synthesizer) → تحليل SWOT + خطة عمل
- 3 مزودي ذكاء اصطناعي: OpenAI، Google Gemini، Anthropic Claude
- 7 مصادر بيانات حقيقية
- واجهة عربية/إنجليزية مع بث مباشر (SSE)

---

## المرحلة 1: البنية التحتية الأساسية

### الخادم (Flask Backend)
- إنشاء `app.py` — خادم Flask مع بث SSE (Server-Sent Events)
- تدفق البيانات: طلب المستخدم → 6 وكلاء بالتوازي → تجميع → SWOT + خطة عمل → حفظ في قاعدة البيانات
- مسارات API: `/analyze-stream`، `/ask-followup`، `/history`، `/export-pdf`، `/compare`، `/dashboard`

### قاعدة البيانات (`database.py`)
- جداول SQLite: `analyses`، `bahrain_data_cache`، `data_cache`
- حفظ واسترجاع التحليلات مع مشاركة عبر رمز فريد (share_token)
- لوحة إحصائيات: عدد التحليلات، متوسط التقييمات، القطاعات الأكثر دراسة

### إطار الوكلاء (`agents/`)
- `agents/base.py` — الفئة الأساسية `BaseAgent` مع `create_completion()` كواجهة موحدة لجميع المزودين
- 6 وكلاء تحليل:
  - `market_logic.py` — تحليل منطق السوق والطلب
  - `financial.py` — التحليل المالي والاستدامة
  - `competitive.py` — تحليل المنافسة والتموضع
  - `legal.py` — التحليل القانوني والتنظيمي
  - `technical.py` — التحليل التقني والبنية التحتية
  - `brokerage_models.py` — تحليل نماذج الوساطة التجارية
- `synthesizer.py` — تجميع نتائج الوكلاء الستة في حكم نهائي
- `swot.py` — تحليل نقاط القوة والضعف والفرص والتهديدات
- `action_plan.py` — خطة العمل التنفيذية بمراحل زمنية

### الواجهة الأمامية (`templates/index.html`)
- تصميم SPA بتقنية Tailwind CSS مع تأثيرات glass morphism
- معالج إعداد من 4 خطوات (Onboarding Wizard)
- عرض نتائج الوكلاء ببطاقات تفاعلية مع مؤشرات تقييم
- مخطط رادار (Chart.js) للتقييم الشامل
- نظام محادثة متابعة مع الذكاء الاصطناعي
- دعم ثنائي اللغة (عربي/إنجليزي)
- تصدير PDF + مشاركة التقارير

### بيانات السوق البحريني (`bahrain_data.py`)
- جلب بيانات حكومية من بوابة البيانات المفتوحة `data.gov.bh`
- بيانات GDP الفصلية مع تفصيل قطاعي
- 9 قطاعات مدعومة مع سياق وساطة مخصص لكل قطاع

---

## المرحلة 2: نظام التحقق من الصحة (Validation System)

### الملفات المعدّلة: جميع ملفات الوكلاء الـ 6 + المُجمّع + الواجهة

### 2.1 تحقق على مستوى الوكيل
كل وكيل يُرجع الآن حقل `validation` يحتوي:
- `confidence_score` (1-10) مع إرشادات تفصيلية للتقييم
- `confidence_reasoning` — تبرير درجة الثقة
- `data_sources_used` — مصفوفة المصادر المستخدمة مع عدد النقاط
- `assumptions` — الافتراضات الرئيسية
- `data_gaps` — الفجوات في البيانات

### 2.2 تحقق متقاطع في المُجمّع
`synthesizer.py` يقوم بالتحقق المتقاطع:
- `weighted_breakdown` — توزيع الثقة عبر الوكلاء
- `contradictions_found` — التناقضات بين الوكلاء
- `critical_data_gaps` — الفجوات الحرجة عبر جميع المصادر
- `synthesis_confidence` — ثقة التجميع الإجمالية (1-10)

### 2.3 عرض التحقق في الواجهة
- `renderAgentCard()` يعرض: درجة الثقة، المصادر، الافتراضات
- `renderVerdict()` يعرض: التناقضات، الفجوات، التوزيع المرجح

---

## المرحلة 3: إضافة مزود Claude/Anthropic كمزود ثالث

### الملفات المعدّلة: `agents/base.py`، `app.py`، `requirements.txt`، `synthesizer.py`، `swot.py`، `action_plan.py`، `index.html`

### 3.1 دعم المزود الأساسي
- `requirements.txt` — إضافة مكتبة `anthropic`
- `agents/base.py`:
  - فرع Claude في `create_completion()` مع معالجة استثناءات خاصة
  - دالة `_extract_json()` لاستخراج JSON من أغلفة markdown (Claude يلف JSON بـ ```json```)

### 3.2 نشر المزود عبر النظام
- `app.py`:
  - دالة `get_default_model(provider)` — اختيار النموذج الافتراضي حسب المزود
  - كشف مفتاح API تلقائياً: `OPENAI_API_KEY`، `ANTHROPIC_API_KEY`، `GEMINI_API_KEY`
  - دعم `synthesizer_provider` — مزود مختلف للمُجمّع
- جميع الوكلاء المتقدمين (synthesizer, swot, action_plan) تمرر `provider` و `model_override`
- معالجة استثناءات Anthropic في decorators الإعادة (retry)

### 3.3 واجهة اختيار المزود
- قائمة منسدلة بـ 3 مزودين: OpenAI، Gemini، Claude
- تحديث ديناميكي للنماذج المتاحة:
  - OpenAI: `gpt-5-mini`، `gpt-5.2`
  - Gemini: `gemini-2.5-flash`
  - Claude: `claude-sonnet-4-20250514`

---

## المرحلة 4: سبعة مصادر بيانات جديدة

### الملفات المُنشأة: 11 ملف في `data_sources/`

### 4.1 المصادر السبعة

| # | المصدر | الملف | النوع | الوصف |
|---|--------|-------|-------|-------|
| 1 | البنك الدولي | `world_bank.py` | API حي | مؤشرات GDP، تضخم، بطالة، سكان، تجارة + مؤشرات قطاعية |
| 2 | مصرف البحرين المركزي | `cbb.py` | API + احتياطي | أسعار صرف الدينار + أسعار الفائدة |
| 3 | سجلات التجاري | `sijilat.py` | بيانات مضمنة | شركات مسجلة حسب النشاط + إحصائيات تقديرية |
| 4 | Trading Economics | `trading_economics.py` | بيانات مضمنة | مؤشرات اقتصادية كلية: GDP تفصيلي، ميزان تجاري |
| 5 | بورصة البحرين | `bahrain_bourse.py` | بيانات مضمنة | شركات مدرجة + قيمة سوقية حسب القطاع |
| 6 | تمكين | `tamkeen.py` | بيانات مضمنة | برامج دعم: رواتب، تدريب، تحول رقمي، سجلي |
| 7 | مجلس التنمية الاقتصادية | `edb.py` | بيانات مضمنة | نظرة اقتصادية + حوافز استثمار + قطاعات تركيز |

### 4.2 البنية التحتية
- `data_sources/base.py` — فئة `DataSourceBase` مع `source_name`، `reliability_score`، `cache_ttl_seconds`، `fetch()`
- `data_sources/aggregator.py` — فئة `DataAggregator`:
  - `fetch_all(sector)` — جلب من جميع المصادر بالتوازي
  - `build_agent_context(sector, agent_type, aggregated)` — بناء سياق مخصص لكل وكيل
  - `SOURCE_META` — بيانات وصفية لكل مصدر
  - `AGENT_SOURCE_MAP` — خريطة: أي مصادر أساسية/ثانوية لكل وكيل
- `data_sources/sector_mapping.py` — ربط 9 قطاعات بمؤشرات كل مصدر

### 4.3 تحديث prompts الوكلاء
- جميع الوكلاء الـ 6 تم تحديث system prompts لتشير إلى المصادر السبعة
- إرشادات لاستخدام البيانات الحقيقية + ذكر المصدر عند الاستشهاد

---

## المرحلة 5: صفحة مصادر البيانات (Data Sources Dashboard)

### الملفات المعدّلة: `aggregator.py`، `app.py`، `index.html`

### 5.1 Backend
- `aggregator.py`:
  - `get_sources_meta()` — بيانات وصفية لجميع المصادر (اسم، أيقونة، نوع، وصف، موثوقية)
  - عكس `AGENT_SOURCE_MAP` لحساب أي وكلاء تستخدم كل مصدر
- `app.py`:
  - `GET /api/data-sources/meta` — metadata ثابت بدون قطاع
  - `GET /api/data-sources/fetch?sector=X` — جلب بيانات جميع المصادر لقطاع محدد

### 5.2 Frontend — تاب جديد "مصادر البيانات"
- زر تاب جديد في شريط التنقل
- اختيار قطاع + زر "جلب البيانات"
- 3 بطاقات إحصائية: نقاط البيانات، المصادر النشطة، المصادر الحية
- 7 بطاقات glass لكل مصدر مع:
  - أيقونة + اسم + وصف
  - شريط موثوقية (%)
  - شارة حالة (API حي / مضمنة / خطأ)
  - عدد نقاط البيانات + الوكلاء المستخدمين
  - زر "عرض البيانات" قابل للتوسيع
- خريطة وكيل ← مصادر
- معاينة بيانات مهيكلة: 7 formatters متخصصة (جداول/قوائم)

---

## المرحلة 6: مراجعة وتحسينات بناءً على التوصيات

### الملفات المعدّلة: `worldbank.py`، `aggregator.py`، `index.html`

### 6.1 إصلاح البنك الدولي — مؤشرات أكثر
**المشكلة**: كان يجلب 3-4 مؤشرات فقط (الخاصة بالقطاع)
**الحل**: `worldbank.py` — إضافة 5 مؤشرات أساسية لجميع القطاعات:
```python
core = ["NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG", "SP.POP.TOTL", "SL.UEM.TOTL.ZS", "NE.TRD.GNFS.ZS"]
```
**النتيجة**: ارتفع من 15 نقطة بيانات إلى 35 نقطة (لقطاع التقنية)

### 6.2 تحسين وصف المصادر
- `aggregator.py` — تحديث وصف `world_bank` من "15 مؤشراً" إلى وصف دقيق

### 6.3 ملاحظة البورصة للقطاعات الصغيرة
- `index.html` `formatBoursePreview()` — ملاحظة تلقائية عندما يكون عدد الشركات المدرجة ≤ 3:
  > "معظم شركات هذا القطاع في البحرين غير مدرجة في البورصة (شركات ناشئة وصغيرة ومتوسطة)"

### 6.4 طابع زمني + تصدير JSON
- `renderDataSourcesSummary()` — عرض وقت الجلب + اسم القطاع
- دالة `exportDataSources()` — تصدير البيانات الخام كملف JSON

### 6.5 مقارنة سريعة بين القطاعات
- شريط أزرار للتبديل السريع بين القطاعات
- دالة `quickSwitchSector()` — جلب فوري لقطاع جديد

---

## المرحلة 7: نظام شفافية مصادر البيانات (Data Attribution)

### الملفات المعدّلة: `aggregator.py`، `app.py`، `index.html`

**المشكلة**: المستخدم لا يعرف أي بيانات وصلت لأي وكيل أثناء تحليل دراسة الجدوى

### 7.1 Backend — بناء خريطة الإسناد
- `aggregator.py` — دالة `build_data_attribution(aggregated_data)`:
  - لكل وكيل: المصادر الأساسية والثانوية مع حالة كل مصدر
  - إحصائيات: نقاط البيانات الإجمالية، المصادر النشطة، إجمالي المصادر

### 7.2 Backend — حدث SSE جديد
- `app.py` — بعد بناء سياق الوكلاء وقبل تشغيلهم:
  ```python
  attribution = data_aggregator.build_data_attribution(aggregated)
  event_queue.put(("data_sources_used", json.dumps(attribution, ensure_ascii=False)))
  ```
- معالجة خاصة في حلقة SSE: لا يُخزن في `results` (ليس نتيجة وكيل)

### 7.3 Frontend — قسم عرض الإسناد
- مستمع SSE: `eventSource.addEventListener('data_sources_used', ...)`
- قسم HTML جديد بين نتائج الوكلاء ومخطط الرادار
- دالة `renderDataAttribution(attr)`:
  - **3 بطاقات ملخصة**: نقاط البيانات (62)، المصادر النشطة (7/7)، الوكلاء المدعومين (6)
  - **6 بطاقات تفصيلية** (واحدة لكل وكيل):
    - كل مصدر مع أيقونة حالة (أخضر=نشط، أحمر=خطأ، رمادي=فارغ)
    - نوع المصدر (أساسي/ثانوي)
    - عدد نقاط البيانات
  - ألوان متطابقة مع بطاقات الوكلاء (أزرق=سوق، أخضر=مالي، بنفسجي=منافسة، إلخ)

---

## إصلاحات الأخطاء

| # | الخطأ | السبب | الحل | الملف |
|---|-------|-------|------|-------|
| 1 | `NotFoundError: model: gpt-5.2` عند استخدام Claude | النموذج الافتراضي كان مشفراً لـ OpenAI | دالة `get_default_model(provider)` | `app.py` |
| 2 | Claude يرجع JSON ملفوف بـ ```json``` | Claude لا يدعم JSON mode الأصلي | دالة `_extract_json()` | `agents/base.py` |
| 3 | مسارات `/ask-followup` لا تحترم المزود | نموذج احتياطي مشفر | `model or get_default_model(provider)` | `app.py` |

---

## ملخص الملفات

### ملفات معدّلة (14 ملف)
| الملف | التغيير الرئيسي |
|-------|----------------|
| `app.py` | مزودي AI، SSE attribution، مسارات بيانات |
| `agents/base.py` | Claude provider، JSON extraction |
| `agents/market_logic.py` | Validation + data sources في prompt |
| `agents/financial.py` | Validation + data sources في prompt |
| `agents/competitive.py` | Validation + data sources في prompt |
| `agents/legal.py` | Validation + data sources في prompt |
| `agents/technical.py` | Validation + data sources في prompt |
| `agents/brokerage_models.py` | Validation + data sources في prompt |
| `agents/synthesizer.py` | Cross-validation، Anthropic support |
| `agents/swot.py` | Anthropic support، model override |
| `agents/action_plan.py` | Anthropic support، model override |
| `database.py` | جدول data_cache |
| `requirements.txt` | مكتبة anthropic |
| `templates/index.html` | جميع تحسينات الواجهة |

### ملفات مُنشأة (11 ملف)
| الملف | الوصف |
|-------|-------|
| `data_sources/__init__.py` | تهيئة الوحدة |
| `data_sources/base.py` | فئة DataSourceBase |
| `data_sources/aggregator.py` | مُجمّع البيانات + attribution |
| `data_sources/sector_mapping.py` | ربط القطاعات بالمؤشرات |
| `data_sources/world_bank.py` | البنك الدولي (API) |
| `data_sources/cbb.py` | مصرف البحرين المركزي |
| `data_sources/sijilat.py` | السجل التجاري |
| `data_sources/trading_economics.py` | مؤشرات اقتصادية |
| `data_sources/bahrain_bourse.py` | بورصة البحرين |
| `data_sources/tamkeen.py` | صندوق العمل |
| `data_sources/edb.py` | مجلس التنمية الاقتصادية |

---

## إحصائيات سريعة

- **7** مراحل تطوير رئيسية
- **14** ملف معدّل + **11** ملف جديد = **25** ملف
- **3** مزودي ذكاء اصطناعي مدعومين
- **7** مصادر بيانات حقيقية
- **6** وكلاء تحليل + 3 وكلاء متقدمين (مُجمّع + SWOT + خطة عمل)
- **9** قطاعات مدعومة
- **62** نقطة بيانات لكل تحليل (قطاع التقنية)
- **3** أخطاء حرجة تم إصلاحها
