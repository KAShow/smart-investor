import asyncio
import json
import logging
import os
import queue
import threading
import traceback
import webbrowser
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response, send_file
from dotenv import load_dotenv
from tenacity import RetryError
from agents import (MarketLogicAgent, FinancialAgent, CompetitiveAgent,
                    LegalAgent, TechnicalAgent, SynthesizerAgent, SwotAgent, ActionPlanAgent)
from database import (init_db, save_analysis, get_all_analyses, get_analysis,
                      delete_analysis, get_analysis_by_token, rate_analysis, get_dashboard_stats,
                      get_bahrain_data_status)
from bahrain_data import BahrainDataService, SECTORS
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
synthesizer = SynthesizerAgent()
swot_agent = SwotAgent()
action_plan_agent = ActionPlanAgent()
bahrain_service = BahrainDataService()

# تهيئة قاعدة البيانات
init_db()


def validate_input(idea, api_key):
    """التحقق من صحة المدخلات وإرجاع رسالة خطأ أو None"""
    if not api_key:
        return 'الرجاء إدخال مفتاح API'
    if not idea:
        return 'الرجاء إدخال الفكرة الاستثمارية'
    if len(idea) < 10:
        return 'الفكرة قصيرة جداً - الرجاء إدخال وصف لا يقل عن 10 أحرف'
    if len(idea) > 5000:
        return 'الفكرة طويلة جداً - الحد الأقصى 5000 حرف'
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


