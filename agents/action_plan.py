import json
import logging
import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from .base import create_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """أنت مستشار أعمال استراتيجي متخصص في بناء خطط العمل التنفيذية.

مهمتك: بناءً على تحليلات لجنة الاستثمار والحكم النهائي، قم بإنشاء خطة عمل تنفيذية مفصلة ومرحلية.

** مهم جداً: يجب أن ترد بصيغة JSON فقط بالهيكل التالي **
{
  "executive_summary": "ملخص تنفيذي في 2-3 جمل",
  "phases": [
    {
      "name": "المرحلة الأولى: التأسيس",
      "duration": "1-3 أشهر",
      "tasks": ["مهمة 1", "مهمة 2", "مهمة 3"],
      "milestones": ["إنجاز 1", "إنجاز 2"],
      "estimated_cost": "تقدير التكلفة"
    }
  ],
  "total_budget": "إجمالي الميزانية المقدرة",
  "key_metrics": ["مؤشر أداء 1", "مؤشر أداء 2", "مؤشر 3"],
  "critical_success_factors": ["عامل نجاح 1", "عامل نجاح 2"],
  "risk_mitigation": ["إجراء وقائي 1", "إجراء وقائي 2"]
}

- phases يجب أن تحتوي 3-5 مراحل
- كل مرحلة تحتوي 3-5 مهام و 1-3 إنجازات
- key_metrics: 3-5 مؤشرات أداء رئيسية
- لا تضف أي نص خارج JSON"""


class ActionPlanAgent:
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
    async def generate(self, idea: str, all_analyses: dict, verdict: str, api_key: str) -> str:
        user_message = f"""الفكرة الاستثمارية:
{idea}

---

الحكم الاستثماري النهائي:
{verdict}

---

تحليل السوق:
{all_analyses.get('market_analysis', '')}

تحليل مالي:
{all_analyses.get('financial_analysis', '')}

تحليل تنافسي:
{all_analyses.get('competitive_analysis', '')}

تحليل قانوني:
{all_analyses.get('legal_analysis', '')}

تحليل تقني:
{all_analyses.get('technical_analysis', '')}

---

بناءً على كل ما سبق، قدم خطة عمل تنفيذية مفصلة ومرحلية لتنفيذ هذا المشروع."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]

        content = await create_completion('openai', self.model, api_key, messages, max_tokens=6000)
        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            return json.dumps({
                "executive_summary": content,
                "phases": [],
                "total_budget": "غير محدد",
                "key_metrics": [],
                "critical_success_factors": [],
                "risk_mitigation": []
            }, ensure_ascii=False)
