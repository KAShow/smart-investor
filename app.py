import asyncio
import json
import logging
import os
import queue
import threading
import traceback
import uuid
import webbrowser
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response, send_file
from dotenv import load_dotenv
from tenacity import RetryError
from agents import (MarketLogicAgent, FinancialAgent, CompetitiveAgent,
                    LegalAgent, TechnicalAgent, BrokerageModelsAgent,
                    SynthesizerAgent, SwotAgent, ActionPlanAgent)
from database import (init_db, save_analysis, get_all_analyses, get_analysis,
                      delete_analysis, get_analysis_by_token, rate_analysis, get_dashboard_stats,
                      get_bahrain_data_status)
from bahrain_data import BahrainDataService, SECTORS
from data_sources import DataAggregator
from data_sources.sijilat import SijilatSource
from agents.competitor_enrichment import CompetitorEnrichment
from web_search import search_web

logger = logging.getLogger(__name__)

ENV_PATH = Path(__file__).parent / '.env'
load_dotenv(ENV_PATH)

app = Flask(__name__)

market_agent = MarketLogicAgent()
financial_agent = FinancialAgent()
competitive_agent = CompetitiveAgent()
legal_agent = LegalAgent()
technical_agent = TechnicalAgent()
brokerage_models_agent = BrokerageModelsAgent()
synthesizer = SynthesizerAgent()
swot_agent = SwotAgent()
action_plan_agent = ActionPlanAgent()
bahrain_service = BahrainDataService()
data_aggregator = DataAggregator()

# تهيئة قاعدة البيانات
init_db()

# Pending analysis params store (token → params dict, auto-expires on use)
_pending_analyses = {}


DEFAULT_MODELS = {
    'openai': 'gpt-5.2',
    'gemini': 'gemini-2.5-flash',
    'anthropic': 'claude-sonnet-4-20250514',
}


def get_default_model(provider: str) -> str:
    return DEFAULT_MODELS.get(provider, 'gpt-5.2')


def validate_input(sector, api_key):
    """التحقق من صحة المدخلات وإرجاع رسالة خطأ أو None"""
    if not api_key:
        return 'الرجاء إدخال مفتاح API'
    if not sector or sector not in SECTORS:
        return 'الرجاء اختيار قطاع صالح لدراسة الوساطة'
    return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/shared/<token>')
def shared_view(token):
    analysis = get_analysis_by_token(token)
    if not analysis:
        return render_template('index.html'), 404
    return render_template('shared.html', analysis=analysis)


@app.route('/api/prepare-analysis', methods=['POST'])
def prepare_analysis():
    """Store analysis params server-side and return a short token for SSE."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'طلب غير صالح'}), 400
    token = uuid.uuid4().hex[:16]
    _pending_analyses[token] = data
    return jsonify({'token': token})


@app.route('/analyze-stream')
def analyze_stream():
    # Support both: token-based (new) and direct query params (legacy)
    token = request.args.get('token', '').strip()
    if token and token in _pending_analyses:
        params = _pending_analyses.pop(token)
        sector = params.get('sector', '').strip()
        provider = params.get('provider', 'openai').strip()
        model = params.get('model', '').strip() or get_default_model(provider)
        synthesizer_provider = params.get('synthesizer_provider', '').strip() or provider
        synthesizer_model = params.get('synthesizer_model', '').strip() or get_default_model(synthesizer_provider)
        budget = params.get('budget', '').strip()
        notes = params.get('notes', '').strip()
        requester_name = params.get('requester_name', '').strip()
        requester_email = params.get('requester_email', '').strip()
        requester_company = params.get('requester_company', '').strip()
        api_key = params.get('api_key', '').strip()
    else:
        sector = request.args.get('sector', '').strip()
        provider = request.args.get('provider', 'openai').strip()
        model = request.args.get('model', '').strip() or get_default_model(provider)
        synthesizer_provider = request.args.get('synthesizer_provider', '').strip() or provider
        synthesizer_model = request.args.get('synthesizer_model', '').strip() or get_default_model(synthesizer_provider)
        budget = request.args.get('budget', '').strip()
        notes = request.args.get('notes', '').strip()
        requester_name = request.args.get('requester_name', '').strip()
        requester_email = request.args.get('requester_email', '').strip()
        requester_company = request.args.get('requester_company', '').strip()
        api_key = request.args.get('api_key', '').strip()

    # تحديد مفتاح API حسب المزود
    if not api_key:
        if provider == 'anthropic':
            api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        elif provider == 'gemini':
            api_key = os.environ.get('GEMINI_API_KEY', '')
        else:
            api_key = os.environ.get('OPENAI_API_KEY', '')

    error = validate_input(sector, api_key)
    if error:
        return jsonify({'error': error}), 400

    # توليد نص الدراسة تلقائياً بناءً على القطاع
    sector_name = SECTORS[sector]['name_ar']
    idea = f"دراسة جدوى إنشاء شركة وساطة تجارية في قطاع {sector_name} في مملكة البحرين"
    if notes:
        idea += f"\n\nملاحظات إضافية: {notes}"

    def generate():
        event_queue = queue.Queue()

        # جلب بيانات السوق البحريني حسب القطاع المختار
        market_context = bahrain_service.build_market_context(sector=sector)

        # إضافة قيد رأس المال إن وُجد
        if budget:
            try:
                budget_int = int(budget)
                budget_formatted = f"{budget_int:,}"
                market_context += f"""

