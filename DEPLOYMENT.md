# دليل النشر — Smart Investor API + واجهة Lovable

## نظرة عامة

```
[hawsh-khalifa.lovable.app]  ──Bearer JWT──>  [smart-investor-api.onrender.com]
React + Vite + Supabase                       Flask + Redis + SQLite
```

- **Backend**: Flask 3 على Render، يحمي كل المسارات بـ Supabase JWT
- **Frontend**: مكوّنات React في مجلد `lovable/` تُنسخ يدوياً إلى مشروع Lovable
- **Auth**: Supabase (مجاناً حتى 50K MAU)
- **Rate limiting**: Redis (Upstash مجاني أو Render Redis)
- **AI**: Perplexity Sonar — مفتاح واحد للمالك يدفع للجميع

## الخطوات بالترتيب

### 1. Supabase (إذا لم يكن جاهزاً)

1. أنشئ مشروع Supabase على https://supabase.com
2. من **Settings → API**، انسخ:
   - **Project URL** → `SUPABASE_URL`
   - **JWT Secret** → `SUPABASE_JWT_SECRET`
   - **anon (public) key** → `VITE_SUPABASE_ANON_KEY` (للواجهة فقط)
3. من **Authentication → Providers**، فعّل Email + Google (حسب رغبتك)

### 2. توليد مفاتيح التشفير

```bash
# مفتاح Fernet لتشفير PII في قاعدة البيانات
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# مفتاح Flask sessions
python -c "import secrets; print(secrets.token_hex(32))"
```

احتفظ بهما — ستضعهما في Render env vars.

### 3. نشر Flask على Render

1. اربط الـ repo بـ Render: New → Blueprint → اختر هذا الـ repo
2. Render سيقرأ `render.yaml` وينشئ تلقائياً:
   - خدمة Web `smart-investor-api` (Python 3.12.8)
   - خدمة Redis `smart-investor-redis` (مجاناً)
3. عند الطلب، أدخل المتغيرات السرية في Render Dashboard:

| المتغير | القيمة |
|---------|--------|
| `PERPLEXITY_API_KEY` | مفتاحك من perplexity.ai/account |
| `SUPABASE_URL` | من Supabase Settings → API |
| `SUPABASE_JWT_SECRET` | من Supabase Settings → API → JWT Secret |
| `FERNET_KEY` | (Render سيولّده تلقائياً عبر `generateValue: true`) |
| `FLASK_SECRET_KEY` | (Render سيولّده تلقائياً) |
| `ADMIN_USER_IDS` | UUID حسابك في Supabase (auth.users.id) — يفعّل /api/admin/* |

4. اضغط **Apply** وانتظر deploy (~3-5 دقائق)
5. تحقق: `curl https://smart-investor-api.onrender.com/api/health` يجب 200 `{"status":"ok"}`

### 4. نشر الواجهة في Lovable.dev

1. افتح مشروعك على Lovable (`hawsh-khalifa.lovable.app`)
2. **Project Settings → Environment Variables** أضف:
   ```
   VITE_SMART_INVESTOR_API=https://smart-investor-api.onrender.com
   ```
3. ثبّت الحزم الإضافية من Lovable IDE → Install package:
   - `react-markdown`
   - `rehype-sanitize`
   - `zod`
   - `react-hook-form`
   - `@hookform/resolvers`
4. انسخ ملفات `lovable/src/` من هذا الـ repo إلى مشروع Lovable بنفس البنية (راجع `lovable/README.md`)
5. أضف المسار في `App.tsx`:
   ```tsx
   <Route path="/tools/smart-investor" element={<SmartInvestor />} />
   ```
6. أضف بطاقة في صفحة `/learn` أو `/tools` تربط للأداة الجديدة

### 5. اختبار end-to-end

| الخطوة | التحقق |
|--------|--------|
| تسجيل دخول في Lovable | يفتح الجلسة Supabase |
| فتح `/tools/smart-investor` | تظهر شبكة القطاعات |
| اختيار قطاع + إرسال نموذج | يبدأ stream الـ SSE فوراً |
| متابعة المراحل | `data_sources_used → 6 وكلاء → final_verdict → swot → action_plan → done` |
| التحقق من DB | `analyses` يحتوي صفاً جديداً مع `user_id` |
| تنزيل PDF | الزر يفتح `/api/analyses/<id>/export-pdf` |
| محاولة 6 تحليلات في يوم واحد | السادس يرجع 429 |

## اختبارات الأمان السريعة

```bash
# 1. لا قبول لمفاتيح API في URL
curl -X POST 'https://smart-investor-api.onrender.com/api/analyze?api_key=fake' \
  -H 'Content-Type: application/json' -d '{"sector":"food_hospitality"}'
# المتوقع: 401 unauthorized (المفتاح في URL يُتجاهل تماماً)

# 2. CORS لا يسمح بـ origins غير مدرجة
curl -H 'Origin: https://evil.example' -i https://smart-investor-api.onrender.com/api/sectors
# لا يجب أن يظهر Access-Control-Allow-Origin

# 3. Auth إجباري
curl -X POST https://smart-investor-api.onrender.com/api/analyze \
  -H 'Content-Type: application/json' -d '{"sector":"food_hospitality"}'
# المتوقع: 401

# 4. Rate limiting يعمل (محاولة من نفس المستخدم 10 مرات)
for i in {1..10}; do
  curl -s -o /dev/null -w '%{http_code}\n' -X POST \
    -H "Authorization: Bearer $JWT" \
    -H 'Content-Type: application/json' \
    -d '{"sector":"food_hospitality"}' \
    https://smart-investor-api.onrender.com/api/analyze
done
# المتوقع: 5 × 200, ثم 429 لـ 5 المتبقية
```

## المراقبة بعد النشر

- **Render Logs**: راقب الأخطاء في `smart-investor-api` log stream
- **Render Redis Metrics**: تحقق من cmd/sec عادي (<100/sec للحركة الطبيعية)
- **Supabase Dashboard → Logs**: راجع تسجيلات Auth
- **عداد الاستخدام**: راقب فاتورة Perplexity شهرياً (ضع تنبيه عند 50% من الميزانية)

## استكشاف الأخطاء

| العرض | السبب المحتمل | الحل |
|------|--------------|------|
| 401 على كل الطلبات | `SUPABASE_JWT_SECRET` خطأ | انسخه من Supabase Settings → API → JWT Secret |
| CORS error في المتصفح | الـ origin غير مدرج | أضف origin إلى `CORS_ORIGINS` env var |
| Rate limit يخطئ في multi-process | `REDIS_URL` يستخدم `memory://` | تأكد من ربط Redis في Render |
| PII تُحفظ كـ plaintext | `FERNET_KEY` فارغ | اضبطه في env vars |
| 500 على /api/analyze | `PERPLEXITY_API_KEY` غير صالح أو نفد رصيده | تحقق من perplexity.ai/account |
| التحليل يتوقف بعد دقيقة | gunicorn timeout | في `render.yaml`، `--timeout 300` (مضبوط بالفعل) |

## ما بعد الإطلاق (Roadmap)

- مراقبة Sentry أو LogTail للأخطاء
- إضافة Cloudflare Turnstile قبل تشغيل التحليل (إن لاحظت إساءة)
- نقل البيانات من SQLite إلى Postgres (Supabase) عند تجاوز 10K تحليل
- اختبارات تلقائية: pytest + Playwright
- i18n إنجليزي