@app.route('/analyze-stream')
def analyze_stream():
    idea = request.args.get('idea', '').strip()
    api_key = request.args.get('api_key', '').strip() or os.environ.get('OPENAI_API_KEY', '')
    provider = request.args.get('provider', 'openai').strip()
    model = request.args.get('model', '').strip() or None
    sector = request.args.get('sector', 'general').strip()
    budget = request.args.get('budget', '').strip()

    error = validate_input(idea, api_key)
    if error:
        return jsonify({'error': error}), 400

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
- قيّم الفكرة من منظور هذه الميزانية: هل هي كافية؟ هل تحتاج تعديل؟
- إذا كانت الميزانية غير كافية للفكرة، وضّح ذلك بصراحة واقترح بديلاً أصغر
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

            # تشغيل الوكلاء الخمسة بالتوازي مع بيانات السوق البحريني
            await asyncio.gather(
                run_agent("market_analysis", market_agent.analyze(idea, api_key, provider, model, market_context=market_context)),
                run_agent("financial_analysis", financial_agent.analyze(idea, api_key, provider, model, market_context=market_context)),
                run_agent("competitive_analysis", competitive_agent.analyze(idea, api_key, provider, model, market_context=market_context)),
                run_agent("legal_analysis", legal_agent.analyze(idea, api_key, provider, model, market_context=market_context)),
                run_agent("technical_analysis", technical_agent.analyze(idea, api_key, provider, model, market_context=market_context)),
            )
            event_queue.put(("agents_done", None))

        def run_async():
            asyncio.run(run_agents())

        thread = threading.Thread(target=run_async)
        thread.start()

        results = {}
        # انتظار نتائج الوكلاء الخمسة
        while True:
            name, data = event_queue.get()
            if name == "agents_done":
                break
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
                    api_key=api_key,
                    provider=provider,
                    model_override=model
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
        status, verdict = synth_queue.get()

        if status == "error":
            verdict = json.dumps({"summary": verdict, "consensus": [], "conflicts": [], "verdict": "خطأ", "overall_score": 0, "score_justification": "", "advice": []}, ensure_ascii=False)

        yield f"event: final_verdict\ndata: {json.dumps({'content': verdict}, ensure_ascii=False)}\n\n"

        # تشغيل SWOT و خطة العمل بالتوازي
        yield f"event: generating_extras\ndata: {json.dumps({'status': 'started'}, ensure_ascii=False)}\n\n"

        extras_queue = queue.Queue()
        def run_extras():
            async def _extras():
                swot_result, plan_result = await asyncio.gather(
                    swot_agent.analyze(idea, results, api_key),
                    action_plan_agent.generate(idea, results, verdict, api_key),
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
        _, swot_result, plan_result = extras_queue.get()

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
            swot_analysis=swot_result,
            action_plan=plan_result,
            final_verdict=verdict,
            sector=sector
        )

        # إرسال معرف التحليل
        analysis = get_analysis(analysis_id)
        share_token = analysis.get('share_token', '') if analysis else ''
        yield f"event: done\ndata: {json.dumps({'status': 'completed', 'analysis_id': analysis_id, 'share_token': share_token}, ensure_ascii=False)}\n\n"

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
    analysis_sector = analysis.get('sector', 'general')
    bahrain_context = bahrain_service.build_market_context(sector=analysis_sector)

    return f"""أنت مستشار استثماري أول ومحلل استراتيجي متخصص في السوق البحريني. لديك خبرة عميقة في تحليل الأسواق، التمويل، التقنية، والتنظيمات القانونية في مملكة البحرين.

تم إجراء تحليل شامل للفكرة الاستثمارية التالية من قبل فريق من المحللين المتخصصين. استخدم هذه التحليلات وبيانات السوق البحريني الحقيقية للإجابة على أسئلة المستخدم.
{bahrain_context}

═══ الفكرة الاستثمارية ═══
{analysis['idea']}

═══ تحليل منطق السوق ═══
{_parse_agent_analysis(analysis.get('market_analysis', ''))}

═══ التحليل المالي ═══
{_parse_agent_analysis(analysis.get('financial_analysis', ''))}

═══ التحليل التنافسي ═══
{_parse_agent_analysis(analysis.get('competitive_analysis', ''))}

═══ التحليل القانوني والتنظيمي ═══
{_parse_agent_analysis(analysis.get('legal_analysis', ''))}

═══ التحليل التقني ═══
{_parse_agent_analysis(analysis.get('technical_analysis', ''))}

═══ تحليل SWOT ═══
{_parse_swot(analysis.get('swot_analysis', ''))}

═══ خطة العمل التنفيذية ═══
{_parse_action_plan(analysis.get('action_plan', ''))}

═══ الحكم النهائي ═══
{_parse_verdict(analysis.get('final_verdict', ''))}

═══ تعليمات الإجابة ═══
أنت تجيب على أسئلة متابعة من المستخدم حول هذه الفكرة الاستثمارية بناءً على التحليلات أعلاه.

عند الإجابة، التزم بما يلي:
1. **العمق والتفصيل**: قدم إجابات شاملة ومفصلة. لا تكتفِ بإجابات سطحية. استخدم الأرقام والمعطيات من التحليلات عند الإمكان.
2. **الهيكلة**: استخدم العناوين (##) والنقاط المرقمة والقوائم لتنظيم إجابتك.
3. **التحليل النقدي**: لا تكتفِ بتكرار ما في التحليلات. أضف رؤية نقدية، وربط بين النقاط، واقترح حلولاً عملية.
4. **السياق العربي**: خذ بعين الاعتبار طبيعة الأسواق العربية، الثقافة الاستهلاكية، والبيئة التنظيمية في المنطقة.
5. **اللغة**: أجب بالعربية الفصحى بأسلوب مهني واحترافي.
6. **الأمانة**: إذا كان السؤال خارج نطاق التحليلات المتوفرة، أشر إلى ذلك بوضوح وقدم رأياً عاماً مع التنبيه.
7. **المحادثة**: تذكّر سياق الأسئلة السابقة في هذه المحادثة وابنِ عليها.
8. **المصادر**: عند الاستشهاد بأي رقم أو إحصائية من بيانات السوق البحريني، اذكر صراحةً أن المصدر هو "بوابة البيانات المفتوحة البحرينية (data.gov.bh)"."""


