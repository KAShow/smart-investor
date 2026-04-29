"""Follow-up chat service for asking questions about a saved analysis."""
import json
import logging
import traceback

from openai import OpenAI

from agents.base import PROVIDERS
from bahrain_data import BahrainDataService
from config import Config
from utils.sanitize import sanitize_user_input
from web_search import search_web

logger = logging.getLogger(__name__)
_bahrain_service = BahrainDataService()


def _safe_parse_json(json_str, extractor):
    if not json_str:
        return "غير متوفر"
    try:
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
        parts = extractor(data)
        return "\n".join(parts) if parts else str(json_str)[:500]
    except (json.JSONDecodeError, TypeError, AttributeError):
        return str(json_str)[:500]


def _agent_fields(data):
    parts = []
    for key, label in [('title', 'العنوان'), ('summary', 'الملخص')]:
        if data.get(key):
            parts.append(f"{label}: {data[key]}")
    if data.get('score') is not None:
        parts.append(f"التقييم: {data['score']}/10")
    if data.get('details'):
        parts.append("النقاط الرئيسية:")
        for i, d in enumerate(data['details'], 1):
            parts.append(f"  {i}. {d}")
    if data.get('recommendation'):
        parts.append(f"التوصية: {data['recommendation']}")
    return parts


def _brokerage_fields(data):
    parts = []
    for key, label in [('title', 'العنوان'), ('summary', 'الملخص')]:
        if data.get(key):
            parts.append(f"{label}: {data[key]}")
    if data.get('models'):
        parts.append("النماذج:")
        for m in data['models']:
            parts.append(f"  - {m.get('name', '')}: {m.get('score', 0)}/10 (ملاءمة: {m.get('fit_for_bahrain', '')})")
    if data.get('recommended_model'):
        parts.append(f"النموذج الموصى به: {data['recommended_model']}")
    return parts


def _verdict_fields(data):
    parts = []
    for key, label in [('verdict', 'القرار'), ('overall_score', 'التقييم الإجمالي'),
                       ('summary', 'الملخص'), ('score_justification', 'تبرير التقييم'),
                       ('recommended_model', 'النموذج الموصى به'),
                       ('model_justification', 'تبرير النموذج')]:
        if data.get(key) is not None:
            parts.append(f"{label}: {data[key]}")
    for key, label in [('consensus', 'نقاط التوافق'), ('conflicts', 'نقاط الاختلاف'),
                       ('advice', 'النصائح الاستراتيجية')]:
        items = data.get(key, [])
        if items:
            parts.append(f"{label}:")
            for i, item in enumerate(items, 1):
                parts.append(f"  {i}. {item}")
    return parts


def _swot_fields(data):
    parts = []
    for key, label in [('strengths', 'نقاط القوة'), ('weaknesses', 'نقاط الضعف'),
                       ('opportunities', 'الفرص'), ('threats', 'التهديدات')]:
        items = data.get(key, [])
        if items:
            parts.append(f"{label}:")
            for i, item in enumerate(items, 1):
                point = item.get('point', item) if isinstance(item, dict) else item
                parts.append(f"  {i}. {point}")
    return parts


def _action_plan_fields(data):
    parts = []
    if data.get('executive_summary'):
        parts.append(f"الملخص التنفيذي: {data['executive_summary']}")
    if data.get('total_budget'):
        parts.append(f"الميزانية الإجمالية: {data['total_budget']}")
    if data.get('phases'):
        parts.append("المراحل:")
        for phase in data['phases']:
            parts.append(f"  - {phase.get('name', 'مرحلة')} ({phase.get('duration', '')})")
            for task in phase.get('tasks', []):
                parts.append(f"    • {task}")
    for key, label in [('key_metrics', 'مؤشرات الأداء'),
                       ('critical_success_factors', 'عوامل النجاح الحاسمة')]:
        items = data.get(key, [])
        if items:
            parts.append(f"{label}:")
            for i, m in enumerate(items, 1):
                parts.append(f"  {i}. {m}")
    return parts


