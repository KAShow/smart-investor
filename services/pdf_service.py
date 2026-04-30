"""Server-side PDF generation for analyses.

Renders agent outputs (Markdown) and synthesizer outputs (JSON) into a
properly-formatted A4 report. Falls back to a printable HTML response if
weasyprint native deps are missing on the host.
"""
import html as html_lib
import io
import json
import logging
import re
import tempfile
from pathlib import Path

from markdown_it import MarkdownIt

logger = logging.getLogger(__name__)

_md = MarkdownIt('commonmark', {'html': False, 'linkify': True, 'typographer': False})
_md.enable('table')
_md.enable('strikethrough')

_weasyprint_broken = False
_SCORE_PREFIX_RE = re.compile(r'^\s*\[SCORE:\s*(\d+(?:\.\d+)?)\]\s*\n?', re.MULTILINE)


def _esc(s) -> str:
    return html_lib.escape(str(s) if s is not None else '')


def _strip_fence(text: str) -> str:
    s = (text or '').strip()
    m = re.match(r'^```(?:json)?\s*([\s\S]*?)\s*```$', s, re.IGNORECASE)
    return m.group(1).strip() if m else s


def _try_json(text):
    if text is None:
        return None
    if isinstance(text, (dict, list)):
        return text
    if not isinstance(text, str):
        return None
    s = _strip_fence(text)
    if not (s.startswith('{') or s.startswith('[')):
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


def _render_markdown(text: str) -> str:
    """Render markdown to HTML with score badge if present."""
    if not text:
        return '<p class="muted">لا يوجد محتوى.</p>'
    score = None
    score_match = _SCORE_PREFIX_RE.search(text)
    if score_match:
        score = score_match.group(1)
        text = _SCORE_PREFIX_RE.sub('', text, count=1)
    body_html = _md.render(text)
    if score is not None:
        return f'<div class="score-badge">الدرجة: {_esc(score)}/10</div>{body_html}'
    return body_html


def _render_swot(swot: dict) -> str:
    def items(key):
        arr = swot.get(key) or []
        if not arr:
            return '<li class="muted">—</li>'
        out = []
        for it in arr:
            if isinstance(it, dict):
                txt = it.get('point') or it.get('title') or json.dumps(it, ensure_ascii=False)
                out.append(f'<li>{_esc(txt)}</li>')
            else:
                out.append(f'<li>{_esc(it)}</li>')
        return ''.join(out)

    return f'''
    <div class="swot-grid">
      <div class="swot-cell s"><h4>نقاط القوة (Strengths)</h4><ul>{items('strengths')}</ul></div>
      <div class="swot-cell w"><h4>نقاط الضعف (Weaknesses)</h4><ul>{items('weaknesses')}</ul></div>
      <div class="swot-cell o"><h4>الفرص (Opportunities)</h4><ul>{items('opportunities')}</ul></div>
      <div class="swot-cell t"><h4>التهديدات (Threats)</h4><ul>{items('threats')}</ul></div>
    </div>
    '''


def _render_action_plan(plan: dict) -> str:
    parts = []
    if plan.get('executive_summary'):
        parts.append(f'<p><strong>الملخص التنفيذي:</strong> {_esc(plan["executive_summary"])}</p>')
    if plan.get('total_budget'):
        parts.append(f'<p><strong>إجمالي الميزانية:</strong> {_esc(plan["total_budget"])}</p>')

    phases = plan.get('phases') or []
    if phases:
        parts.append('<h4>المراحل</h4>')
        for i, ph in enumerate(phases, 1):
            name = ph.get('name', f'مرحلة {i}')
            duration = ph.get('duration') or ''
            tasks = ph.get('tasks') or []
            tasks_html = ''.join(f'<li>{_esc(t)}</li>' for t in tasks) if tasks else '<li class="muted">—</li>'
            parts.append(
                f'<div class="phase"><strong>{_esc(name)}</strong>'
                f'{f" — <em>{_esc(duration)}</em>" if duration else ""}'
                f'<ul>{tasks_html}</ul></div>'
            )

    for label, key in [
        ('مؤشرات النجاح', 'key_metrics'),
        ('عوامل النجاح الحرجة', 'critical_success_factors'),
        ('تخفيف المخاطر', 'risk_mitigation'),
    ]:
        arr = plan.get(key) or []
        if arr:
            items_html = ''.join(f'<li>{_esc(x)}</li>' for x in arr)
            parts.append(f'<h4>{label}</h4><ul>{items_html}</ul>')

    return '\n'.join(parts) or '<p class="muted">لا توجد بيانات.</p>'


