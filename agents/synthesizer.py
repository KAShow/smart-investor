import json
import logging
from openai import AsyncOpenAI
import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from .base import create_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """أنت الشريك العام وصانع القرار الاستثماري النهائي.

دورك: استلام تحليلات خمسة محللين متخصصين (منطق السوق، الاستدامة المالية، المتانة التنافسية، القانون والتنظيم، الجدوى التقنية) ودمجها في حكم نهائي شامل.

عند اتخاذ القرار:
1. وازن بين الحجج المتناقضة من المحللين الخمسة
2. حدد أوجه التوافق والاختلاف بين التحليلات
3. قيّم المخاطر الإجمالية مقابل الفرص
4. أصدر حكماً استثمارياً واضحاً

** مهم جداً: يجب أن ترد بصيغة JSON فقط بالهيكل التالي **
{
  "summary": "ملخص شامل لجميع التحليلات في فقرة أو فقرتين",
  "consensus": ["نقطة توافق 1", "نقطة توافق 2", "..."],
  "conflicts": ["نقطة اختلاف 1", "نقطة اختلاف 2", "..."],
  "verdict": "استثمر بقوة | استثمر بحذر | راقب وانتظر | لا تستثمر",
  "overall_score": "<رقم 1-10 بناءً على المعيار أدناه>",
  "score_justification": "تبرير التقييم",
  "advice": ["نصيحة عملية 1", "نصيحة عملية 2", "نصيحة 3", "..."]
}

** معيار التسجيل النهائي (overall_score) - استخدم النطاق الكامل من 1 إلى 10: **
- 9-10: استثمر بقوة — فكرة ممتازة من جميع الجوانب، فرصة نادرة، مخاطر منخفضة
- 7-8: استثمر بحذر — فكرة جيدة مع بعض التحفظات، تحتاج تنفيذ منضبط
- 5-6: راقب وانتظر — فكرة متوسطة، تحتاج تعديلات جوهرية أو توقيت أفضل
- 3-4: لا تستثمر غالباً — مخاطر تفوق الفرص، يحتاج pivot كبير
- 1-2: لا تستثمر أبداً — فكرة فاشلة من الأساس

مهم: لا تتردد في إعطاء 9 أو 10 للأفكار الممتازة فعلاً. ولا تتردد في إعطاء 2 أو 3 للأفكار الضعيفة. كن صادقاً ودقيقاً ولا تميل للوسط دائماً. الـ verdict يجب أن يتوافق مع الـ score (9-10 = "استثمر بقوة"، 7-8 = "استثمر بحذر"، 5-6 = "راقب وانتظر"، 1-4 = "لا تستثمر").
- verdict يجب أن يكون واحداً من: "استثمر بقوة" أو "استثمر بحذر" أو "راقب وانتظر" أو "لا تستثمر"
- consensus و conflicts و advice كل منها 2-5 نقاط
- عند الإشارة إلى أي بيانات أو إحصائيات من السوق البحريني في الملخص أو النصائح، اذكر أن المصدر هو "بوابة البيانات المفتوحة البحرينية (data.gov.bh)"
- لا تضف أي نص خارج JSON"""


class SynthesizerAgent:
    def __init__(self):
        self.model = "gpt-5.2"
        self.system_prompt = SYSTEM_PROMPT

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            openai.APITimeoutError,
            openai.RateLimitError,
            openai.APIConnectionError,
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def synthesize(
        self,
        idea: str,
        market_analysis: str,
        financial_analysis: str,
        competitive_analysis: str,
        api_key: str,
        legal_analysis: str = '',
        technical_analysis: str = '',
        provider: str = 'openai',
        model_override: str = None
    ) -> str:
        model = model_override or self.model

        user_message = f"""الفكرة الاستثمارية:
{idea}

---

تحليل منطق السوق:
{market_analysis}

---

تحليل الاستدامة المالية:
{financial_analysis}

---

تحليل المتانة التنافسية:
{competitive_analysis}

---

التحليل القانوني والتنظيمي:
{legal_analysis or 'غير متوفر'}

---

تحليل الجدوى التقنية:
{technical_analysis or 'غير متوفر'}

---

بناءً على التحليلات الخمسة أعلاه، قدم حكمك الاستثماري النهائي والاستشارة الاستراتيجية."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]

        content = await create_completion(provider, model, api_key, messages, max_tokens=3000, temperature=0.5)

        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            return json.dumps({"summary": content, "consensus": [], "conflicts": [], "verdict": "راقب وانتظر", "overall_score": 0, "score_justification": "", "advice": []}, ensure_ascii=False)
