# 🔮 Smart Investor — المستثمر الذكي البحريني

أداة دراسات جدوى احترافية لمشاريع الوساطة التجارية في مملكة البحرين، مدعومة بـ ٦ وكلاء ذكاء اصطناعي يعملون بالتوازي على مصادر بيانات حقيقية.

> **شاهد شرح الإصدار الأول على يوتيوب:**  
> [![فيديو الشرح](https://img.youtube.com/vi/S5shoHtZMAk/maxresdefault.jpg)](https://youtu.be/S5shoHtZMAk)

## البنية الحالية (Production)

```
┌──────────────────────────────────────┐         ┌──────────────────────────────────────┐
│ hawsh-khalifa.lovable.app            │         │ smart-investor-api.onrender.com      │
│ React + Vite + Tailwind + shadcn     │ ──JWT──>│ Flask 3 + gunicorn                   │
│ Supabase Auth + DB                   │         │ Supabase JWT verify · Flask-Limiter  │
│ /tools/smart-investor                │         │ Redis · SQLite (WAL) · Perplexity AI │
└──────────────────────────────────────┘         └──────────────────────────────────────┘
```

- **Frontend**: مكوّنات React في مجلد `lovable/` تُنسخ إلى مشروع Lovable.dev (انظر [`lovable/README.md`](lovable/README.md))
- **Backend**: Flask API-only في هذا الـ repo، نشر على Render
- **Auth**: Supabase JWT إلزامي على كل المسارات الحساسة
- **Rate limit**: ٥ تحليلات/يوم لكل مستخدم، ٣٠ طلب/دقيقة لكل IP
- **PII**: مشفّرة عند الكتابة بـ Fernet (AES-128 + HMAC-SHA256)

## 🏗️ هيكل المشروع

```
smart-investor/
├── app.py                    # Application factory (60 سطر)
├── config.py                 # تحميل env vars
├── auth.py                   # Supabase JWT decorator
├── extensions.py             # CORS + Limiter + security headers
├── database.py               # SQLite WAL + cleanup + PII encryption
├── routes/                   # Blueprints
│   ├── analysis.py           # /api/analyze, /api/analyses/*
│   ├── data.py               # /api/sectors, /api/data-sources/*
│   ├── admin.py              # /api/admin/*
│   └── reference_data.py     # COMPANIES و SOLUTIONS
├── services/                 # منطق الأعمال خارج الـ routes
│   ├── analysis_orchestrator.py  # SSE pipeline 6 وكلاء + synthesis
│   ├── followup_service.py       # المحادثة الذكية بعد التحليل
│   └── pdf_service.py            # تصدير PDF
├── utils/                    # أدوات
│   ├── sanitize.py           # دفاع من prompt injection
│   ├── tokens.py             # secrets.token_urlsafe
│   └── crypto.py             # تشفير PII
├── agents/                   # وكلاء AI (6 + synthesizer + swot + action plan)
├── data_sources/             # ربط بـ data.gov.bh, IMF, World Bank, إلخ
├── lovable/                  # ملفات React جاهزة للنسخ في Lovable
└── DEPLOYMENT.md             # دليل النشر التفصيلي
```

## 🚀 التشغيل المحلي

### 1. متطلبات

- Python 3.12+
- (اختياري) Redis للـ rate limiting في multi-process

### 2. الإعداد

```bash
git clone <repo-url>
cd smart-investor
python -m venv .venv
.venv/Scripts/activate    # Windows
# source .venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
cp .env.example .env
# عدّل .env: ضع PERPLEXITY_API_KEY و SUPABASE_JWT_SECRET على الأقل
```

### 3. التشغيل

```bash
python app.py
# الخادم: http://localhost:5000
# health: curl http://localhost:5000/api/health
```

## 📡 API Endpoints

| المسار | الوصف | المصادقة |
|--------|------|---------|
| `GET /api/health` | حالة الخدمة | عام |
| `GET /api/sectors` | قائمة القطاعات | عام |
| `GET /api/sectors/<sector>/market` | بيانات قطاع | عام |
| `GET /api/data-sources/meta` | metadata المصادر | عام |
| `GET /api/providers` | مزودي AI المدعومين | عام |
| `GET /api/share/<token>` | عرض تحليل مشترك | عام |
| `POST /api/analyze` | بدء تحليل (SSE) | JWT |
| `GET /api/analyses` | قائمة تحليلاتي | JWT |
| `GET /api/analyses/<id>` | تحليل واحد | JWT |
| `DELETE /api/analyses/<id>` | حذف تحليل | JWT |
| `POST /api/analyses/<id>/rate` | تقييم | JWT |
| `POST /api/analyses/<id>/followup` | محادثة بعد التحليل | JWT |
| `GET /api/analyses/<id>/export-pdf` | تنزيل PDF | JWT |
| `GET /api/dashboard` | إحصائيات شخصية | JWT |
| `POST /api/analyze-market-needs` | تحليل سريع | JWT |
| `POST /api/gap-analysis` | تحليل فجوات (SSE) | JWT |
| `POST /api/admin/sync-data` | تحديث بيانات البحرين | Admin |
| `POST /api/admin/cleanup-expired` | حذف منتهيي الصلاحية | Admin |

## 🔒 الإصلاحات الأمنية المطبّقة

- ✅ Supabase JWT verification على كل المسارات الحساسة
- ✅ CORS allowlist (لا wildcard)
- ✅ Rate limiting بـ Redis (multi-process safe)
- ✅ Tokens آمنة (`secrets.token_urlsafe(32)` بدلاً من UUID hex مقتطع)
- ✅ تشفير PII عند الكتابة (Fernet)
- ✅ Sanitization ضد prompt injection
- ✅ Security headers (HSTS, X-Frame-Options, X-Content-Type-Options)
- ✅ SQLite WAL mode + indexes
- ✅ Cleanup job للسجلات المنتهية (APScheduler)
- ✅ Owner-scoped queries (لا تسرّب بين المستخدمين)
- ❌ تم حذف قبول API keys من URL params
- ❌ تم حذف endpoint كتابة `.env` من الواجهة

## 🔮 وكلاء التحليل

كل التحليل يستخدم **Perplexity Sonar Pro** عبر مفتاح واحد على الخادم. الوكلاء يعملون بالتوازي عبر `ThreadPoolExecutor`:

1. **MarketLogic** — حجم السوق، الطلب، الاتجاهات
2. **Financial** — اقتصاديات الوحدة، التكاليف، نقطة التعادل
3. **Competitive** — المنافسون من السجل التجاري + الخندق
4. **Legal** — التراخيص، الجمارك، الالتزام التنظيمي
5. **Technical** — البنية التقنية المطلوبة
6. **BrokerageModels** — نماذج الوساطة المقترحة

ثم **Synthesizer** يُجمّع الستة، ثم **SWOT + ActionPlan** بالتوازي.

## 📚 وثائق إضافية

- [دليل النشر الكامل](DEPLOYMENT.md)
- [دليل دمج Lovable.dev](lovable/README.md)
- [وصف المشروع التفصيلي](PROJECT_DESCRIPTION.md)
- [سجل التغييرات](CHANGELOG.md)