def _render_verdict(verdict: dict) -> str:
    parts = []

    summary = verdict.get('summary')
    # Sometimes the synth wraps the whole JSON in `summary`; unwrap if so.
    if isinstance(summary, str):
        nested = _try_json(summary)
        if isinstance(nested, dict):
            verdict = {**nested, **{k: v for k, v in verdict.items() if k != 'summary'}}
            summary = verdict.get('summary')

    if verdict.get('verdict') or verdict.get('overall_score') is not None:
        score = verdict.get('overall_score')
        confidence = verdict.get('overall_confidence')
        verdict_text = verdict.get('verdict') or '—'
        score_html = f' · <strong>الدرجة:</strong> {_esc(score)}/10' if score not in (None, 0, '0') else ''
        conf_html = f' · <strong>الثقة:</strong> {_esc(confidence)}/10' if confidence not in (None, 0, '0') else ''
        parts.append(f'<div class="verdict-banner"><strong>الحكم:</strong> {_esc(verdict_text)}{score_html}{conf_html}</div>')

    if summary and isinstance(summary, str):
        parts.append(f'<p>{_esc(summary)}</p>')

    if verdict.get('score_justification'):
        parts.append(f'<p><strong>تبرير التقييم:</strong> {_esc(verdict["score_justification"])}</p>')

    if verdict.get('recommended_model'):
        parts.append(f'<p><strong>النموذج الموصى به:</strong> {_esc(verdict["recommended_model"])}</p>')
    if verdict.get('model_justification'):
        parts.append(f'<p>{_esc(verdict["model_justification"])}</p>')

    for label, key in [
        ('إجماع المحلّلين', 'consensus'),
        ('نصائح عملية', 'advice'),
        ('فجوات بيانات حرجة', 'critical_data_gaps'),
    ]:
        arr = verdict.get(key) or []
        if arr:
            items_html = ''.join(f'<li>{_esc(x)}</li>' for x in arr)
            parts.append(f'<h4>{label}</h4><ul>{items_html}</ul>')

    breakdown = verdict.get('weighted_breakdown') or {}
    if isinstance(breakdown, dict) and breakdown:
        labels = {
            'market_demand': 'الطلب والسوق',
            'financial': 'الجدوى المالية',
            'competition': 'المنافسة',
            'legal': 'القانوني والتنظيمي',
            'technical': 'الجدوى التقنية',
            'brokerage_model': 'نموذج الوساطة',
        }
        rows = []
        for key, dim in breakdown.items():
            if not isinstance(dim, dict):
                continue
            rows.append(
                f'<tr><td>{_esc(labels.get(key, key))}</td>'
                f'<td>{_esc(dim.get("score", "—"))}/10</td>'
                f'<td>{_esc(dim.get("weight", "—"))}</td>'
                f'<td>{_esc(dim.get("confidence", "—"))}</td></tr>'
            )
        if rows:
            parts.append(
                '<h4>التقييم المرجَّح حسب البُعد</h4>'
                '<table><thead><tr><th>البُعد</th><th>الدرجة</th><th>الوزن</th><th>الثقة</th></tr></thead>'
                f'<tbody>{"".join(rows)}</tbody></table>'
            )

    conflicts = verdict.get('conflicts') or verdict.get('contradictions_found') or []
    if conflicts:
        parts.append('<h4>التناقضات بين الوكلاء</h4>')
        for i, c in enumerate(conflicts, 1):
            if not isinstance(c, dict):
                parts.append(f'<div class="conflict">{_esc(c)}</div>')
                continue
            agents = c.get('agents') or []
            head = ' ↔ '.join(agents) if agents else f'تناقض {i}'
            parts.append(f'<div class="conflict"><strong>{_esc(head)}</strong>')
            if c.get('description'):
                parts.append(f'<p><em>الوصف:</em> {_esc(c["description"])}</p>')
            if c.get('resolution'):
                parts.append(f'<p><em>الحل:</em> {_esc(c["resolution"])}</p>')
            parts.append('</div>')

    inconsistencies = verdict.get('numerical_inconsistencies') or []
    if inconsistencies:
        parts.append('<h4>تناقضات رقمية بين الوكلاء — تم حسمها</h4>')
        for inc in inconsistencies:
            if not isinstance(inc, dict):
                continue
            parts.append(
                f'<div class="conflict">'
                f'<strong>{_esc(inc.get("field", "—"))}</strong>'
                f'<p><em>القيم المُبلَّغة:</em> {_esc(inc.get("values_reported", ""))}</p>'
                f'<p><em>الحسم:</em> {_esc(inc.get("resolution", ""))}</p>'
                f'<p><em>القيمة المعتمدة:</em> <strong>{_esc(inc.get("adopted_value", ""))}</strong></p>'
                f'</div>'
            )

    misleading = verdict.get('misleading_citations') or []
    if misleading:
        parts.append('<h4>⚠️ استشهادات مضللة (تم رصدها للشفافية)</h4>')
        for m in misleading:
            if not isinstance(m, dict):
                continue
            parts.append(
                f'<div class="conflict">'
                f'<strong>{_esc(m.get("agent", "—"))}</strong>'
                f'<p>«{_esc(m.get("citation", ""))}»</p>'
                f'<p><em>المشكلة:</em> {_esc(m.get("issue", ""))}</p>'
                f'</div>'
            )

    if verdict.get('advisor_opinion'):
        parts.append(f'<blockquote>{_esc(verdict["advisor_opinion"])}</blockquote>')

    return '\n'.join(parts) or '<p class="muted">لا توجد بيانات.</p>'