@app.route('/ask-followup', methods=['POST'])
def ask_followup():
    data = request.get_json()
    question = data.get('question', '').strip()
    analysis_id = data.get('analysis_id')
    api_key = data.get('api_key', '').strip() or os.environ.get('OPENAI_API_KEY', '')
    conversation_history = data.get('conversation_history', [])
    provider = data.get('provider', 'openai').strip()
    model = data.get('model', '').strip()
    web_search_enabled = data.get('web_search', False)

    if not question or not analysis_id:
        return jsonify({'error': 'الرجاء إدخال السؤال'}), 400

    analysis = get_analysis(analysis_id)
    if not analysis:
        return jsonify({'error': 'التحليل غير موجود'}), 404

    try:
        context = _build_followup_context(analysis)

        # --- خطوة بحث الويب ---
        web_context = ""
        if web_search_enabled:
            logger.info(f"بحث الويب مفعّل للسؤال: {question[:80]}")
            idea_short = analysis['idea'][:100]
            search_query = f"{question} {idea_short} البحرين"
            search_results = search_web(search_query, max_results=5)
            # إذا لم تنجح المحاولة الأولى، نحاول بالفكرة الاستثمارية فقط
            if not search_results:
                logger.info("محاولة بحث ثانية بالفكرة الاستثمارية فقط...")
                search_results = search_web(f"{idea_short} البحرين", max_results=5)
            if search_results:
                web_context = f"""

═══ نتائج بحث الويب ═══
تم العثور على المعلومات التالية من الإنترنت بخصوص سؤال المستخدم:

{search_results}

═══ تعليمات استخدام نتائج البحث ═══
- استخدم هذه النتائج لدعم إجابتك بمعلومات حديثة وواقعية
- اذكر المصادر عند الاستشهاد بمعلومة من نتائج البحث
- لا تكتفِ بنقل النتائج حرفياً — حللها واربطها بسياق الفكرة الاستثمارية
- إذا تعارضت نتائج البحث مع التحليل الأصلي، وضّح ذلك للمستخدم
- أشر في بداية إجابتك أنك استعنت بنتائج بحث الويب
"""
                logger.info(f"تم إضافة نتائج بحث الويب إلى السياق ({len(web_context)} حرف)")
            else:
                logger.info("لم يتم العثور على نتائج بحث")

        messages = [{"role": "system", "content": context + web_context}]

        # إضافة تاريخ المحادثة (آخر 20 رسالة كحد أقصى)
        if conversation_history:
            for msg in conversation_history[-20:]:
                if msg.get('role') in ('user', 'assistant') and msg.get('content'):
                    messages.append({
                        "role": msg['role'],
                        "content": msg['content'][:2000]
                    })

        messages.append({"role": "user", "content": question})

        logger.info(f"📨 سؤال متابعة: {question[:100]}... | analysis_id={analysis_id} | history={len(conversation_history)} | web_search={web_search_enabled}")

        if provider == 'gemini':
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            system_prompt = messages[0]['content']
            gemini_model = genai.GenerativeModel(
                model or 'gemini-2.5-flash',
                system_instruction=system_prompt
            )
            gemini_history = []
            for msg in messages[1:]:  # skip system (now passed as system_instruction)
                role = 'user' if msg['role'] == 'user' else 'model'
                gemini_history.append({"role": role, "parts": [msg['content']]})
            chat = gemini_model.start_chat(history=gemini_history[:-1])
            gemini_resp = chat.send_message(
                gemini_history[-1]['parts'][0],
                generation_config=genai.types.GenerationConfig(max_output_tokens=4000)
            )
            answer = gemini_resp.text or "لم أتمكن من الإجابة"
        else:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model or 'gpt-5.2',
                messages=messages,
                max_completion_tokens=4000
            )
            answer = response.choices[0].message.content or "لم أتمكن من الإجابة"

        logger.info(f"✅ إجابة المتابعة: {len(answer)} حرف | web_search_used={bool(web_context)}")
        return jsonify({'answer': answer, 'web_search_used': bool(web_context)})

    except Exception as e:
        logger.error(f"❌ خطأ في سؤال المتابعة: {type(e).__name__}: {e}")
        logger.error(f"📋 التتبع:\n{traceback.format_exc()}")
        return jsonify({'answer': f"حدث خطأ: {type(e).__name__} - {str(e)}"})


@app.route('/export-pdf/<int:analysis_id>')
def export_pdf(analysis_id):
    analysis = get_analysis(analysis_id)
    if not analysis:
        return jsonify({'error': 'التحليل غير موجود'}), 404

    # Generate HTML report
    html = render_template('report.html', analysis=analysis)

    # Try weasyprint, fallback to simple HTML download
    try:
        from weasyprint import HTML
        import tempfile
        pdf_path = Path(tempfile.gettempdir()) / f"oracle_report_{analysis_id}.pdf"
        HTML(string=html).write_pdf(str(pdf_path))
        return send_file(str(pdf_path), as_attachment=True,
                        download_name=f'oracle_report_{analysis_id}.pdf',
                        mimetype='application/pdf')
    except ImportError:
        # Fallback: return HTML file for browser print
        return Response(html, mimetype='text/html', headers={
            'Content-Disposition': f'inline; filename=oracle_report_{analysis_id}.html'
        })


@app.route('/api-key/status')
def api_key_status():
    saved_key = os.environ.get('OPENAI_API_KEY', '')
    return jsonify({'saved': bool(saved_key)})


