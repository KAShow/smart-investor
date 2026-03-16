import json
import logging
import traceback
import sys
from openai import AsyncOpenAI
import openai
import anthropic
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

# إعداد logging شامل
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

PROVIDERS = {
    'perplexity': {
        'models': ['sonar', 'sonar-pro', 'sonar-reasoning', 'sonar-reasoning-pro'],
        'default': 'sonar-pro'
    }
}


import re


def _extract_json(text: str) -> str:
    """Extract JSON from text that may be wrapped in markdown code blocks."""
    # Try to extract from ```json ... ``` or ``` ... ```
    match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', text)
    if match:
        return match.group(1).strip()
    # Try to find raw JSON object
    match = re.search(r'(\{[\s\S]*\})', text)
    if match:
        return match.group(1).strip()
    return text.strip()


async def create_completion(provider: str, model: str, api_key: str, messages: list, max_tokens: int = 4000, temperature: float = 0.2):
    logger.info(f"═══════════════════════════════════════════")
    logger.info(f"📡 create_completion بدأ | provider={provider} | model={model}")
    logger.info(f"🔑 API Key: {api_key[:8]}...{api_key[-4:]}")
    
    # تحويل المزود إلى perplexity دائماً حسب طلب المستخدم
    provider = 'perplexity'
    
    logger.info("🟢 استخدام مزود Perplexity (متوافق مع OpenAI API)")
    try:
        # Perplexity API is compatible with OpenAI SDK
        client = AsyncOpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
        kwargs = dict(
            model=model if model in PROVIDERS['perplexity']['models'] else PROVIDERS['perplexity']['default'],
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        logger.info(f"📤 إرسال طلب Perplexity | model={kwargs['model']}")
        response = await client.chat.completions.create(**kwargs)
        
        message = response.choices[0].message
        content = message.content or ""
        
        logger.info(f"✅ Perplexity استجاب بنجاح | طول الاستجابة: {len(content)} حرف")
        logger.info(f"📊 الاستخدام: {response.usage}")
        
        content = _extract_json(content)
        return content

    except Exception as e:
        logger.error(f"❌ خطأ Perplexity: {type(e).__name__}: {e}")
        logger.error(f"📋 التتبع الكامل:\n{traceback.format_exc()}")
        raise


class BaseAgent:
    def __init__(self, model: str, system_prompt: str):
        self.model = model
        self.system_prompt = system_prompt

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            openai.APITimeoutError,
            openai.RateLimitError,
            openai.APIConnectionError,
            openai.InternalServerError,
            anthropic.APITimeoutError,
            anthropic.RateLimitError,
            anthropic.APIConnectionError,
            anthropic.InternalServerError,
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def analyze(self, idea: str, api_key: str, provider: str = 'openai', model_override: str = None, market_context: str = '') -> str:
        model = model_override or self.model
        agent_name = self.__class__.__name__
        logger.info(f"")
        logger.info(f"🤖 ══════ {agent_name}.analyze بدأ ══════")
        logger.info(f"🤖 الوكيل: {agent_name} | model={model} | provider={provider}")
        logger.info(f"💡 طول الفكرة: {len(idea)} حرف | سياق السوق: {len(market_context)} حرف")

        user_content = idea
        if market_context:
            user_content = f"{idea}\n\n{market_context}"

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            content = await create_completion(provider, model, api_key, messages)
            logger.info(f"✅ {agent_name}: استلم محتوى | طول={len(content) if content else 0}")

            try:
                parsed = json.loads(content)
                logger.info(f"✅ {agent_name}: JSON صالح | مفاتيح: {list(parsed.keys()) if isinstance(parsed, dict) else 'ليس dict'}")
                if isinstance(parsed, dict) and 'score' in parsed:
                    logger.info(f"📊 {agent_name}: score={parsed['score']}")
                return content
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ {agent_name}: JSON غير صالح: {e}")
                logger.warning(f"⚠️ المحتوى الخام: {content[:300]}")
                return json.dumps({"title": "تحليل", "summary": content, "details": [], "score": 0, "recommendation": ""}, ensure_ascii=False)

        except Exception as e:
            logger.error(f"❌ {agent_name}: فشل التحليل: {type(e).__name__}: {e}")
            logger.error(f"📋 التتبع الكامل:\n{traceback.format_exc()}")
            raise