def _render_section(title: str, body_html: str) -> str:
    return f'<section class="section"><h2>{_esc(title)}</h2><div class="body">{body_html}</div></section>'


def _render_field(value, kind: str = 'markdown') -> str:
    """Render a stored analysis field. kind: markdown | swot | plan | verdict."""
    if not value:
        return '<p class="muted">غير متوفر.</p>'
    if kind == 'markdown':
        parsed = _try_json(value)
        if isinstance(parsed, dict):
            # Some agents may emit JSON; render key/value table-ish.
            rows = ''.join(
                f'<tr><th>{_esc(k)}</th><td>{_esc(v) if not isinstance(v, list) else "<ul>"+"".join(f"<li>{_esc(i)}</li>" for i in v)+"</ul>"}</td></tr>'
                for k, v in parsed.items()
            )
            return f'<table>{rows}</table>'
        return _render_markdown(str(value))
    parsed = _try_json(value) if isinstance(value, str) else value
    if not isinstance(parsed, dict):
        return _render_markdown(str(value))
    if kind == 'swot':
        return _render_swot(parsed)
    if kind == 'plan':
        return _render_action_plan(parsed)
    if kind == 'verdict':
        return _render_verdict(parsed)
    return _render_markdown(str(value))


def _build_html(analysis: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>تقرير دراسة الجدوى - {_esc(analysis.get('report_number', ''))}</title>
<style>
  @page {{ size: A4; margin: 1.8cm; @bottom-center {{ content: "صفحة " counter(page) " من " counter(pages); color: #6b7280; font-size: 9pt; }} }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Tajawal', 'Segoe UI', 'Tahoma', sans-serif; font-size: 11pt; color: #1f2937; line-height: 1.7; }}
  h1 {{ color: #0D47A1; border-bottom: 3px solid #1565C0; padding-bottom: 10px; font-size: 20pt; margin-bottom: 8px; }}
  h2 {{ color: #1565C0; margin: 0 0 12px; font-size: 14pt; border-right: 4px solid #1565C0; padding-right: 12px; }}
  h3 {{ color: #1f2937; margin: 14px 0 6px; font-size: 12pt; }}
  h4 {{ color: #374151; margin: 12px 0 6px; font-size: 11pt; }}
  p {{ margin: 6px 0; }}
  ul, ol {{ padding-right: 20px; margin: 6px 0; }}
  li {{ margin: 3px 0; }}
  .meta {{ color: #6b7280; font-size: 9pt; margin-bottom: 24px; padding-bottom: 12px; border-bottom: 1px dashed #d1d5db; }}
  .section {{ margin-bottom: 22px; page-break-inside: avoid; }}
  .body {{ background: #f9fafb; padding: 14px 18px; border-radius: 6px; }}
  .muted {{ color: #9ca3af; font-style: italic; }}
  .score-badge {{ display: inline-block; background: #1565C0; color: #fff; padding: 3px 10px; border-radius: 12px; font-size: 9pt; font-weight: bold; margin-bottom: 8px; }}
  .verdict-banner {{ background: #E3F2FD; border: 1px solid #1565C0; padding: 10px 14px; border-radius: 6px; margin-bottom: 12px; }}
  blockquote {{ border-right: 4px solid #1565C0; background: #f3f4f6; padding: 10px 14px; margin: 10px 0; font-style: italic; }}
  table {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 10pt; }}
  th, td {{ border: 1px solid #d1d5db; padding: 6px 10px; text-align: right; }}
  th {{ background: #f3f4f6; font-weight: bold; }}
  .swot-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .swot-cell {{ padding: 10px; border-radius: 6px; }}
  .swot-cell.s {{ background: #ecfdf5; border: 1px solid #10b981; }}
  .swot-cell.w {{ background: #fef2f2; border: 1px solid #ef4444; }}
  .swot-cell.o {{ background: #eff6ff; border: 1px solid #3b82f6; }}
  .swot-cell.t {{ background: #fffbeb; border: 1px solid #f59e0b; }}
  .swot-cell h4 {{ margin: 0 0 6px; font-size: 10pt; }}
  .phase {{ background: #fff; border: 1px solid #e5e7eb; padding: 8px 12px; border-radius: 4px; margin-bottom: 8px; }}
  .conflict {{ background: #fffbeb; padding: 8px 12px; border-radius: 4px; margin-bottom: 6px; border-right: 3px solid #f59e0b; }}
</style>
</head>
<body>
  <h1>تقرير دراسة جدوى الوساطة التجارية</h1>
  <div class="meta">
    <strong>رقم التقرير:</strong> {_esc(analysis.get('report_number', '-'))} ·
    <strong>صادر بتاريخ:</strong> {_esc(analysis.get('created_at', '-'))} ·
    <strong>صالح حتى:</strong> {_esc(analysis.get('valid_until', '-'))}
  </div>
  {_render_section('موضوع الدراسة', f'<p>{_esc(analysis.get("idea", ""))}</p>')}
  {_render_section('الحكم النهائي', _render_field(analysis.get('final_verdict'), 'verdict'))}
  {_render_section('تحليل السوق والطلب', _render_field(analysis.get('market_analysis')))}
  {_render_section('التحليل المالي', _render_field(analysis.get('financial_analysis')))}
  {_render_section('تحليل المنافسة', _render_field(analysis.get('competitive_analysis')))}
  {_render_section('التحليل القانوني', _render_field(analysis.get('legal_analysis')))}
  {_render_section('التحليل التقني', _render_field(analysis.get('technical_analysis')))}
  {_render_section('نماذج الوساطة', _render_field(analysis.get('brokerage_models_analysis')))}
  {_render_section('تحليل SWOT', _render_field(analysis.get('swot_analysis'), 'swot'))}
  {_render_section('خطة العمل', _render_field(analysis.get('action_plan'), 'plan'))}
</body>
</html>"""


def render_pdf(analysis: dict) -> tuple[bytes | None, str | None, str]:
    """Returns (pdf_bytes, html_fallback, filename).

    If weasyprint succeeds → (bytes, None, filename). If not → (None, html, filename).
    """
    global _weasyprint_broken
    report_num = analysis.get('report_number', f"report_{analysis.get('id', 'unknown')}")
    filename = f"BSI_{report_num}.pdf"
    html = _build_html(analysis)

    if _weasyprint_broken:
        return None, html, filename

    try:
        import contextlib
        with contextlib.redirect_stderr(io.StringIO()):
            from weasyprint import HTML as WeasyHTML
        pdf_path = Path(tempfile.gettempdir()) / filename
        WeasyHTML(string=html).write_pdf(str(pdf_path))
        pdf_bytes = pdf_path.read_bytes()
        try:
            pdf_path.unlink(missing_ok=True)
        except Exception:
            pass
        return pdf_bytes, None, filename
    except Exception as e:
        _weasyprint_broken = True
        logger.warning(f"weasyprint unavailable ({type(e).__name__}: {e}); using HTML fallback")
        return None, html, filename
