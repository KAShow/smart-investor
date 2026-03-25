import asyncio
import json
import logging
import traceback
import sys
from openai import AsyncOpenAI
import openai
import anthropic
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

# إعداد logging شامل مع rotation
from logging.handlers import RotatingFileHandler

_log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
_stream_handler = logging.StreamHandler(sys.stdout)
_stream_handler.setFormatter(_log_formatter)
_handlers = [_stream_handler]
try:
    _file_handler = RotatingFileHandler('debug.log', encoding='utf-8', maxBytes=5*1024*1024, backupCount=3)
    _file_handler.setFormatter(_log_formatter)
    _handlers.append(_file_handler)
except Exception:
    pass  # Render filesystem may not support file logging
logging.basicConfig(
    level=logging.DEBUG,
    handlers=_handlers
)
logger = logging.getLogger(__name__)

PROVIDERS = {
    'perplexity': {
        'models': ['sonar', 'sonar-pro', 'sonar-reasoning', 'sonar-reasoning-pro'],
        'default': 'sonar-pro',
        'base_url': 'https://api.perplexity.ai'
    },
    'openai': {
        'models': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'o1', 'o1-mini'],
        'default': 'gpt-4o-mini',
        'base_url': None
    },
    'anthropic': {
        'models': ['claude-sonnet-4-20250514', 'claude-haiku-4-20250414', 'claude-opus-4-20250514'],
        'default': 'claude-sonnet-4-20250514',
        'base_url': None
    },
    'gemini': {
        'models': ['gemini-2.0-flash', 'gemini-2.5-pro-preview-06-05'],
        'default': 'gemini-2.0-flash',
        'base_url': None
    }
}


import re


def _extract_json(text: str) -> str:
    """Extract JSON from text that may be wrapped in markdown code blocks.
    Skip extraction if content looks like Markdown (starts with [SCORE:)."""
    stripped = text.strip()
    # Don't extract from Markdown responses — return as-is
    if stripped.startswith('[SCORE:'):
        return stripped
    # Try to extract from ```json ... ``` or ``` ... ```
    match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', text)
    if match:
        return match.group(1).strip()
    # Try to find raw JSON object
    match = re.search(r'(\{[\s\S]*\})', text)
    if match:
        return match.group(1).strip()
    return stripped


async def create_completion(provider: str, model: str, api_key: str, messages: list, max_tokens: int = 4000, temperature: float = 0.2):
    logger.info(f"═══════════════════════════════════════════")
    logger.info(f"📡 create_completion بدأ | provider={provider} | model={model}")
    logger.info(f"🔑 API Key: ***{api_key[-4:] if len(api_key) > 4 else '****'}")

    # التأكد من أن المزود معروف، وإلا استخدام perplexity كافتراضي
    if provider not in PROVIDERS:
        logger.warning(f"⚠️ مزود غير معروف '{provider}'، استخدام perplexity")
        provider = 'perplexity'

    provider_config = PROVIDERS[provider]
    effective_model = model if model in provider_config['models'] else provider_config['default']
    logger.info(f"🟢 استخدام مزود {provider} | model={effective_model}")

    try:
        if provider == 'anthropic':
            client = AsyncAnthropic(api_key=api_key, timeout=120.0)
            # استخراج system message من messages
            system_content = ""
            user_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                else:
                    user_messages.append(msg)
            response = await client.messages.create(
                model=effective_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_content,
                messages=user_messages
            )
            content = response.content[0].text or ""
            logger.info(f"✅ {provider} استجاب بنجاح | طول الاستجابة: {len(content)} حرف")
        elif provider == 'gemini':
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            genai_model = genai.GenerativeModel(effective_model)
            # تجميع الرسائل في نص واحد
            prompt_parts = []
            for msg in messages:
                prompt_parts.append(msg["content"])
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: genai_model.generate_content("\n\n".join(prompt_parts))
            )
            content = response.text or ""
            logger.info(f"✅ {provider} استجاب بنجاح | طول الاستجابة: {len(content)} حرف")
        else:
            # OpenAI و Perplexity (كلاهما متوافق مع OpenAI SDK)
            client_kwargs = {"api_key": api_key}
            if provider_config.get('base_url'):
                client_kwargs["base_url"] = provider_config['base_url']
            client = AsyncOpenAI(**client_kwargs, timeout=120.0)
            response = await client.chat.completions.create(
                model=effective_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            content = response.choices[0].message.content or ""
            logger.info(f"✅ {provider} استجاب بنجاح | طول الاستجابة: {len(content)} حرف")
            logger.info(f"📊 الاستخدام: {response.usage}")

        content = _extract_json(content)
        return content

    except Exception as e:
        logger.error(f"❌ خطأ {provider}: {type(e).__name__}: {e}")
        logger.error(f"📋 التتبع الكامل:\n{traceback.format_exc()}")
        raise


class BaseAgent:
    def __init__(self, model: str, system_prompt: str):
        self.model = model
        self.system_prompt = system_prompt

    @retry(
        stop=stop_after_attempt(2),
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

            # Markdown response — return as-is
            if content and '[SCORE:' in content:
                score_match = re.search(r'\[SCORE:\s*(\d+(?:\.\d+)?)', content)
                if score_match:
                    logger.info(f"📊 {agent_name}: score={score_match.group(1)} (markdown)")
                return content

            # JSON response — backwards compatibility
            try:
                parsed = json.loads(content)
                logger.info(f"✅ {agent_name}: JSON صالح | مفاتيح: {list(parsed.keys()) if isinstance(parsed, dict) else 'ليس dict'}")
                if isinstance(parsed, dict) and 'score' in parsed:
                    logger.info(f"📊 {agent_name}: score={parsed['score']}")
                return content
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ {agent_name}: JSON غير صالح: {e}")
                logger.warning(f"⚠️ المحتوى الخام: {content[:300]}")
                # Return raw content as-is — frontend will render as markdown fallback
                return content

        except Exception as e:
            logger.error(f"❌ {agent_name}: فشل التحليل: {type(e).__name__}: {e}")
            logger.error(f"📋 التتبع الكامل:\n{traceback.format_exc()}")
            raise
