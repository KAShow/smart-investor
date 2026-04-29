"""Reference data endpoints: sectors, market data, sources, companies, solutions."""
import asyncio
import logging
from datetime import datetime

from flask import Blueprint, Response, g, jsonify, request

from agents.base import PROVIDERS
from auth import require_auth
from bahrain_data import BahrainDataService, get_sectors, refresh_sectors_cache
from data_sources import DataAggregator
from extensions import limiter
from services import run_market_needs_analysis, stream_gap_analysis

logger = logging.getLogger(__name__)
bp = Blueprint('data', __name__)
_bahrain_service = BahrainDataService()
_aggregator = DataAggregator()


# ── Public reference endpoints ────────────────────────────────────────────
# These are read-only references. Auth is light because the data is not
# user-specific. Rate limited per IP to avoid scraping.

@bp.route('/sectors', methods=['GET'])
@limiter.limit('60/minute')
def sectors():
    return jsonify([
        {'value': key, 'name_ar': info['name_ar'], 'icon': info.get('icon', '📊')}
        for key, info in get_sectors().items()
    ])


@bp.route('/sectors/<sector>/market', methods=['GET'])
@limiter.limit('60/minute')
def sector_market(sector):
    return jsonify(_bahrain_service.get_sector_data(sector))


@bp.route('/data-sources/meta', methods=['GET'])
@limiter.limit('60/minute')
def data_sources_meta():
    return jsonify(_aggregator.get_sources_meta())


@bp.route('/data-sources/fetch', methods=['GET'])
@require_auth
@limiter.limit('20/hour', key_func=lambda: f'user:{g.get("user_id", "anon")}')
def data_sources_fetch():
    sector = (request.args.get('sector') or '').strip()
    sectors_map = get_sectors()
    if not sector or sector not in sectors_map:
        return jsonify({'error': 'الرجاء اختيار قطاع صالح'}), 400

    try:
        results = asyncio.run(_aggregator.fetch_all(sector))
    except Exception as e:
        logger.error(f"Data sources fetch error: {e}")
        return jsonify({'error': 'فشل جلب البيانات'}), 500

    meta = _aggregator.get_sources_meta()
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
        'sector_name_ar': sectors_map[sector]['name_ar'],
        'fetched_at': datetime.now().isoformat(),
        'total_data_points': total_points,
        'sources': sources_response,
    })


@bp.route('/providers', methods=['GET'])
@limiter.limit('60/minute')
def providers():
    return jsonify(PROVIDERS)


# ── Authenticated analytical endpoints ────────────────────────────────────

@bp.route('/analyze-market-needs', methods=['POST'])
@require_auth
@limiter.limit('10/day', key_func=lambda: f'user:{g.get("user_id", "anon")}')
def analyze_market_needs():
    data = request.get_json(silent=True) or {}
    sector = (data.get('sector') or '').strip()
    budget = (data.get('budget') or '').strip() or None
    if not sector:
        return jsonify({'error': 'الرجاء اختيار قطاع'}), 400

    result = run_market_needs_analysis(sector=sector, budget=budget)
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@bp.route('/gap-analysis', methods=['POST'])
@require_auth
@limiter.limit('5/day', key_func=lambda: f'user:{g.get("user_id", "anon")}')
def gap_analysis():
    """Streams the gap analysis directly (no two-step token handoff)."""
    data = request.get_json(silent=True) or {}
    sector = (data.get('sector') or '').strip()
    if not sector:
        return jsonify({'error': 'الرجاء اختيار قطاع'}), 400

    return Response(
        stream_gap_analysis(sector=sector),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


# ── Static reference data (companies & solutions) ─────────────────────────

@bp.route('/companies', methods=['GET'])
@limiter.limit('60/minute')
def companies():
    from .reference_data import BAHRAIN_COMPANIES
    return jsonify(BAHRAIN_COMPANIES)


@bp.route('/solutions', methods=['GET'])
@limiter.limit('60/minute')
def solutions():
    from .reference_data import UNIVERSAL_SOLUTIONS, SECTOR_SOLUTIONS
    return jsonify({'universal': UNIVERSAL_SOLUTIONS, 'sector': SECTOR_SOLUTIONS})
