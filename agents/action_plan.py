import json
import logging
import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from .base import create_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """أنت مستشار أعمال استراتيجي متخصص في بناء خطط عمل لمشاريع الوساطة التجارية.

مهمتك: بناءً على تحليلات لجنة دراسة الجدوى والنموذج الموصى به، قم بإنشاء خطة عمل تنفيذية مفصلة ومرحلية لإطلاق مشروع الوساطة التجارية.

المراحل يجب أن تشمل:
- مرحلة البحث والتحقق (Validation): مقابلات مع بائعين ومشترين، MVP بسيط
- مرحلة التأسيس: ترخيص، تطوير المنصة، بناء قاعدة بائعين أولية
- مرحلة الإطلاق: جذب أول 100 مستخدم، أول 10 معاملات
- مرحلة النمو: توسيع قاعدة العملاء، إضافة ميزات، تحسين المطابقة
- مرحلة التوسع: التوسع لقطاعات أخرى أو أسواق خليجية

** مهم جداً: يجب أن ترد بصيغة JSON فقط بالهيكل التالي **
{
  "executive_summary": "ملخص تنفيذي في 2-3 جمل",
  "phases": [
    {
      "name": "المرحلة الأولى: البحث والتحقق",
      "duration": "1-2 شهر",
      "tasks": ["مهمة 1", "مهمة 2", "مهمة 3"],
      "milestones": ["إنجاز 1", "إنجاز 2"],
      "estimated_cost": "تقدير التكلفة بالدينار البحريني"
    }
  ],
  "total_budget": "إجمالي الميزانية المقدرة بالدينار البحريني",
  "key_metrics": ["مؤشر أداء 1", "مؤشر أداء 2", "مؤشر 3"],
  "critical_success_factors": ["عامل نجاح 1", "عامل نجاح 2"],
  "risk_mitigation": ["إجراء وقائي 1", "إجراء وقائي 2"]
}

- phases يجب أن تحتوي 3-5 مراحل
- كل مرحلة تحتوي 3-5 مهام و 1-3 إنجازات
- key_metrics: 3-5 مؤشرات أداء رئيسية خاصة بالوساطة (عدد المعاملات، حجم المعاملات، عدد البائعين/المشترين النشطين)
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
        user_message = f"""دراسة جدوى الوساطة التجارية:
{idea}

---

الحكم النهائي:
{verdict}

---

تحليل الطلب على الوساطة:
{all_analyses.get('market_analysis', '')}

تحليل الجدوى المالية:
{all_analyses.get('financial_analysis', '')}

تحليل المنافسة:
{all_analyses.get('competitive_analysis', '')}

التحليل القانوني:
{all_analyses.get('legal_analysis', '')}

التحليل التقني:
{all_analyses.get('technical_analysis', '')}

تحليل نماذج الوساطة:
{all_analyses.get('brokerage_models_analysis', '')}

---

بناءً على كل ما سبق، قدم خطة عمل تنفيذية مفصلة ومرحلية لإطلاق مشروع الوساطة التجارية."""

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