══ قيد رأس المال ══
** المستثمر يملك أقل من {budget_formatted} دينار بحريني **
- يجب أن يلتزم تحليلك بهذه الميزانية المحددة ({budget_formatted} د.ب)
- لا تقترح أي خطوة أو استثمار يتطلب رأس مال أعلى من {budget_formatted} د.ب
- قيّم جدوى الوساطة من منظور هذه الميزانية: هل هي كافية؟ هل تحتاج تعديل؟
- إذا كانت الميزانية غير كافية لنموذج وساطة معين، وضّح ذلك بصراحة واقترح بديلاً أصغر
- اذكر تكاليف تقديرية واقعية بالدينار البحريني ضمن حدود الميزانية"""
            except ValueError:
                pass

        async def run_agents():
            async def run_agent(name, coro):
                try:
                    logger.info(f"🚀 بدء وكيل: {name}")
                    result = await coro
                    logger.info(f"✅ وكيل {name} انتهى بنجاح | طول النتيجة: {len(result) if result else 0}")
                    event_queue.put((name, result))
                except RetryError as e:
                    last_err = e.last_attempt.exception() if e.last_attempt else e
                    err_type = type(last_err).__name__
                    err_msg = str(last_err)
                    logger.error(f"❌❌ وكيل {name} فشل بعد 3 محاولات!")
                    logger.error(f"❌ نوع الخطأ الأصلي: {err_type}")
                    logger.error(f"❌ رسالة الخطأ: {err_msg}")
                    logger.error(f"❌ التتبع الكامل:\n{traceback.format_exc()}")
                    event_queue.put((name, json.dumps({"title": "خطأ", "summary": f"{err_type}: {err_msg}", "details": [f"فشل بعد 3 محاولات", f"نوع الخطأ: {err_type}"], "score": 0, "recommendation": ""}, ensure_ascii=False)))
                except Exception as e:
                    err_type = type(e).__name__
                    err_msg = str(e)
                    logger.error(f"❌ وكيل {name} فشل: {err_type}: {err_msg}")
                    logger.error(f"❌ التتبع:\n{traceback.format_exc()}")
                    event_queue.put((name, json.dumps({"title": "خطأ", "summary": f"{err_type}: {err_msg}", "details": [], "score": 0, "recommendation": ""}, ensure_ascii=False)))

            # جلب بيانات إضافية من مصادر متعددة
            try:
                aggregated = await data_aggregator.fetch_all(sector)
            except Exception as e:
                logger.warning(f"⚠️ فشل جلب البيانات الإضافية: {e}")
                aggregated = {}

            # جلب وإثراء بيانات المنافسين
            sijilat_source = SijilatSource()
            competitors_raw = sijilat_source.get_competitors(sector)
            competitors_enriched = competitors_raw  # default: no enrichment
            try:
                enrichment = CompetitorEnrichment()
                competitors_enriched = enrichment.enrich_batch(competitors_raw, sector, max_enrich=8)
                logger.info(f"✅ تم إثراء {len(competitors_enriched)} منافس لقطاع '{sector}'")
            except Exception as e:
                logger.warning(f"⚠️ فشل إثراء المنافسين: {e}")

            # إرسال بيانات المنافسين للواجهة
            event_queue.put(("competitors_found", json.dumps({
                "count": len(competitors_enriched),
                "competitors": competitors_enriched,
            }, ensure_ascii=False)))

            # بناء سياق مخصص لكل وكيل
            market_ctx = market_context + data_aggregator.build_agent_context(sector, "market", aggregated)
            financial_ctx = market_context + data_aggregator.build_agent_context(sector, "financial", aggregated)
            competitive_ctx = market_context + data_aggregator.build_agent_context(sector, "competitive", aggregated)
            legal_ctx = market_context + data_aggregator.build_agent_context(sector, "legal", aggregated)
            technical_ctx = market_context + data_aggregator.build_agent_context(sector, "technical", aggregated)
            brokerage_ctx = market_context + data_aggregator.build_agent_context(sector, "brokerage_models", aggregated)

            # إضافة بيانات المنافسين لسياق وكيل المنافسة
            if competitors_enriched:
                comp_lines = ["\n\n══ بيانات المنافسين الفعليين من السجل التجاري ══"]
                for i, c in enumerate(competitors_enriched, 1):
                    line = f"{i}. {c.get('name_ar', '')} ({c.get('name_en', '')}) — {c.get('activity', '')} | تأسست: {c.get('established', '?')} | الحجم: {c.get('size', '?')} | المحافظة: {c.get('governorate', '?')} | النوع: {c.get('entity_type', '?')}"
                    if c.get('website'):
                        line += f" | الموقع: {c['website']}"
                    if c.get('web_description'):
                        line += f"\n   وصف: {c['web_description']}"
                    comp_lines.append(line)
                competitive_ctx += "\n".join(comp_lines)

            # إرسال خريطة مصادر البيانات لكل وكيل
            attribution = data_aggregator.build_data_attribution(aggregated)
            event_queue.put(("data_sources_used", json.dumps(attribution, ensure_ascii=False)))

            # تشغيل الوكلاء الستة بالتوازي مع بيانات مخصصة لكل وكيل
            await asyncio.gather(
                run_agent("market_analysis", market_agent.analyze(idea, api_key, provider, model, market_context=market_ctx)),
                run_agent("financial_analysis", financial_agent.analyze(idea, api_key, provider, model, market_context=financial_ctx)),
                run_agent("competitive_analysis", competitive_agent.analyze(idea, api_key, provider, model, market_context=competitive_ctx)),
                run_agent("legal_analysis", legal_agent.analyze(idea, api_key, provider, model, market_context=legal_ctx)),
                run_agent("technical_analysis", technical_agent.analyze(idea, api_key, provider, model, market_context=technical_ctx)),
                run_agent("brokerage_models_analysis", brokerage_models_agent.analyze(idea, api_key, provider, model, market_context=brokerage_ctx)),
            )
            event_queue.put(("agents_done", None))

        def run_async():
            asyncio.run(run_agents())

        thread = threading.Thread(target=run_async)
        thread.start()

        results = {}
        # انتظار نتائج الوكلاء الستة
        while True:
            try:
                name, data = event_queue.get(timeout=300)
            except queue.Empty:
                logger.error("❌ انتهت مهلة انتظار الوكلاء (5 دقائق)")
                yield f"event: error\ndata: {json.dumps({'error': 'انتهت مهلة التحليل'}, ensure_ascii=False)}\n\n"
                return
            if name == "agents_done":
                break
            if name in ("data_sources_used", "competitors_found"):
                yield f"event: {name}\ndata: {data}\n\n"
            else:
                results[name] = data
                yield f"event: {name}\ndata: {json.dumps({'content': data}, ensure_ascii=False)}\n\n"

        # تشغيل الـ Synthesizer
        yield f"event: synthesizing\ndata: {json.dumps({'status': 'started'}, ensure_ascii=False)}\n\n"

        def run_synthesizer():
            async def _synthesize():
                return await synthesizer.synthesize(
                    idea=idea,
                    market_analysis=results.get('market_analysis', ''),
                    financial_analysis=results.get('financial_analysis', ''),
                    competitive_analysis=results.get('competitive_analysis', ''),
                    legal_analysis=results.get('legal_analysis', ''),
                    technical_analysis=results.get('technical_analysis', ''),
                    brokerage_models_analysis=results.get('brokerage_models_analysis', ''),
                    api_key=api_key,
                    provider=synthesizer_provider,
                    model_override=synthesizer_model
                )
            return asyncio.run(_synthesize())

        synth_queue = queue.Queue()
        def synth_thread():
            try:
                result = run_synthesizer()
                synth_queue.put(("ok", result))
            except Exception as e:
                synth_queue.put(("error", str(e)))

        t = threading.Thread(target=synth_thread)
        t.start()
        try:
            status, verdict = synth_queue.get(timeout=300)
        except queue.Empty:
            logger.error("❌ انتهت مهلة انتظار المُجمّع (5 دقائق)")
            status, verdict = "error", "انتهت مهلة التجميع"

        if status == "error":
            verdict = json.dumps({"summary": verdict, "consensus": [], "conflicts": [], "verdict": "خطأ", "overall_score": 0, "score_justification": "", "recommended_model": "", "model_justification": "", "advice": []}, ensure_ascii=False)

        yield f"event: final_verdict\ndata: {json.dumps({'content': verdict}, ensure_ascii=False)}\n\n"

        # تشغيل SWOT و خطة العمل بالتوازي
        yield f"event: generating_extras\ndata: {json.dumps({'status': 'started'}, ensure_ascii=False)}\n\n"

        extras_queue = queue.Queue()
        def run_extras():
            async def _extras():
                effective_model = model or get_default_model(provider)
                swot_result, plan_result = await asyncio.gather(
                    swot_agent.analyze(idea, results, api_key, provider=provider, model_override=effective_model),
                    action_plan_agent.generate(idea, results, verdict, api_key, provider=provider, model_override=effective_model),
                    return_exceptions=True
                )
                if isinstance(swot_result, Exception):
                    swot_result = json.dumps({"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}, ensure_ascii=False)
                if isinstance(plan_result, Exception):
                    plan_result = json.dumps({"executive_summary": str(plan_result), "phases": [], "total_budget": "", "key_metrics": [], "critical_success_factors": [], "risk_mitigation": []}, ensure_ascii=False)
                extras_queue.put(("ok", swot_result, plan_result))
            asyncio.run(_extras())

        et = threading.Thread(target=run_extras)
        et.start()
        try:
            _, swot_result, plan_result = extras_queue.get(timeout=300)
        except queue.Empty:
            logger.error("❌ انتهت مهلة SWOT/ActionPlan (5 دقائق)")
            swot_result = json.dumps({"strengths": [], "weaknesses": [], "opportunities": [], "threats": [], "swot_summary": []}, ensure_ascii=False)
            plan_result = json.dumps({"executive_summary": "انتهت مهلة التحليل", "phases": [], "total_budget": "", "key_metrics": [], "critical_success_factors": [], "risk_mitigation": []}, ensure_ascii=False)

        yield f"event: swot_analysis\ndata: {json.dumps({'content': swot_result}, ensure_ascii=False)}\n\n"
        yield f"event: action_plan\ndata: {json.dumps({'content': plan_result}, ensure_ascii=False)}\n\n"

        # حفظ في قاعدة البيانات
        analysis_id = save_analysis(
            idea=idea,
            market_analysis=results.get('market_analysis', ''),
            financial_analysis=results.get('financial_analysis', ''),
            competitive_analysis=results.get('competitive_analysis', ''),
            legal_analysis=results.get('legal_analysis', ''),
            technical_analysis=results.get('technical_analysis', ''),
            brokerage_models_analysis=results.get('brokerage_models_analysis', ''),
            swot_analysis=swot_result,
            action_plan=plan_result,
            final_verdict=verdict,
            sector=sector,
            requester_name=requester_name,
            requester_email=requester_email,
            requester_company=requester_company,
        )

        # إرسال معرف التحليل
        analysis = get_analysis(analysis_id)
        share_token = analysis.get('share_token', '') if analysis else ''
        report_number = analysis.get('report_number', '') if analysis else ''
        valid_until = analysis.get('valid_until', '') if analysis else ''
        yield f"event: done\ndata: {json.dumps({'status': 'completed', 'analysis_id': analysis_id, 'share_token': share_token, 'report_number': report_number, 'valid_until': valid_until}, ensure_ascii=False)}\n\n"

    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
    })


@app.route('/history')
def history():
    analyses = get_all_analyses()
    return jsonify(analyses)


@app.route('/history/<int:analysis_id>')
def history_detail(analysis_id):
    analysis = get_analysis(analysis_id)
    if not analysis:
        return jsonify({'error': 'التحليل غير موجود'}), 404
    return jsonify(analysis)


@app.route('/history/<int:analysis_id>', methods=['DELETE'])
def history_delete(analysis_id):
    analysis = get_analysis(analysis_id)
    if not analysis:
        return jsonify({'error': 'التحليل غير موجود'}), 404
    delete_analysis(analysis_id)
    return jsonify({'success': True})


@app.route('/rate/<int:analysis_id>', methods=['POST'])
def rate(analysis_id):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'طلب غير صالح'}), 400
    rating = data.get('rating', 0)
    feedback = data.get('feedback', '')
    if not 1 <= rating <= 5:
        return jsonify({'error': 'التقييم يجب أن يكون بين 1 و 5'}), 400
    rate_analysis(analysis_id, rating, feedback)
    return jsonify({'success': True})


@app.route('/compare')
def compare():
    id1 = request.args.get('id1', type=int)
    id2 = request.args.get('id2', type=int)
    if not id1 or not id2:
        return jsonify({'error': 'يجب تحديد تحليلين للمقارنة'}), 400
    a1 = get_analysis(id1)
    a2 = get_analysis(id2)
    if not a1 or not a2:
        return jsonify({'error': 'أحد التحليلات غير موجود'}), 404
    return jsonify({'analysis1': a1, 'analysis2': a2})


@app.route('/dashboard')
def dashboard():
    stats = get_dashboard_stats()
    return jsonify(stats)


def _parse_agent_analysis(json_str):
    """تحويل JSON التحليل إلى نص مقروء."""
    if not json_str:
        return "غير متوفر"
    try:
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
        parts = []
        if data.get('title'):
            parts.append(f"العنوان: {data['title']}")
        if data.get('summary'):
            parts.append(f"الملخص: {data['summary']}")
        if data.get('score') is not None:
            parts.append(f"التقييم: {data['score']}/10")
        if data.get('details'):
            parts.append("النقاط الرئيسية:")
            for i, d in enumerate(data['details'], 1):
                parts.append(f"  {i}. {d}")
        if data.get('recommendation'):
            parts.append(f"التوصية: {data['recommendation']}")
        return "\n".join(parts) if parts else json_str[:500]
    except (json.JSONDecodeError, TypeError, AttributeError):
        return str(json_str)[:500]


def _parse_brokerage_models(json_str):
    """تحويل JSON تحليل نماذج الوساطة إلى نص مقروء."""
    if not json_str:
        return "غير متوفر"
    try:
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
        parts = []
        if data.get('title'):
            parts.append(f"العنوان: {data['title']}")
        if data.get('summary'):
            parts.append(f"الملخص: {data['summary']}")
        if data.get('models'):
            parts.append("النماذج:")
            for m in data['models']:
                name = m.get('name', '')
                score = m.get('score', 0)
                fit = m.get('fit_for_bahrain', '')
                parts.append(f"  - {name}: {score}/10 (ملاءمة: {fit})")
                if m.get('pros'):
                    parts.append(f"    إيجابيات: {', '.join(m['pros'][:3])}")
                if m.get('cons'):
                    parts.append(f"    سلبيات: {', '.join(m['cons'][:2])}")
        if data.get('recommended_model'):
            parts.append(f"النموذج الموصى به: {data['recommended_model']}")
        if data.get('recommendation_reason'):
            parts.append(f"سبب التوصية: {data['recommendation_reason']}")
        return "\n".join(parts) if parts else json_str[:500]
    except (json.JSONDecodeError, TypeError, AttributeError):
        return str(json_str)[:500]


def _parse_verdict(json_str):
    """تحويل JSON الحكم النهائي إلى نص مقروء."""
    if not json_str:
        return "غير متوفر"
    try:
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
        parts = []
        if data.get('verdict'):
            parts.append(f"القرار: {data['verdict']}")
        if data.get('overall_score') is not None:
            parts.append(f"التقييم الإجمالي: {data['overall_score']}/10")
        if data.get('summary'):
            parts.append(f"الملخص: {data['summary']}")
        if data.get('score_justification'):
            parts.append(f"تبرير التقييم: {data['score_justification']}")
        if data.get('recommended_model'):
            parts.append(f"النموذج الموصى به: {data['recommended_model']}")
        if data.get('model_justification'):
            parts.append(f"تبرير النموذج: {data['model_justification']}")
        if data.get('consensus'):
            parts.append("نقاط التوافق:")
            for i, c in enumerate(data['consensus'], 1):
                parts.append(f"  {i}. {c}")
        if data.get('conflicts'):
            parts.append("نقاط الاختلاف:")
            for i, c in enumerate(data['conflicts'], 1):
                parts.append(f"  {i}. {c}")
        if data.get('advice'):
            parts.append("النصائح الاستراتيجية:")
            for i, a in enumerate(data['advice'], 1):
                parts.append(f"  {i}. {a}")
        return "\n".join(parts) if parts else json_str[:500]
    except (json.JSONDecodeError, TypeError, AttributeError):
        return str(json_str)[:500]


def _parse_swot(json_str):
    """تحويل JSON تحليل SWOT إلى نص مقروء."""
    if not json_str:
        return "غير متوفر"
    try:
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
        parts = []
        for key, label in [('strengths', 'نقاط القوة'), ('weaknesses', 'نقاط الضعف'),
                           ('opportunities', 'الفرص'), ('threats', 'التهديدات')]:
            items = data.get(key, [])
            if items:
                parts.append(f"{label}:")
                for i, item in enumerate(items, 1):
                    point = item.get('point', item) if isinstance(item, dict) else item
                    parts.append(f"  {i}. {point}")
        return "\n".join(parts) if parts else json_str[:500]
    except (json.JSONDecodeError, TypeError, AttributeError):
        return str(json_str)[:500]


def _parse_action_plan(json_str):
    """تحويل JSON خطة العمل إلى نص مقروء."""
    if not json_str:
        return "غير متوفر"
    try:
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
        parts = []
        if data.get('executive_summary'):
            parts.append(f"الملخص التنفيذي: {data['executive_summary']}")
        if data.get('total_budget'):
            parts.append(f"الميزانية الإجمالية: {data['total_budget']}")
        if data.get('phases'):
            parts.append("المراحل:")
            for phase in data['phases']:
                name = phase.get('name', 'مرحلة')
                duration = phase.get('duration', '')
                parts.append(f"  - {name} ({duration})")
                for task in phase.get('tasks', []):
                    parts.append(f"    • {task}")
        if data.get('key_metrics'):
            parts.append("مؤشرات الأداء:")
            for i, m in enumerate(data['key_metrics'], 1):
                parts.append(f"  {i}. {m}")
        if data.get('critical_success_factors'):
            parts.append("عوامل النجاح الحاسمة:")
            for i, f in enumerate(data['critical_success_factors'], 1):
                parts.append(f"  {i}. {f}")
        return "\n".join(parts) if parts else json_str[:500]
    except (json.JSONDecodeError, TypeError, AttributeError):
        return str(json_str)[:500]


def _build_followup_context(analysis):
    """بناء system prompt احترافي لأسئلة المتابعة مع تحويل التحليلات لنص مقروء."""
    # جلب بيانات السوق البحريني حسب القطاع المحفوظ مع التحليل
    analysis_sector = analysis.get('sector', 'food_hospitality')
    bahrain_context = bahrain_service.build_market_context(sector=analysis_sector)

    return f"""أنت مستشار متخصص في الوساطة التجارية ومحلل استراتيجي متخصص في السوق البحريني. لديك خبرة عميقة في نماذج الوساطة، المنصات التجارية، والتنظيمات القانونية في مملكة البحرين.