def _build_context(analysis: dict) -> str:
    sector = analysis.get('sector', 'food_hospitality')
    bahrain_context = _bahrain_service.build_market_context(sector=sector)
    parts = [
        "أنت مستشار متخصص في الوساطة التجارية ومحلل استراتيجي للسوق البحريني. "
        "لديك خبرة عميقة في نماذج الوساطة، المنصات التجارية، والتنظيمات القانونية في مملكة البحرين.",
        bahrain_context,
        "═══ موضوع الدراسة ═══",
        analysis['idea'],
        "═══ تحليل الطلب ═══",
        _safe_parse_json(analysis.get('market_analysis', ''), _agent_fields),
        "═══ التحليل المالي ═══",
        _safe_parse_json(analysis.get('financial_analysis', ''), _agent_fields),
        "═══ تحليل المنافسة ═══",
        _safe_parse_json(analysis.get('competitive_analysis', ''), _agent_fields),
        "═══ التحليل القانوني ═══",
        _safe_parse_json(analysis.get('legal_analysis', ''), _agent_fields),
        "═══ التحليل التقني ═══",
        _safe_parse_json(analysis.get('technical_analysis', ''), _agent_fields),
        "═══ نماذج الوساطة ═══",
        _safe_parse_json(analysis.get('brokerage_models_analysis', ''), _brokerage_fields),
        "═══ تحليل SWOT ═══",
        _safe_parse_json(analysis.get('swot_analysis', ''), _swot_fields),
        "═══ خطة العمل ═══",
        _safe_parse_json(analysis.get('action_plan', ''), _action_plan_fields),
        "═══ الحكم النهائي ═══",
        _safe_parse_json(analysis.get('final_verdict', ''), _verdict_fields),
        "═══ تعليمات الإجابة ═══",
        "1. قدّم إجابات شاملة ومفصلة بالعربية الفصحى مع أرقام من التحليلات.",
        "2. هيكل الإجابة بالعناوين والقوائم.",
        "3. أضف رؤية نقدية وحلولاً عملية - لا تكتفِ بإعادة الكتابة.",
        "4. إن خرج السؤال عن نطاق التحليلات، أشر لذلك بوضوح.",
        "5. عند الاستشهاد بالأرقام، اذكر أن المصدر هو data.gov.bh.",
    ]
    return "\n\n".join(p for p in parts if p)


def ask_followup(*, analysis: dict, question: str, conversation_history: list,
                 web_search_enabled: bool = False, model: str = '') -> dict:
    api_key = Config.PERPLEXITY_API_KEY
    if not api_key:
        return {'error': 'الخادم لم يُهيَّأ بمفتاح Perplexity'}

    question_clean = sanitize_user_input(question, max_len=2000)
    if not question_clean:
        return {'error': 'الرجاء إدخال سؤال'}

    system_content = _build_context(analysis)
    web_search_used = False

    if web_search_enabled:
        idea_short = analysis['idea'][:100]
        try:
            search_results = search_web(f"{question_clean} {idea_short} البحرين", max_results=5)
            if not search_results:
                search_results = search_web(f"{idea_short} البحرين", max_results=5)
            if search_results:
                system_content += f"\n\n═══ نتائج بحث الويب ═══\n{search_results}\n"
                web_search_used = True
        except Exception as e:
            logger.warning(f"web search failed: {e}")

    messages = [{"role": "system", "content": system_content}]
    for msg in (conversation_history or [])[-20:]:
        if msg.get('role') in ('user', 'assistant') and msg.get('content'):
            messages.append({
                "role": msg['role'],
                "content": sanitize_user_input(msg['content'], max_len=2000)
            })
    messages.append({"role": "user", "content": question_clean})

    effective_model = model.strip() if model else Config.PERPLEXITY_DEFAULT_MODEL
    if effective_model not in PROVIDERS['perplexity']['models']:
        effective_model = Config.PERPLEXITY_DEFAULT_MODEL

    try:
        client = OpenAI(api_key=api_key, base_url='https://api.perplexity.ai', timeout=120.0)
        response = client.chat.completions.create(
            model=effective_model, messages=messages, max_tokens=4000, temperature=0.3
        )
        answer = response.choices[0].message.content or "لم أتمكن من الإجابة"
        return {'answer': answer, 'web_search_used': web_search_used}
    except Exception as e:
        logger.error(f"followup failed: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        return {'error': f'حدث خطأ: {type(e).__name__}'}
