import json
import logging
import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from .base import create_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """أنت محلل استراتيجي متخصص في تحليل SWOT (نقاط القوة، الضعف، الفرص، التهديدات).

مهمتك: بناءً على تحليلات خمسة محللين متخصصين (السوق، المالية، المنافسة، القانون، التقنية)، قم بإنشاء تحليل SWOT شامل ومنظم.

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
  ]
}

- كل قسم يحتوي 3-5 نقاط
- impact يحدد مدى تأثير النقطة (high/medium/low)
- لا تضف أي نص خارج JSON"""


class SwotAgent:
    def __init__(self):
        self.model = "gpt-5-mini"
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
    async def analyze(self, idea: str, all_analyses: dict, api_key: str) -> str:
        user_message = f"""الفكرة الاستثمارية:
{idea}

---

تحليل منطق السوق:
{all_analyses.get('market_analysis', '')}

---

تحليل الاستدامة المالية:
{all_analyses.get('financial_analysis', '')}

---

تحليل المتانة التنافسية:
{all_analyses.get('competitive_analysis', '')}

---

التحليل القانوني:
{all_analyses.get('legal_analysis', '')}

---

التحليل التقني:
{all_analyses.get('technical_analysis', '')}

---

بناءً على جميع التحليلات أعلاه، قدم تحليل SWOT شامل."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]

        content = await create_completion('openai', self.model, api_key, messages, max_tokens=4000)
        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            return json.dumps({"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}, ensure_ascii=False)
