"""Orchestrates the multi-agent analysis pipeline and yields SSE events.

Extracted from app.py so blueprints can stay thin. The function returns a
generator suitable for `Response(generator, mimetype='text/event-stream')`.
"""
import asyncio
import json
import logging
import queue
import threading
import traceback

from agents import (ActionPlanAgent, BrokerageModelsAgent, CompetitiveAgent,
                    FinancialAgent, LegalAgent, MarketLogicAgent,
                    SwotAgent, SynthesizerAgent, TechnicalAgent)
from agents.competitor_enrichment import CompetitorEnrichment
from bahrain_data import BahrainDataService, get_sectors
from config import Config
from data_sources import DataAggregator
from data_sources.sijilat import SijilatSource
from database import get_analysis, save_analysis
from utils.sanitize import sanitize_user_input

logger = logging.getLogger(__name__)

# Singleton agent instances — reused across requests.
_market_agent = MarketLogicAgent()
_financial_agent = FinancialAgent()
_competitive_agent = CompetitiveAgent()
_legal_agent = LegalAgent()
_technical_agent = TechnicalAgent()
_brokerage_models_agent = BrokerageModelsAgent()
_synthesizer = SynthesizerAgent()
_swot_agent = SwotAgent()
_action_plan_agent = ActionPlanAgent()
_bahrain_service = BahrainDataService()
_data_aggregator = DataAggregator()


def _sse_event(event: str, data) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _empty_results():
    return {"title": "خطأ", "summary": "تعذّر إنتاج التحليل", "details": [], "score": 0, "recommendation": ""}


