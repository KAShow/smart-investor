"""Analysis-related endpoints: run, history, rate, share, export, followup."""
import logging

from flask import Blueprint, Response, g, jsonify, request

from auth import require_auth
from database import (delete_analysis, get_analysis, get_analysis_by_token,
                      get_dashboard_stats, list_analyses_for_user, rate_analysis)
from extensions import limiter
from services import stream_analysis
from services.followup_service import ask_followup as _ask_followup
from services.pdf_service import render_pdf
from utils.sanitize import sanitize_user_input

logger = logging.getLogger(__name__)
bp = Blueprint('analysis', __name__)


@bp.route('/health', methods=['GET'])
@limiter.exempt
def health():
    return jsonify({'status': 'ok'})


@bp.route('/analyze', methods=['POST'])
@require_auth
@limiter.limit('5/day', key_func=lambda: f'user:{g.get("user_id", "anon")}')
def analyze():
    """SSE streaming endpoint. Body: { sector, budget?, notes?, requester_* }"""
    data = request.get_json(silent=True) or {}
    sector = (data.get('sector') or '').strip()
    budget = (data.get('budget') or '').strip()
    notes = data.get('notes') or ''
    requester_name = sanitize_user_input(data.get('requester_name'), max_len=100)
    requester_email = sanitize_user_input(data.get('requester_email'), max_len=200)
    requester_company = sanitize_user_input(data.get('requester_company'), max_len=200)

    if not sector:
        return jsonify({'error': 'الرجاء اختيار القطاع'}), 400

    return Response(
        stream_analysis(
            sector=sector, budget=budget, notes=notes, user_id=g.user_id,
            requester_name=requester_name, requester_email=requester_email,
            requester_company=requester_company,
        ),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@bp.route('/analyses', methods=['GET'])
@require_auth
def list_my_analyses():
    return jsonify(list_analyses_for_user(g.user_id, limit=100))


@bp.route('/analyses/<int:analysis_id>', methods=['GET'])
@require_auth
def get_my_analysis(analysis_id):
    analysis = get_analysis(analysis_id, user_id=g.user_id)
    if not analysis:
        return jsonify({'error': 'التحليل غير موجود'}), 404
    return jsonify(analysis)


@bp.route('/analyses/<int:analysis_id>', methods=['DELETE'])
@require_auth
def delete_my_analysis(analysis_id):
    analysis = get_analysis(analysis_id, user_id=g.user_id)
    if not analysis:
        return jsonify({'error': 'التحليل غير موجود'}), 404
    delete_analysis(analysis_id, user_id=g.user_id)
    return jsonify({'success': True})


@bp.route('/analyses/<int:analysis_id>/rate', methods=['POST'])
@require_auth
def rate(analysis_id):
    data = request.get_json(silent=True) or {}
    rating = data.get('rating', 0)
    feedback = sanitize_user_input(data.get('feedback', ''), max_len=2000)
    if not isinstance(rating, int) or not 1 <= rating <= 5:
        return jsonify({'error': 'التقييم يجب أن يكون عدداً بين 1 و 5'}), 400
    analysis = get_analysis(analysis_id, user_id=g.user_id)
    if not analysis:
        return jsonify({'error': 'التحليل غير موجود'}), 404
    rate_analysis(analysis_id, rating, feedback, user_id=g.user_id)
    return jsonify({'success': True})


@bp.route('/share/<token>', methods=['GET'])
@limiter.limit('30/minute')
def shared_view(token):
    """Public read-only view of an analysis via share token. No auth required."""
    analysis = get_analysis_by_token(token)
    if not analysis:
        return jsonify({'error': 'الرابط غير موجود أو منتهي الصلاحية'}), 404
    public = {k: v for k, v in analysis.items()
              if k not in ('user_id', 'requester_email', 'requester_name', 'requester_company')}
    return jsonify(public)


@bp.route('/analyses/<int:analysis_id>/export-pdf', methods=['GET'])
@require_auth
def export_pdf(analysis_id):
    analysis = get_analysis(analysis_id, user_id=g.user_id)
    if not analysis:
        return jsonify({'error': 'التحليل غير موجود'}), 404
    pdf_bytes, html_fallback, filename = render_pdf(analysis)
    if pdf_bytes:
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename={filename}'},
        )
    return Response(
        html_fallback,
        mimetype='text/html',
        headers={'Content-Disposition': f'inline; filename={filename}.html'},
    )


@bp.route('/analyses/<int:analysis_id>/followup', methods=['POST'])
@require_auth
@limiter.limit('30/hour', key_func=lambda: f'user:{g.get("user_id", "anon")}')
def followup(analysis_id):
    analysis = get_analysis(analysis_id, user_id=g.user_id)
    if not analysis:
        return jsonify({'error': 'التحليل غير موجود'}), 404

    data = request.get_json(silent=True) or {}
    result = _ask_followup(
        analysis=analysis,
        question=data.get('question', ''),
        conversation_history=data.get('conversation_history') or [],
        web_search_enabled=bool(data.get('web_search', False)),
        model=data.get('model', ''),
    )
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@bp.route('/dashboard', methods=['GET'])
@require_auth
def dashboard():
    return jsonify(get_dashboard_stats(user_id=g.user_id))


@bp.route('/compare', methods=['GET'])
@require_auth
def compare():
    id1 = request.args.get('id1', type=int)
    id2 = request.args.get('id2', type=int)
    if not id1 or not id2:
        return jsonify({'error': 'يجب تحديد تحليلين للمقارنة'}), 400
    a1 = get_analysis(id1, user_id=g.user_id)
    a2 = get_analysis(id2, user_id=g.user_id)
    if not a1 or not a2:
        return jsonify({'error': 'أحد التحليلات غير موجود'}), 404
    return jsonify({'analysis1': a1, 'analysis2': a2})
