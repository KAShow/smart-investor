import json
import logging
import openai
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from .base import create_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """أنت محلل استراتيجي متخصص في تحليل SWOT (نقاط القوة، الضعف، الفرص، التهديدات).

مهمتك: بناءً على تحليلات ستة محللين متخصصين (الطلب على الوساطة، الجدوى المالية للوساطة، المنافسة في الوساطة، قانون الوساطة، الجدوى التقنية، نماذج الوساطة)، قم بإنشاء تحليل SWOT شامل ومنظم لمشروع الوساطة التجارية في القطاع المحدد.

** مهم جداً: يجب أن ترد بصيغة JSON فقط بالهيكل التالي **
{
  "strengths": [
    {"point": "نقطة قوة", "impact": "high/medium/low"}
  ],
  "weaknesses": [
    {"point": "نقطة ضعف", "impact": "high/medium/low"}
  ],
  "opportunities": [
    {"point": "فرصة", "impact": "high/medium/low"}
  ],
  "threats": [
    {"point": "تهديد", "impact": "high/medium/low"}
  ],
  "swot_summary": [
    "أبرز قوة يمكن استغلالها فوراً: ...",
    "أخطر ضعف يجب معالجته قبل البدء: ...",
    "أكبر فرصة في السوق الآن: ...",
    "أخطر تهديد يجب الاستعداد له: ...",
    "القرار المصيري: ... (الشي اللي لو ما انسوى، المشروع بيفشل)"
  ]
}

- كل قسم (strengths/weaknesses/opportunities/threats) يحتوي 3-5 نقاط
- impact يحدد مدى تأثير النقطة (high/medium/low)
- swot_summary يحتوي 3-5 نقاط مباشرة — هذه "الزبدة" التي يحتاجها صانع القرار
- لا تضف أي نص خارج JSON"""


class SwotAgent:
    def __init__(self):
        self.model = "sonar-pro"
        self.system_prompt = SYSTEM_PROMPT

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            openai.APITimeoutError,
            openai.RateLimitError,
            openai.APIConnectionError,
            anthropic.APITimeoutError,
            anthropic.RateLimitError,
            anthropic.APIConnectionError,
            anthropic.InternalServerError,
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def analyze(self, idea: str, all_analyses: dict, api_key: str, provider: str = 'openai', model_override: str = None) -> str:
        user_message = f"""دراسة جدوى الوساطة التجارية:
{idea}

---

تحليل الطلب على الوساطة:
{all_analyses.get('market_analysis', '')}

---

تحليل الجدوى المالية للوساطة:
{all_analyses.get('financial_analysis', '')}

---

تحليل المنافسة في الوساطة:
{all_analyses.get('competitive_analysis', '')}

---

التحليل القانوني للوساطة:
{all_analyses.get('legal_analysis', '')}

---

التحليل التقني للمنصة:
{all_analyses.get('technical_analysis', '')}

---

تحليل نماذج الوساطة:
{all_analyses.get('brokerage_models_analysis', '')}

---

بناءً على جميع التحليلات أعلاه، قدم تحليل SWOT شامل لمشروع الوساطة التجارية."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]

        model = model_override or self.model
        content = await create_completion(provider, model, api_key, messages, max_tokens=4000)
        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            return json.dumps({"strengths": [], "weaknesses": [], "opportunities": [], "threats": [], "swot_summary": []}, ensure_ascii=False)

    def analyze_sync(self, idea, all_analyses, api_key, provider='openai', model_override=None):
        """Synchronous SWOT — works reliably with gunicorn."""
        from .base import create_completion_sync
        user_message = f"""دراسة جدوى الوساطة التجارية:
{idea}

---

تحليل الطلب على الوساطة:
{all_analyses.get('market_analysis', '')}

---

تحليل الجدوى المالية للوساطة:
{all_analyses.get('financial_analysis', '')}

---

تحليل المنافسة في الوساطة:
{all_analyses.get('competitive_analysis', '')}

---

التحليل القانوني للوساطة:
{all_analyses.get('legal_analysis', '')}

---

التحليل التقني للمنصة:
{all_analyses.get('technical_analysis', '')}

---

تحليل نماذج الوساطة:
{all_analyses.get('brokerage_models_analysis', '')}

---

بناءً على جميع التحليلات أعلاه، قدم تحليل SWOT شامل لمشروع الوساطة التجارية."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]

        model = model_override or self.model
        content = create_completion_sync(provider, model, api_key, messages, max_tokens=4000)
        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            return json.dumps({"strengths": [], "weaknesses": [], "opportunities": [], "threats": [], "swot_summary": []}, ensure_ascii=False)