تم إجراء دراسة جدوى شاملة للوساطة التجارية في القطاع المحدد من قبل فريق من المحللين المتخصصين. استخدم هذه التحليلات وبيانات السوق البحريني الحقيقية للإجابة على أسئلة المستخدم.
{bahrain_context}

═══ موضوع الدراسة ═══
{analysis['idea']}

═══ تحليل الطلب على الوساطة ═══
{_parse_agent_analysis(analysis.get('market_analysis', ''))}

═══ التحليل المالي للوساطة ═══
{_parse_agent_analysis(analysis.get('financial_analysis', ''))}

═══ تحليل المنافسة في الوساطة ═══
{_parse_agent_analysis(analysis.get('competitive_analysis', ''))}

═══ التحليل القانوني للوساطة ═══
{_parse_agent_analysis(analysis.get('legal_analysis', ''))}

═══ التحليل التقني للمنصة ═══
{_parse_agent_analysis(analysis.get('technical_analysis', ''))}

═══ تحليل نماذج الوساطة ═══
{_parse_brokerage_models(analysis.get('brokerage_models_analysis', ''))}

═══ تحليل SWOT ═══
{_parse_swot(analysis.get('swot_analysis', ''))}

═══ خطة العمل التنفيذية ═══
{_parse_action_plan(analysis.get('action_plan', ''))}