@app.route('/api-key/save', methods=['POST'])
def save_api_key():
    data = request.get_json()
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
    """قائمة القطاعات الاستثمارية المتاحة."""
    return jsonify({k: {"name_ar": v["name_ar"], "icon": v["icon"]} for k, v in SECTORS.items()})


@app.route('/api/market-needs/<sector>')
def market_needs_data(sector):
    """بيانات احتياج السوق لقطاع معين - مهيكلة للعرض المرئي."""
    data = bahrain_service.get_sector_data(sector)
    return jsonify(data)


@app.route('/api/analyze-market-needs', methods=['POST'])
def analyze_market_needs():
    """تحليل احتياج السوق بالذكاء الاصطناعي - يحلل البيانات ويقترح أنشطة استثمارية."""
    data = request.get_json()
    sector = data.get('sector', 'general').strip()
    budget = data.get('budget', '').strip()
    api_key = data.get('api_key', '').strip() or os.environ.get('OPENAI_API_KEY', '')
    provider = data.get('provider', 'openai').strip()
    model = data.get('model', '').strip()

    if not api_key:
        return jsonify({'error': 'الرجاء إدخال مفتاح API'}), 400

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
- يجب أن تكون جميع الأنشطة المقترحة قابلة للتنفيذ بميزانية لا تتجاوز {budget_formatted} د.ب
- لا تقترح أي مشروع يتطلب رأس مال أعلى من {budget_formatted} د.ب
- ركز على المشاريع الصغيرة والمتناهية الصغر إذا كانت الميزانية محدودة
- وضّح في investment_range أن التكلفة ضمن حدود الميزانية المتاحة
"""

        system_prompt = f"""أنت محلل استثماري استراتيجي متخصص في السوق البحريني. مهمتك تحليل بيانات السوق الحقيقية لقطاع "{sector_name}" وتحديد الاحتياجات والفرص الاستثمارية.

{market_context}
{budget_constraint}
بناءً على البيانات أعلاه، حلل القطاع وقدم توصيات استثمارية.

** مهم جداً: يجب أن ترد بصيغة JSON فقط بالهيكل التالي **
{{
  "sector_overview": "تحليل شامل للقطاع في فقرتين أو ثلاث، يتضمن الوضع الحالي والاتجاهات بناءً على الأرقام الفعلية",
  "opportunities": [
    {{"activity": "اسم النشاط الاستثماري", "why": "لماذا هذا النشاط مناسب - مع أرقام من البيانات", "potential": "عالي أو متوسط أو منخفض", "investment_range": "نطاق الاستثمار المتوقع بالدينار البحريني"}},
    ...5-8 أنشطة
  ],
  "gaps": ["فجوة سوقية 1 مع تفصيل", "فجوة 2", ...3-6 فجوات],
  "risks": ["مخاطرة 1 مع تفصيل", "مخاطرة 2", ...3-5 مخاطر],
  "recommendation": "التوصية الاستراتيجية النهائية في فقرة",
  "best_activity": "أفضل نشاط استثماري مقترح مع تبرير مختصر",
  "estimated_demand": "تقدير حجم الطلب في السوق البحريني لهذا القطاع"
}}

- opportunities يجب أن تحتوي 5-8 أنشطة
- potential يجب أن يكون: "عالي" أو "متوسط" أو "منخفض"
- استخدم الأرقام الحقيقية من البيانات المرفقة في تحليلك
- عند ذكر أي إحصائية، اذكر أن المصدر هو "بوابة البيانات المفتوحة البحرينية (data.gov.bh)"
- لا تضف أي نص خارج JSON"""

        budget_note = f" برأس مال لا يتجاوز {int(budget):,} دينار بحريني" if budget else ""
        user_message = f"حلل احتياج السوق البحريني في قطاع \"{sector_name}\" واقترح أنشطة استثمارية مناسبة{budget_note} بناءً على البيانات الاقتصادية الفعلية."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        import asyncio
        from agents.base import create_completion

        async def _run():
            return await create_completion(provider, model or 'gpt-5.2', api_key, messages, max_tokens=4000, temperature=0.6)

        content = asyncio.run(_run())

        try:
            result = json.loads(content)
            return jsonify({'analysis': result})
        except json.JSONDecodeError:
            return jsonify({'analysis': {'sector_overview': content, 'opportunities': [], 'gaps': [], 'risks': [], 'recommendation': '', 'best_activity': '', 'estimated_demand': ''}})

    except Exception as e:
        logger.error(f"❌ خطأ في تحليل احتياج السوق: {type(e).__name__}: {e}")
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