def stream_analysis(*, sector: str, budget: str, notes: str, user_id: str,
                    requester_name: str = '', requester_email: str = '',
                    requester_company: str = ''):
    """SSE generator for the full 6-agent + synthesizer + SWOT/action-plan pipeline.

    All AI calls use the server's PERPLEXITY_API_KEY (single shared key).
    """
    api_key = Config.PERPLEXITY_API_KEY
    provider = 'perplexity'
    model = Config.PERPLEXITY_DEFAULT_MODEL

    sectors = get_sectors()
    if sector not in sectors:
        yield _sse_event('error', {'error': 'القطاع المختار غير صالح'})
        return
    if not api_key:
        yield _sse_event('error', {'error': 'الخادم لم يُهيَّأ بمفتاح Perplexity'})
        return

    sector_name = sectors[sector]['name_ar']
    notes_clean = sanitize_user_input(notes, max_len=1500)
    idea = f"دراسة جدوى إنشاء شركة وساطة تجارية في قطاع {sector_name} في مملكة البحرين"
    if notes_clean:
        idea += f"\n\nملاحظات إضافية: {notes_clean}"

    market_context = _bahrain_service.build_market_context(sector=sector)
    if budget:
        try:
            budget_int = int(budget)
            budget_formatted = f"{budget_int:,}"
            market_context += (
                f"\n\n══ قيد رأس المال ══\n"
                f"** المستثمر يملك أقل من {budget_formatted} دينار بحريني **\n"
                f"- يجب أن يلتزم تحليلك بهذه الميزانية المحددة ({budget_formatted} د.ب)\n"
                f"- لا تقترح أي خطوة أو استثمار يتطلب رأس مال أعلى من {budget_formatted} د.ب\n"
                f"- اذكر تكاليف تقديرية واقعية بالدينار البحريني ضمن حدود الميزانية"
            )
        except (TypeError, ValueError):
            pass

    event_queue = queue.Queue()

    def run_pipeline():
        from concurrent.futures import ThreadPoolExecutor, as_completed

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            aggregated = loop.run_until_complete(_data_aggregator.fetch_all(sector))
        except Exception as e:
            logger.warning(f"Failed to fetch supplemental data: {e}")
            aggregated = {}
        finally:
            loop.close()

        try:
            sijilat_source = SijilatSource()
            competitors_raw = sijilat_source.get_competitors(sector)
            try:
                enrichment = CompetitorEnrichment()
                competitors_enriched = enrichment.enrich_batch(competitors_raw, sector, max_enrich=8)
            except Exception as e:
                logger.warning(f"Competitor enrichment failed: {e}")
                competitors_enriched = competitors_raw
        except Exception as e:
            logger.warning(f"Sijilat source failed: {e}")
            competitors_enriched = []

        event_queue.put(("competitors_found", {
            "count": len(competitors_enriched),
            "competitors": competitors_enriched,
        }))

        ctx_for = lambda role: market_context + _data_aggregator.build_agent_context(sector, role, aggregated)
        market_ctx = ctx_for("market")
        financial_ctx = ctx_for("financial")
        competitive_ctx = ctx_for("competitive")
        legal_ctx = ctx_for("legal")
        technical_ctx = ctx_for("technical")
        brokerage_ctx = ctx_for("brokerage_models")

        if competitors_enriched:
            comp_lines = ["\n\n══ بيانات المنافسين الفعليين من السجل التجاري ══"]
            for i, c in enumerate(competitors_enriched, 1):
                line = (f"{i}. {c.get('name_ar', '')} ({c.get('name_en', '')}) — "
                        f"{c.get('activity', '')} | تأسست: {c.get('established', '?')} | "
                        f"الحجم: {c.get('size', '?')} | المحافظة: {c.get('governorate', '?')} | "
                        f"النوع: {c.get('entity_type', '?')}")
                if c.get('website'):
                    line += f" | الموقع: {c['website']}"
                if c.get('web_description'):
                    line += f"\n   وصف: {c['web_description']}"
                comp_lines.append(line)
            competitive_ctx += "\n".join(comp_lines)

        attribution = _data_aggregator.build_data_attribution(aggregated)
        event_queue.put(("data_sources_used", attribution))

        agent_tasks = [
            ("market_analysis", _market_agent, market_ctx),
            ("financial_analysis", _financial_agent, financial_ctx),
            ("competitive_analysis", _competitive_agent, competitive_ctx),
            ("legal_analysis", _legal_agent, legal_ctx),
            ("technical_analysis", _technical_agent, technical_ctx),
            ("brokerage_models_analysis", _brokerage_models_agent, brokerage_ctx),
        ]

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(agent.analyze_sync, idea, api_key, provider, model, market_context=ctx): name
                for name, agent, ctx in agent_tasks
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    event_queue.put((name, result))
                except Exception as e:
                    logger.error(f"Agent {name} failed: {type(e).__name__}: {e}")
                    err_payload = dict(_empty_results(), summary=f"{type(e).__name__}: {e}")
                    event_queue.put((name, json.dumps(err_payload, ensure_ascii=False)))

        event_queue.put(("agents_done", None))

    pipeline_thread = threading.Thread(target=run_pipeline, daemon=True)
    pipeline_thread.start()

    results = {}
    waited = 0
    while True:
        try:
            name, data = event_queue.get(timeout=10)
            waited = 0
        except queue.Empty:
            yield ": heartbeat\n\n"
            waited += 10
            if waited >= Config.SSE_TIMEOUT_SECONDS:
                logger.error("Agent pipeline timed out")
                yield _sse_event('error', {'error': 'انتهت مهلة التحليل'})
                return
            continue

        if name == "agents_done":
            break
        if name in ("data_sources_used", "competitors_found"):
            yield _sse_event(name, data)
        else:
            results[name] = data
            yield _sse_event(name, {'content': data})

    # ── Synthesizer ──────────────────────────────────────────────────────
    yield _sse_event('synthesizing', {'status': 'started'})

    synth_queue = queue.Queue()

    def run_synthesizer():
        try:
            verdict = _synthesizer.synthesize_sync(
                idea=idea,
                market_analysis=results.get('market_analysis', ''),
                financial_analysis=results.get('financial_analysis', ''),
                competitive_analysis=results.get('competitive_analysis', ''),
                legal_analysis=results.get('legal_analysis', ''),
                technical_analysis=results.get('technical_analysis', ''),
                brokerage_models_analysis=results.get('brokerage_models_analysis', ''),
                api_key=api_key,
                provider=provider,
                model_override=model,
            )
            synth_queue.put(("ok", verdict))
        except Exception as e:
            logger.error(f"Synthesizer failed: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            synth_queue.put(("error", str(e)))

    threading.Thread(target=run_synthesizer, daemon=True).start()

    waited = 0
    status, verdict = "error", ""
    while True:
        try:
            status, verdict = synth_queue.get(timeout=10)
            break
        except queue.Empty:
            yield ": heartbeat\n\n"
            waited += 10
            if waited >= Config.SSE_TIMEOUT_SECONDS:
                logger.error("Synthesizer timed out")
                status, verdict = "error", "انتهت مهلة التجميع"
                break

    if status == "error":
        verdict = json.dumps({
            "summary": verdict, "consensus": [], "conflicts": [], "verdict": "خطأ",
            "overall_score": 0, "score_justification": "", "recommended_model": "",
            "model_justification": "", "advice": []
        }, ensure_ascii=False)

    yield _sse_event('final_verdict', {'content': verdict})

    # ── SWOT + Action Plan in parallel ───────────────────────────────────
    yield _sse_event('generating_extras', {'status': 'started'})

    extras_queue = queue.Queue()

    def run_extras():
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as executor:
            swot_future = executor.submit(
                _swot_agent.analyze_sync, idea, results, api_key,
                provider=provider, model_override=model
            )
            plan_future = executor.submit(
                _action_plan_agent.generate_sync, idea, results, verdict,
                api_key, provider=provider, model_override=model
            )
            try:
                swot_result = swot_future.result()
            except Exception:
                swot_result = json.dumps({
                    "strengths": [], "weaknesses": [], "opportunities": [], "threats": []
                }, ensure_ascii=False)
            try:
                plan_result = plan_future.result()
            except Exception:
                plan_result = json.dumps({
                    "executive_summary": "فشل إنشاء خطة العمل", "phases": [],
                    "total_budget": "", "key_metrics": [],
                    "critical_success_factors": [], "risk_mitigation": []
                }, ensure_ascii=False)
        extras_queue.put((swot_result, plan_result))

    threading.Thread(target=run_extras, daemon=True).start()

    waited = 0
    swot_result = plan_result = None
    while True:
        try:
            swot_result, plan_result = extras_queue.get(timeout=10)
            break
        except queue.Empty:
            yield ": heartbeat\n\n"
            waited += 10
            if waited >= Config.SSE_TIMEOUT_SECONDS:
                swot_result = json.dumps(
                    {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []},
                    ensure_ascii=False
                )
                plan_result = json.dumps(
                    {"executive_summary": "انتهت مهلة التحليل", "phases": [],
                     "total_budget": "", "key_metrics": [],
                     "critical_success_factors": [], "risk_mitigation": []},
                    ensure_ascii=False
                )
                break

    yield _sse_event('swot_analysis', {'content': swot_result})
    yield _sse_event('action_plan', {'content': plan_result})

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
        user_id=user_id,
        requester_name=requester_name,
        requester_email=requester_email,
        requester_company=requester_company,
    )

    analysis = get_analysis(analysis_id, user_id=user_id)
    yield _sse_event('done', {
        'status': 'completed',
        'analysis_id': analysis_id,
        'share_token': analysis.get('share_token', '') if analysis else '',
        'report_number': analysis.get('report_number', '') if analysis else '',
        'valid_until': analysis.get('valid_until', '') if analysis else '',
    })