═══ الحكم النهائي ═══
{_parse_verdict(analysis.get('final_verdict', ''))}

═══ تعليمات الإجابة ═══
أنت تجيب على أسئلة متابعة من المستخدم حول دراسة جدوى الوساطة التجارية بناءً على التحليلات أعلاه.

عند الإجابة، التزم بما يلي:
1. **العمق والتفصيل**: قدم إجابات شاملة ومفصلة. لا تكتفِ بإجابات سطحية. استخدم الأرقام والمعطيات من التحليلات عند الإمكان.
2. **الهيكلة**: استخدم العناوين (##) والنقاط المرقمة والقوائم لتنظيم إجابتك.
3. **التحليل النقدي**: لا تكتفِ بتكرار ما في التحليلات. أضف رؤية نقدية، وربط بين النقاط، واقترح حلولاً عملية.
4. **السياق العربي**: خذ بعين الاعتبار طبيعة الأسواق العربية، الثقافة التجارية، والبيئة التنظيمية في المنطقة.
5. **اللغة**: أجب بالعربية الفصحى بأسلوب مهني واحترافي.
6. **الأمانة**: إذا كان السؤال خارج نطاق التحليلات المتوفرة، أشر إلى ذلك بوضوح وقدم رأياً عاماً مع التنبيه.
7. **المحادثة**: تذكّر سياق الأسئلة السابقة في هذه المحادثة وابنِ عليها.
8. **المصادر**: عند الاستشهاد بأي رقم أو إحصائية من بيانات السوق البحريني، اذكر صراحةً أن المصدر هو "بوابة البيانات المفتوحة البحرينية (data.gov.bh)"."""


@app.route('/ask-followup', methods=['POST'])
def ask_followup():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'طلب غير صالح'}), 400
    question = data.get('question', '').strip()
    analysis_id = data.get('analysis_id')
    provider = data.get('provider', 'openai').strip()
    api_key = data.get('api_key', '').strip()
    if not api_key:
        if provider == 'anthropic':
            api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        elif provider == 'gemini':
            api_key = os.environ.get('GEMINI_API_KEY', '')
        else:
            api_key = os.environ.get('OPENAI_API_KEY', '')
    conversation_history = data.get('conversation_history', [])
    model = data.get('model', '').strip()
    web_search_enabled = data.get('web_search', False)

    if not question or not analysis_id:
        return jsonify({'error': 'الرجاء إدخال السؤال'}), 400

    analysis = get_analysis(analysis_id)
    if not analysis:
        return jsonify({'error': 'التحليل غير موجود'}), 404

    try:
        context = _build_followup_context(analysis)
        web_search_used = False

        logger.info(f"📨 سؤال متابعة: {question[:100]}... | analysis_id={analysis_id} | provider={provider} | history={len(conversation_history)} | web_search={web_search_enabled}")

        # --- بناء الرسائل الأساسية ---
        def _build_messages(system_content):
            msgs = [{"role": "system", "content": system_content}]
            if conversation_history:
                for msg in conversation_history[-20:]:
                    if msg.get('role') in ('user', 'assistant') and msg.get('content'):
                        msgs.append({"role": msg['role'], "content": msg['content'][:2000]})
            msgs.append({"role": "user", "content": question})
            return msgs

        # --- DuckDuckGo fallback (لـ Anthropic أو عند فشل البحث الأصلي) ---
        def _ddg_web_context():
            idea_short = analysis['idea'][:100]
            search_query = f"{question} {idea_short} البحرين"
            search_results = search_web(search_query, max_results=5)
            if not search_results:
                search_results = search_web(f"{idea_short} البحرين", max_results=5)
            if search_results:
                return f"""

═══ نتائج بحث الويب ═══
تم العثور على المعلومات التالية من الإنترنت بخصوص سؤال المستخدم:

{search_results}

═══ تعليمات استخدام نتائج البحث ═══
- استخدم هذه النتائج لدعم إجابتك بمعلومات حديثة وواقعية
- اذكر المصادر عند الاستشهاد بمعلومة من نتائج البحث
- لا تكتفِ بنقل النتائج حرفياً — حللها واربطها بسياق دراسة الوساطة التجارية
- إذا تعارضت نتائج البحث مع التحليل الأصلي، وضّح ذلك للمستخدم
- أشر في بداية إجابتك أنك استعنت بنتائج بحث الويب
"""
            return ""

        # ============================================================
        # مسار 1: OpenAI مع بحث ويب أصلي (Responses API + web_search)
        # ============================================================
        if provider == 'openai' and web_search_enabled:
            logger.info("🔍 OpenAI: استخدام بحث الويب الأصلي (Responses API + web_search)")
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)

                # بناء input messages لـ Responses API
                input_msgs = []
                if conversation_history:
                    for msg in conversation_history[-20:]:
                        if msg.get('role') in ('user', 'assistant') and msg.get('content'):
                            input_msgs.append({"role": msg['role'], "content": msg['content'][:2000]})
                input_msgs.append({"role": "user", "content": question})

                response = client.responses.create(
                    model=model or get_default_model(provider),
                    instructions=context,
                    input=input_msgs,
                    tools=[{"type": "web_search"}],
                    max_output_tokens=4000,
                )
                answer = response.output_text or "لم أتمكن من الإجابة"
                web_search_used = True
                logger.info(f"✅ OpenAI Responses API + web_search نجح | طول الإجابة: {len(answer)}")
            except Exception as e:
                logger.warning(f"⚠️ OpenAI web_search فشل ({type(e).__name__}: {e}), fallback إلى DuckDuckGo")
                web_ctx = _ddg_web_context()
                messages = _build_messages(context + web_ctx)
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model=model or get_default_model(provider),
                    messages=messages,
                    max_completion_tokens=4000
                )
                answer = response.choices[0].message.content or "لم أتمكن من الإجابة"
                web_search_used = bool(web_ctx)

        # ============================================================
        # مسار 2: Gemini مع بحث ويب أصلي (Google Search Grounding)
        # ============================================================
        elif provider == 'gemini' and web_search_enabled:
            logger.info("🔍 Gemini: استخدام Google Search Grounding")
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                # إنشاء أداة google_search_retrieval
                google_search_tool = genai.protos.Tool(
                    google_search_retrieval=genai.protos.GoogleSearchRetrieval()
                )
                gemini_model = genai.GenerativeModel(
                    model or get_default_model(provider),
                    system_instruction=context,
                    tools=[google_search_tool]
                )
                chat_history = []
                if conversation_history:
                    for msg in conversation_history[-20:]:
                        if msg.get('role') in ('user', 'assistant') and msg.get('content'):
                            role = 'user' if msg['role'] == 'user' else 'model'
                            chat_history.append({"role": role, "parts": [msg['content'][:2000]]})
                chat = gemini_model.start_chat(history=chat_history)
                gemini_resp = chat.send_message(
                    question,
                    generation_config=genai.types.GenerationConfig(max_output_tokens=4000)
                )
                answer = gemini_resp.text or "لم أتمكن من الإجابة"
                web_search_used = True
                logger.info(f"✅ Gemini Google Search Grounding نجح | طول الإجابة: {len(answer)}")
            except Exception as e:
                logger.warning(f"⚠️ Gemini grounding فشل ({type(e).__name__}: {e}), fallback إلى DuckDuckGo")
                web_ctx = _ddg_web_context()
                messages = _build_messages(context + web_ctx)
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                gemini_model = genai.GenerativeModel(
                    model or get_default_model(provider),
                    system_instruction=messages[0]['content']
                )
                gemini_history = []
                for msg in messages[1:]:
                    role = 'user' if msg['role'] == 'user' else 'model'
                    gemini_history.append({"role": role, "parts": [msg['content']]})
                chat = gemini_model.start_chat(history=gemini_history[:-1])
                gemini_resp = chat.send_message(
                    gemini_history[-1]['parts'][0],
                    generation_config=genai.types.GenerationConfig(max_output_tokens=4000)
                )
                answer = gemini_resp.text or "لم أتمكن من الإجابة"
                web_search_used = bool(web_ctx)

        # ============================================================
        # مسار 3: Anthropic مع بحث DuckDuckGo (لا يدعم بحث أصلي)
        # ============================================================
        elif provider == 'anthropic' and web_search_enabled:
            logger.info("🔍 Anthropic: استخدام DuckDuckGo (لا يدعم بحث ويب أصلي)")
            web_ctx = _ddg_web_context()
            messages = _build_messages(context + web_ctx)
            import anthropic as anthropic_sdk
            client = anthropic_sdk.Anthropic(api_key=api_key)
            system_msg = ""
            api_messages = []
            for msg in messages:
                if msg['role'] == 'system':
                    system_msg = msg['content']
                else:
                    api_messages.append(msg)
            response = client.messages.create(
                model=model or get_default_model(provider),
                max_tokens=4000,
                system=system_msg,
                messages=api_messages,
            )
            answer = (response.content[0].text if response.content else None) or "لم أتمكن من الإجابة"
            web_search_used = bool(web_ctx)

        # ============================================================
        # مسار 4: بدون بحث ويب (جميع المزودين)
        # ============================================================
        else:
            messages = _build_messages(context)
            if provider == 'gemini':
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                gemini_model = genai.GenerativeModel(
                    model or get_default_model(provider),
                    system_instruction=messages[0]['content']
                )
                gemini_history = []
                for msg in messages[1:]:
                    role = 'user' if msg['role'] == 'user' else 'model'
                    gemini_history.append({"role": role, "parts": [msg['content']]})
                chat = gemini_model.start_chat(history=gemini_history[:-1])
                gemini_resp = chat.send_message(
                    gemini_history[-1]['parts'][0],
                    generation_config=genai.types.GenerationConfig(max_output_tokens=4000)
                )
                answer = gemini_resp.text or "لم أتمكن من الإجابة"
            elif provider == 'anthropic':
                import anthropic as anthropic_sdk
                client = anthropic_sdk.Anthropic(api_key=api_key)
                system_msg = ""
                api_messages = []
                for msg in messages:
                    if msg['role'] == 'system':
                        system_msg = msg['content']
                    else:
                        api_messages.append(msg)
                response = client.messages.create(
                    model=model or get_default_model(provider),
                    max_tokens=4000,
                    system=system_msg,
                    messages=api_messages,
                )
                answer = (response.content[0].text if response.content else None) or "لم أتمكن من الإجابة"
            else:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model=model or get_default_model(provider),
                    messages=messages,
                    max_completion_tokens=4000
                )
                answer = response.choices[0].message.content or "لم أتمكن من الإجابة"

        logger.info(f"✅ إجابة المتابعة: {len(answer)} حرف | web_search_used={web_search_used}")
        return jsonify({'answer': answer, 'web_search_used': web_search_used})

    except Exception as e:
        logger.error(f"❌ خطأ في سؤال المتابعة: {type(e).__name__}: {e}")
        logger.error(f"📋 التتبع:\n{traceback.format_exc()}")
        return jsonify({'answer': f"حدث خطأ: {type(e).__name__} - {str(e)}"}), 500


@app.route('/export-pdf/<int:analysis_id>')
def export_pdf(analysis_id):
    analysis = get_analysis(analysis_id)
    if not analysis:
        return jsonify({'error': 'التحليل غير موجود'}), 404

    # Generate HTML report
    html = render_template('report.html', analysis=analysis)

    # Try weasyprint, fallback to browser print-to-PDF
    report_num = analysis.get('report_number', f'report_{analysis_id}')
    if not getattr(app, '_weasyprint_broken', False):
        try:
            import io, contextlib
            with contextlib.redirect_stderr(io.StringIO()):
                from weasyprint import HTML as WeasyprintHTML
            import tempfile
            pdf_path = Path(tempfile.gettempdir()) / f"bsi_{report_num}.pdf"
            WeasyprintHTML(string=html).write_pdf(str(pdf_path))
            return send_file(str(pdf_path), as_attachment=True,
                            download_name=f'BSI_{report_num}.pdf',
                            mimetype='application/pdf')
        except Exception as pdf_err:
            app._weasyprint_broken = True
            logger.warning(f"weasyprint PDF failed ({type(pdf_err).__name__}), will use browser print for all exports")

    # Fallback: inject print toolbar into the HTML report
    print_bar = '''<div id="bsi-print-bar" style="position:fixed;top:0;left:0;right:0;z-index:9999;
        background:linear-gradient(135deg,#1565C0,#0D47A1);color:#fff;padding:12px 24px;
        display:flex;align-items:center;justify-content:space-between;font-family:Tajawal,sans-serif;
        box-shadow:0 2px 8px rgba(0,0,0,0.3);direction:rtl">
        <span style="font-size:14px;font-weight:600">&#128196; لتصدير PDF: اختر "Save as PDF" من نافذة الطباعة</span>
        <div>
            <button onclick="document.getElementById(\'bsi-print-bar\').style.display=\'none\';window.print()"
                style="background:#fff;color:#1565C0;border:none;padding:8px 24px;border-radius:6px;
                font-weight:700;cursor:pointer;font-size:14px;font-family:Tajawal,sans-serif;margin-left:8px">
                &#128424; طباعة / تصدير PDF
            </button>
            <button onclick="document.getElementById(\'bsi-print-bar\').style.display=\'none\'"
                style="background:transparent;color:#fff;border:1px solid rgba(255,255,255,0.5);
                padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px;font-family:Tajawal,sans-serif">
                &#10005; إغلاق
            </button>
        </div>
    </div>
    <style>@media print { #bsi-print-bar { display: none !important; } body { padding-top: 0 !important; } }
    @media screen { body { padding-top: 60px; } }</style>'''
    html = html.replace('<body>', f'<body>{print_bar}', 1)
    return Response(html, mimetype='text/html', headers={
        'Content-Disposition': f'inline; filename=BSI_{report_num}.html'
    })


@app.route('/api-key/status')
def api_key_status():
    saved_key = os.environ.get('OPENAI_API_KEY', '')
    return jsonify({'saved': bool(saved_key)})


@app.route('/api-key/save', methods=['POST'])
def save_api_key():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'طلب غير صالح'}), 400
    api_key = data.get('api_key', '')

    if not api_key:
        return jsonify({'error': 'الرجاء إدخال مفتاح API'}), 400

    ENV_PATH.write_text(f'OPENAI_API_KEY={api_key}\n')
    os.environ['OPENAI_API_KEY'] = api_key

    return jsonify({'success': True})


@app.route('/providers')
def get_providers():
    from agents.base import PROVIDERS
    return jsonify(PROVIDERS)


@app.route('/sectors')
def get_sectors():
    """قائمة القطاعات المتاحة لدراسة جدوى الوساطة."""
    return jsonify({k: {"name_ar": v["name_ar"], "icon": v["icon"]} for k, v in SECTORS.items()})


@app.route('/api/market-needs/<sector>')
def market_needs_data(sector):
    """بيانات فرص الوساطة لقطاع معين - مهيكلة للعرض المرئي."""
    data = bahrain_service.get_sector_data(sector)
    return jsonify(data)


@app.route('/api/data-sources/meta')
def data_sources_meta():
    """Metadata about all 7 data sources (static, no sector needed)."""
    meta = data_aggregator.get_sources_meta()
    return jsonify(meta)


@app.route('/api/data-sources/fetch')
def data_sources_fetch():
    """Fetch data from all 7 sources for a given sector."""
    sector = request.args.get('sector', '').strip()
    if not sector or sector not in SECTORS:
        return jsonify({'error': 'الرجاء اختيار قطاع صالح'}), 400

    import asyncio as _asyncio
    from datetime import datetime as _dt

    try:
        results = _asyncio.run(data_aggregator.fetch_all(sector))
    except Exception as e:
        logger.error(f"Data sources fetch error: {e}")
        return jsonify({'error': str(e)}), 500

    meta = data_aggregator.get_sources_meta()
    meta_by_key = {s['key']: s for s in meta['sources']}

    sources_response = {}
    total_points = 0
    for source_key, source_data in results.items():
        has_error = bool(source_data.get('error'))
        dp = source_data.get('data_points', 0)
        total_points += dp
        sources_response[source_key] = {
            'meta': meta_by_key.get(source_key, {}),
            'status': 'error' if has_error else 'success',
            'error': source_data.get('error') if has_error else None,
            'data_points': dp,
            'reliability': source_data.get('reliability', 0),
            'is_live': source_data.get('is_live', False),
            'note': source_data.get('note', ''),
            'data': source_data,
        }

    return jsonify({
        'sector': sector,
        'sector_name_ar': SECTORS[sector]['name_ar'],
        'fetched_at': _dt.now().isoformat(),
        'total_data_points': total_points,
        'sources': sources_response,
    })


@app.route('/api/analyze-market-needs', methods=['POST'])
def analyze_market_needs():
    """تحليل فرص الوساطة التجارية بالذكاء الاصطناعي - يحلل البيانات ويقترح نماذج وساطة."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'طلب غير صالح'}), 400
    sector = data.get('sector', '').strip()
    budget = data.get('budget', '').strip()
    provider = data.get('provider', 'openai').strip()
    model = data.get('model', '').strip()
    api_key = data.get('api_key', '').strip()
    if not api_key:
        if provider == 'anthropic':
            api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        elif provider == 'gemini':
            api_key = os.environ.get('GEMINI_API_KEY', '')
        else:
            api_key = os.environ.get('OPENAI_API_KEY', '')

    if not api_key:
        return jsonify({'error': 'الرجاء إدخال مفتاح API'}), 400

    if not sector or sector not in SECTORS:
        return jsonify({'error': 'الرجاء اختيار قطاع صالح'}), 400

    try:
        # جلب بيانات القطاع المهيكلة + السياق النصي
        sector_data = bahrain_service.get_sector_data(sector)
        market_context = bahrain_service.build_market_context(sector=sector)
        sector_name = sector_data.get('sector_name', sector)

        # قيد رأس المال
        budget_constraint = ""
        if budget:
            budget_int = int(budget)
            budget_formatted = f"{budget_int:,}"
            budget_constraint = f"""
** قيد رأس المال: المستثمر يملك أقل من {budget_formatted} دينار بحريني **
- يجب أن تكون جميع نماذج الوساطة المقترحة قابلة للتنفيذ بميزانية لا تتجاوز {budget_formatted} د.ب
- لا تقترح أي نموذج يتطلب رأس مال أعلى من {budget_formatted} د.ب
- ركز على نماذج الوساطة منخفضة التكلفة إذا كانت الميزانية محدودة
"""

        # سياق الوساطة الخاص بالقطاع
        brokerage_ctx = SECTORS.get(sector, {}).get('brokerage_context', '')

        system_prompt = f"""أنت محلل متخصص في الوساطة التجارية (الدلالة/السمسرة) في السوق البحريني.

مهمتك: تحليل بيانات السوق الحقيقية لقطاع "{sector_name}" وتحديد فرص إنشاء شركة وساطة تجارية تربط البائعين بالمشترين في هذا القطاع.

سياق الوساطة في هذا القطاع:
{brokerage_ctx}

{market_context}
{budget_constraint}

** الوساطة التجارية تعني: شركة/منصة تربط البائعين بالمشترين وتأخذ عمولة أو رسوم على كل معاملة ناجحة. لا تبيع ولا تشتري بنفسها. **

بناءً على البيانات أعلاه، حلل فرص الوساطة التجارية (الدلالة) في هذا القطاع.

** مهم جداً: يجب أن ترد بصيغة JSON فقط بالهيكل التالي **
{{
  "sector_overview": "تحليل شامل لواقع الوساطة في هذا القطاع: هل يعتمد على وسطاء تقليديين أم علاقات شخصية؟ ما حجم المعاملات التي يمكن التوسط فيها؟ (فقرتين أو ثلاث)",
  "buyer_seller_map": [
    {{"sellers": "وصف البائعين (مثلاً: مصانع أغذية، مستوردين)", "buyers": "وصف المشترين (مثلاً: مطاعم، فنادق)", "transaction_type": "نوع المعاملة (مثلاً: توريد مواد خام)", "estimated_volume": "حجم المعاملات التقديري", "current_method": "كيف تتم المعاملات حالياً (علاقات شخصية، وسطاء تقليديين، منصات...)"}},
    ...3-5 أزواج
  ],
  "brokerage_models": [
    {{"model_name": "اسم نموذج الوساطة (مثلاً: سوق B2B إلكتروني، وساطة بالعمولة، نظام مزادات...)", "how_it_works": "كيف يعمل هذا النموذج في هذا القطاع تحديداً", "revenue_model": "كيف يربح الوسيط (عمولة %، اشتراك شهري، رسوم إدراج...)", "estimated_commission": "نسبة العمولة أو الرسوم المتوقعة", "potential": "عالي أو متوسط أو منخفض", "startup_cost": "تكلفة الإطلاق التقديرية بالدينار البحريني"}},
    ...4-6 نماذج
  ],
  "gaps": ["فجوة 1: وصف مفصل لفجوة في الوساطة الحالية يمكن استغلالها", ...3-5 فجوات],
  "risks": ["مخاطرة 1: وصف مفصل", ...3-5 مخاطر],
  "best_model": "أفضل نموذج وساطة مقترح لهذا القطاع مع تبرير",
  "estimated_demand": "تقدير حجم الطلب على خدمات الوساطة في هذا القطاع",
  "recommendation": "التوصية الاستراتيجية النهائية: ما النموذج الأمثل ولماذا وكيف تبدأ"
}}

- buyer_seller_map: 3-5 أزواج بائع-مشتري رئيسية في القطاع
- brokerage_models: 4-6 نماذج وساطة مع تفاصيل الإيرادات والتكلفة
- potential يجب أن يكون: "عالي" أو "متوسط" أو "منخفض"
- استخدم الأرقام الحقيقية من البيانات المرفقة في تحليلك
- عند ذكر أي إحصائية، اذكر أن المصدر هو "بوابة البيانات المفتوحة البحرينية (data.gov.bh)"
- لا تضف أي نص خارج JSON"""

        budget_note = f" برأس مال لا يتجاوز {int(budget):,} دينار بحريني" if budget else ""
        user_message = f"حلل فرص الوساطة التجارية (الدلالة/السمسرة) في قطاع \"{sector_name}\" بالسوق البحريني: من البائعون؟ من المشترون؟ ما المعاملات التي يمكن التوسط فيها؟ ما أفضل نموذج وساطة؟{budget_note}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        import asyncio
        from agents.base import create_completion

        async def _run():
            return await create_completion(provider, model or get_default_model(provider), api_key, messages, max_tokens=4000, temperature=0.6)

        content = asyncio.run(_run())

        try:
            result = json.loads(content)
            return jsonify({'analysis': result})
        except json.JSONDecodeError:
            return jsonify({'analysis': {'sector_overview': content, 'buyer_seller_map': [], 'brokerage_models': [], 'gaps': [], 'risks': [], 'recommendation': '', 'best_model': '', 'estimated_demand': ''}})

    except Exception as e:
        logger.error(f"❌ خطأ في تحليل فرص الوساطة: {type(e).__name__}: {e}")
        logger.error(f"📋 التتبع:\n{traceback.format_exc()}")
        return jsonify({'error': f'حدث خطأ: {type(e).__name__} - {str(e)}'}), 500


@app.route('/admin/sync-data', methods=['POST'])
def sync_data():
    """تحديث بيانات البحرين من المنصة المفتوحة."""
    try:
        count = bahrain_service.sync_all_data()
        return jsonify({'success': True, 'message': f'تم تحديث {count} مجموعة بيانات بنجاح'})
    except Exception as e:
        logger.error(f"❌ فشل مزامنة البيانات: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/data-status')
def data_status():
    """حالة آخر تحديث للبيانات."""
    status = get_bahrain_data_status()
    return jsonify(status)


if __name__ == '__main__':
    webbrowser.open('http://localhost:5000')
    app.run(debug=True, use_reloader=False)
