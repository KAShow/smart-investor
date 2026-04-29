# Lovable.dev Frontend Files — Smart Investor Tool

ملفات React/Vite/TypeScript جاهزة للنسخ إلى مشروعك على Lovable.dev (`hawsh-khalifa.lovable.app`) لإضافة أداة "المستثمر الذكي".

## افتراضات

مشروع Lovable.dev قياسي يستخدم:
- React 18 + Vite + TypeScript
- Tailwind CSS + shadcn/ui (`@/components/ui/*`)
- Supabase Auth (`@supabase/supabase-js` + helper hook)
- React Router

إذا كان مشروعك يستخدم بنية مختلفة (مثل Next.js)، عدّل المسارات و الـ imports قليلاً.

## خطوات الدمج

### 1. متغيرات البيئة (Lovable → Project Settings → Environment)

```
VITE_SMART_INVESTOR_API=https://smart-investor-api.onrender.com
```

(`VITE_SUPABASE_URL` و `VITE_SUPABASE_ANON_KEY` يجب أن تكون موجودة بالفعل.)

### 2. الحزم الإضافية المطلوبة

من Lovable IDE → "Install package":

```
react-markdown
rehype-sanitize
zod
react-hook-form
@hookform/resolvers
```

(أغلب projects Lovable عندها `lucide-react`, `react-router-dom`, `@supabase/supabase-js`, و shadcn جاهزين بالفعل.)

### 3. النسخ

اسحب الملفات من هذا المجلد إلى مشروع Lovable بنفس البنية:

```
src/
├── lib/smart-investor/
│   ├── api.ts
│   ├── constants.ts
│   ├── types.ts
│   └── use-analysis-stream.ts
├── components/smart-investor/
│   ├── SectorPicker.tsx
│   ├── IdeaForm.tsx
│   ├── AnalysisStream.tsx
│   ├── AgentReport.tsx
│   └── AnalysesList.tsx
└── pages/
    └── SmartInvestor.tsx
```

### 4. تسجيل المسار

في `src/App.tsx` (أو حيث تُعرّف routes):

```tsx
import SmartInvestor from '@/pages/SmartInvestor';
import { Route } from 'react-router-dom';

// داخل <Routes>:
<Route path="/tools/smart-investor" element={<SmartInvestor />} />
```

`SmartInvestor.tsx` يستخدم `useSession()` من Supabase ويعيد التوجيه لصفحة `/auth` إذا لم يكن المستخدم مسجلاً. عدّل اسم المسار ليطابق صفحة auth في مشروعك.

### 5. إضافة الأداة في صفحة `/learn` أو `/tools`

```tsx
<Link to="/tools/smart-investor" className="...">
  <Card>
    <CardHeader>
      <LineChart className="text-primary" />
      <CardTitle>المستثمر الذكي البحريني</CardTitle>
    </CardHeader>
    <CardContent>
      دراسة جدوى احترافية لمشاريع الوساطة التجارية في البحرين بالذكاء الاصطناعي.
    </CardContent>
  </Card>
</Link>
```

## ملاحظات تقنية مهمة

- **SSE Streaming**: نستخدم `fetch + ReadableStream` بدلاً من `EventSource` لأنّ EventSource لا يدعم `Authorization: Bearer` headers. هذا مدعوم في كل المتصفحات الحديثة.
- **Markdown آمن**: `react-markdown` + `rehype-sanitize` لتجنب XSS من محتوى الـ AI.
- **RTL**: المكوّنات تستخدم `dir="rtl"` على المستوى العالي. تأكد أن مشروع Lovable يحمّل خط `Tajawal` أو `Cairo` للعربية.
- **Auth**: نمرر `session.access_token` كـ Bearer للـ Flask API. Supabase JWT يُتحقق منه على الخادم.
