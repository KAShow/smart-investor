import json
import logging
from openai import AsyncOpenAI
import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from .base import create_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """أنت صانع القرار النهائي في لجنة دراسة جدوى الوساطة التجارية.

دورك: استلام تحليلات ستة محللين متخصصين (الطلب على الوساطة، الجدوى المالية للوساطة، المنافسة في الوساطة، قانون الوساطة، الجدوى التقنية، نماذج الوساطة) ودمجها في حكم نهائي شامل حول جدوى إنشاء شركة وساطة تجارية في القطاع المحدد.

عند اتخاذ القرار:
1. وازن بين الحجج المتناقضة من المحللين الستة
2. حدد أوجه التوافق والاختلاف بين التحليلات
3. قيّم المخاطر الإجمالية مقابل الفرص
4. أصدر حكماً واضحاً حول جدوى الوساطة في هذا القطاع
5. حدد النموذج الأمثل للوساطة بناءً على تحليل نماذج الوساطة

** مهم جداً: يجب أن ترد بصيغة JSON فقط بالهيكل التالي **
{
  "summary": "ملخص شامل لجميع التحليلات في فقرة أو فقرتين",
  "consensus": ["نقطة توافق 1", "نقطة توافق 2", "..."],
  "conflicts": ["نقطة اختلاف 1", "نقطة اختلاف 2", "..."],
  "verdict": "قطاع مثالي للوساطة | فرصة واعدة | تحتاج دراسة أعمق | غير مناسب للوساطة",
  "overall_score": 7,
  "score_justification": "تبرير التقييم",
  "recommended_model": "اسم نموذج الوساطة الموصى به",
  "model_justification": "لماذا هذا النموذج هو الأنسب لهذا القطاع",
  "advice": ["نصيحة عملية 1", "نصيحة عملية 2", "نصيحة 3", "..."]
}

** معيار التسجيل النهائي (overall_score) - استخدم النطاق الكامل من 1 إلى 10: **
- 9-10: قطاع مثالي للوساطة — فجوة واضحة، طلب مرتفع، ربحية ممتازة، بيئة قانونية سهلة
- 7-8: فرصة واعدة — فرصة جيدة مع بعض التحديات، تحتاج تنفيذ منضبط
- 5-6: تحتاج دراسة أعمق — فرصة متوسطة، تحديات جوهرية تحتاج حلول
- 3-4: غير مناسب غالباً — مخاطر تفوق الفرص، يحتاج pivot كبير
- 1-2: غير مناسب للوساطة أبداً — لا جدوى من الوساطة في هذا القطاع

مهم: لا تتردد في إعطاء 9 أو 10 للقطاعات المثالية فعلاً. ولا تتردد في إعطاء 2 أو 3 للقطاعات غير المناسبة. كن صادقاً ودقيقاً ولا تميل للوسط دائماً. الـ verdict يجب أن يتوافق مع الـ score (9-10 = "قطاع مثالي للوساطة"، 7-8 = "فرصة واعدة"، 5-6 = "تحتاج دراسة أعمق"، 1-4 = "غير مناسب للوساطة").
- verdict يجب أن يكون واحداً من: "قطاع مثالي للوساطة" أو "فرصة واعدة" أو "تحتاج دراسة أعمق" أو "غير مناسب للوساطة"
- consensus و conflicts و advice كل منها 2-5 نقاط
- عند الإشارة إلى أي بيانات أو إحصائيات من السوق البحريني، اذكر أن المصدر هو "بوابة البيانات المفتوحة البحرينية (data.gov.bh)"
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
        brokerage_models_analysis: str = '',
        provider: str = 'openai',
        model_override: str = None
    ) -> str:
        model = model_override or self.model

        user_message = f"""دراسة جدوى الوساطة التجارية:
{idea}

---

تحليل الطلب على الوساطة:
{market_analysis}

---

تحليل الجدوى المالية للوساطة:
{financial_analysis}

---

تحليل المنافسة في الوساطة:
{competitive_analysis}

---

التحليل القانوني للوساطة:
{legal_analysis or 'غير متوفر'}

---

تحليل الجدوى التقنية للمنصة:
{technical_analysis or 'غير متوفر'}

---

تحليل نماذج الوساطة:
{brokerage_models_analysis or 'غير متوفر'}

---

بناءً على التحليلات الستة أعلاه، قدم حكمك النهائي حول جدوى الوساطة التجارية في هذا القطاع، مع تحديد النموذج الأمثل."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]

        content = await create_completion(provider, model, api_key, messages, max_tokens=3000, temperature=0.5)

        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            return json.dumps({"summary": content, "consensus": [], "conflicts": [], "verdict": "تحتاج دراسة أعمق", "overall_score": 0, "score_justification": "", "recommended_model": "", "model_justification": "", "advice": []}, ensure_ascii=False)