def run_market_needs_analysis(*, sector: str, budget: str | None = None):
    """Run a one-shot market-needs analysis (synchronous, returns dict).

    Used by /api/analyze-market-needs.
    """
    from agents.base import create_completion

    sectors = get_sectors()
    if sector not in sectors:
        return {'error': 'الرجاء اختيار قطاع صالح'}

    api_key = Config.PERPLEXITY_API_KEY
    if not api_key:
        return {'error': 'الخادم لم يُهيَّأ بمفتاح Perplexity'}

    sector_data = _bahrain_service.get_sector_data(sector)
    market_context = _bahrain_service.build_market_context(sector=sector)
    sector_name = sector_data.get('sector_name', sector)
    brokerage_ctx = sectors.get(sector, {}).get('brokerage_context', '')

    budget_constraint = ""
    if budget:
        try:
            budget_int = int(budget)
            budget_formatted = f"{budget_int:,}"
            budget_constraint = (
                f"\n** قيد رأس المال: المستثمر يملك أقل من {budget_formatted} دينار بحريني **\n"
                f"- يجب أن تكون جميع نماذج الوساطة المقترحة قابلة للتنفيذ بميزانية لا تتجاوز {budget_formatted} د.ب\n"
            )
        except (TypeError, ValueError):
            pass

    system_prompt = f"""أنت محلل متخصص في الوساطة التجارية في السوق البحريني.
مهمتك: تحليل بيانات السوق لقطاع "{sector_name}" وتحديد فرص إنشاء شركة وساطة.
{brokerage_ctx}
{market_context}
{budget_constraint}

** الوساطة التجارية تعني: شركة/منصة تربط البائعين بالمشترين وتأخذ عمولة. **

ارد بصيغة JSON فقط:
{{
  "sector_overview": "...",
  "buyer_seller_map": [{{"sellers":"...", "buyers":"...", "transaction_type":"...", "estimated_volume":"...", "current_method":"..."}}],
  "brokerage_models": [{{"model_name":"...", "how_it_works":"...", "revenue_model":"...", "estimated_commission":"...", "potential":"عالي|متوسط|منخفض", "startup_cost":"..."}}],
  "gaps": ["..."],
  "risks": ["..."],
  "best_model": "...",
  "estimated_demand": "...",
  "recommendation": "..."
}}
- buyer_seller_map: 3-5 أزواج
- brokerage_models: 4-6 نماذج
- اذكر "بوابة البيانات المفتوحة البحرينية (data.gov.bh)" كمصدر للأرقام
- لا تضف أي نص خارج JSON"""

    budget_note = f" برأس مال لا يتجاوز {int(budget):,} دينار بحريني" if budget else ""
    user_message = (
        f"حلل فرص الوساطة التجارية في قطاع \"{sector_name}\" بالسوق البحريني: "
        f"من البائعون؟ من المشترون؟ ما أفضل نموذج وساطة؟{budget_note}"
    )

    try:
        content = asyncio.run(create_completion(
            provider='perplexity',
            model=Config.PERPLEXITY_DEFAULT_MODEL,
            api_key=api_key,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=4000,
            temperature=0.3,
        ))
    except Exception as e:
        logger.error(f"market-needs analysis failed: {e}")
        return {'error': f'حدث خطأ: {type(e).__name__}'}

    cleaned = content.strip()
    try:
        return {'analysis': json.loads(cleaned)}
    except json.JSONDecodeError:
        try:
            start = cleaned.index('{')
            end = cleaned.rindex('}') + 1
            return {'analysis': json.loads(cleaned[start:end])}
        except (json.JSONDecodeError, ValueError):
            logger.error(f"Could not parse JSON: {cleaned[:300]}")
            return {'analysis': {
                'sector_overview': content, 'buyer_seller_map': [], 'brokerage_models': [],
                'gaps': [], 'risks': [], 'recommendation': '', 'best_model': '', 'estimated_demand': ''
            }}


