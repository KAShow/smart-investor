import json
import logging
import traceback
import sys
from openai import AsyncOpenAI
import openai
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
    'openai': {
        'models': ['gpt-5-mini', 'gpt-5.2', 'gpt-4o', 'gpt-4o-mini'],
        'default': 'gpt-5-mini'
    },
    'gemini': {
        'models': ['gemini-2.5-flash', 'gemini-2.5-pro'],
        'default': 'gemini-2.5-flash'
    }
}


async def create_completion(provider: str, model: str, api_key: str, messages: list, max_tokens: int = 16000, temperature: float = 0.7):
    logger.info(f"═══════════════════════════════════════════")
    logger.info(f"📡 create_completion بدأ | provider={provider} | model={model}")
    logger.info(f"🔑 API Key: {api_key[:8]}...{api_key[-4:]} (length={len(api_key)})")
    logger.info(f"💬 عدد الرسائل: {len(messages)} | max_tokens={max_tokens} | temperature={temperature}")

    if provider == 'gemini':
        logger.info("🟢 استخدام مزود Gemini")
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            gen_model = genai.GenerativeModel(
                model,
                system_instruction=messages[0]['content'] if messages and messages[0]['role'] == 'system' else None,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                    response_mime_type="application/json"
                )
            )
            user_msgs = [m['content'] for m in messages if m['role'] == 'user']
            logger.info(f"📤 إرسال طلب Gemini | model={model}")
            response = await gen_model.generate_content_async(user_msgs[-1] if user_msgs else '')
            logger.info(f"✅ Gemini استجاب بنجاح | طول الاستجابة: {len(response.text)} حرف")
            return response.text
        except Exception as e:
            logger.error(f"❌ خطأ Gemini: {type(e).__name__}: {e}")
            logger.error(f"📋 التتبع الكامل:\n{traceback.format_exc()}")
            raise
    else:
        logger.info("🔵 استخدام مزود OpenAI")
        try:
            client = AsyncOpenAI(api_key=api_key)
            kwargs = dict(
                model=model,
                messages=messages,
                max_completion_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            logger.info(f"📤 إرسال طلب OpenAI | model={model} | kwargs keys: {list(kwargs.keys())}")
            try:
                kwargs['temperature'] = temperature
                response = await client.chat.completions.create(**kwargs)
                logger.info(f"✅ OpenAI استجاب بنجاح")
            except openai.BadRequestError as e:
                logger.warning(f"⚠️ BadRequestError: {e}")
                if 'temperature' in str(e):
                    logger.info("🔄 إعادة المحاولة بدون temperature...")
                    kwargs.pop('temperature', None)
                    response = await client.chat.completions.create(**kwargs)
                    logger.info(f"✅ OpenAI استجاب بنجاح (بدون temperature)")
                else:
                    raise

            message = response.choices[0].message
            logger.info(f"📥 الاستجابة: finish_reason={response.choices[0].finish_reason} | refusal={message.refusal}")
            logger.info(f"📊 الاستخدام: {response.usage}")

            if message.refusal:
                logger.warning(f"🚫 الموديل رفض الطلب: {message.refusal}")
                return json.dumps({"title": "رفض", "summary": message.refusal, "details": [], "score": 0, "recommendation": ""}, ensure_ascii=False)

            content = message.content or ""
            logger.info(f"📄 طول المحتوى: {len(content)} حرف")
            logger.debug(f"📄 أول 200 حرف: {content[:200]}")
            return content

        except Exception as e:
            logger.error(f"❌ خطأ OpenAI: {type(e).__name__}: {e}")
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