def stream_gap_analysis(*, sector: str):
    """SSE generator for gap analysis on a single sector."""
    from agents.gap_analyzer import GapAnalyzerAgent

    sectors = get_sectors()
    if sector not in sectors:
        yield _sse_event('error', {'message': f'قطاع غير معروف: {sector}'})
        return

    api_key = Config.PERPLEXITY_API_KEY
    if not api_key:
        yield _sse_event('error', {'message': 'الخادم لم يُهيَّأ بمفتاح Perplexity'})
        return

    sector_info = sectors[sector]
    event_queue = queue.Queue()

    def run_analysis():
        try:
            event_queue.put(('status', {'message': 'جاري جلب البيانات من المصادر...', 'step': 1}))
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            aggregator = DataAggregator()
            aggregated_data = loop.run_until_complete(aggregator.fetch_all(sector))
            loop.close()

            active = sum(1 for v in aggregated_data.values() if not v.get('error'))
            total_points = sum(v.get('data_points', 0) for v in aggregated_data.values() if not v.get('error'))
            event_queue.put(('data_collected', {
                'active_sources': active,
                'total_sources': len(aggregated_data),
                'total_data_points': total_points,
            }))

            event_queue.put(('status', {'message': 'جاري تحليل الفجوات والفرص...', 'step': 2}))
            context = aggregator.build_agent_context(sector, 'gap_analysis', aggregated_data)
            gap_agent = GapAnalyzerAgent()
            idea = f"تحليل فجوات السوق وفرص الوساطة التجارية في قطاع: {sector_info.get('name_ar', sector)}"
            if sector_info.get('brokerage_context'):
                idea += f"\n\nسياق الوساطة: {sector_info['brokerage_context']}"

            result = gap_agent.analyze_sync(
                idea=idea, market_context=context, provider='perplexity',
                api_key=api_key, model_override=Config.PERPLEXITY_DEFAULT_MODEL,
            )
            event_queue.put(('gap_result', {'content': result, 'sector': sector}))

            attribution = aggregator.build_data_attribution(aggregated_data)
            event_queue.put(('attribution', attribution))
            event_queue.put(('done', {'sector': sector}))
        except Exception as e:
            logger.error(f"Gap analysis failed: {e}\n{traceback.format_exc()}")
            event_queue.put(('error', {'message': str(e)}))

    threading.Thread(target=run_analysis, daemon=True).start()

    waited = 0
    while True:
        try:
            event_name, event_data = event_queue.get(timeout=10)
            waited = 0
            yield _sse_event(event_name, event_data)
            if event_name in ('done', 'error'):
                break
        except queue.Empty:
            yield ": heartbeat\n\n"
            waited += 10
            if waited >= Config.SSE_TIMEOUT_SECONDS:
                yield _sse_event('error', {'message': 'انتهت مهلة التحليل'})
                break
