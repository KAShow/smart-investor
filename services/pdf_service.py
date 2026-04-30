"""Server-side PDF generation for analyses.

Renders the same visual language as the front-end detail view:
- Hero banner with gradient and SVG score circle
- Final verdict card with weighted-breakdown table and structured sections
- SWOT 2x2 color grid
- Action plan numbered timeline
- Agent reports with score-tinted left edge and [DATA]/[ESTIMATE]/[ASSUMPTION]/
  [UNKNOWN] inline pills

Falls back to a printable HTML response if weasyprint native libs are missing.
"""
import html as html_lib
import io
import json
import logging
import math
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
_MARKER_RE = re.compile(r'\[(DATA|ESTIMATE|ASSUMPTION|UNKNOWN)(?::[^\]]*)?\]', re.IGNORECASE)
_MARKER_LABELS = {
    'DATA': 'بيانات',
    'ESTIMATE': 'تقدير',
    'ASSUMPTION': 'افتراض',
    'UNKNOWN': 'مجهول',
}

DIM_LABELS = {
    'market_demand': 'الطلب والسوق',
    'financial': 'الجدوى المالية',
    'competition': 'المنافسة',
    'legal': 'القانوني والتنظيمي',
    'technical': 'الجدوى التقنية',
    'brokerage_model': 'نموذج الوساطة',
}


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


def _replace_markers(html: str) -> str:
    """Wrap [DATA]/[ESTIMATE]/[ASSUMPTION]/[UNKNOWN] tokens in styled pills.
    Runs on already-rendered HTML so it survives Markdown."""
    def repl(m):
        kind = m.group(1).upper()
        label = _MARKER_LABELS.get(kind, kind)
        return f'<span class="marker marker-{kind.lower()}">{label}</span>'
    return _MARKER_RE.sub(repl, html)


def _render_markdown(text: str) -> str:
    """Render markdown and apply marker pill replacement. Extracts [SCORE:N]
    prefix into a separate badge."""
    if not text:
        return '<p class="muted">لا يوجد محتوى.</p>'
    score = None
    m = _SCORE_PREFIX_RE.search(text)
    if m:
        score = m.group(1)
        text = _SCORE_PREFIX_RE.sub('', text, count=1)
    body_html = _md.render(text)
    body_html = _replace_markers(body_html)
    if score is not None:
        return f'<div class="score-badge">الدرجة {_esc(score)}/10</div>{body_html}'
    return body_html


def _score_color(score) -> str:
    try:
        s = float(score)
    except (TypeError, ValueError):
        return '#9ca3af'
    if s >= 7:
        return '#10b981'
    if s >= 5:
        return '#f59e0b'
    return '#ef4444'


def _score_circle_svg(score, size: int = 110, label: str = '') -> str:
    """SVG circular score gauge that renders cleanly in weasyprint."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return ''
    s = max(0.0, min(s, 10.0))
    color = _score_color(s)
    stroke = 8
    radius = (size - stroke) / 2
    cx = cy = size / 2
    circumference = 2 * math.pi * radius
    offset = circumference - (s / 10.0) * circumference
    score_text = f'{s:g}'
    sub = f'<div class="score-circle-sub">{_esc(label)}</div>' if label else ''
    return f'''
    <div class="score-circle-wrap">
      <div class="score-circle" style="width:{size}px;height:{size}px">
        <svg width="{size}" height="{size}" style="transform:rotate(-90deg)">
          <circle cx="{cx}" cy="{cy}" r="{radius}" stroke="#e5e7eb" stroke-width="{stroke}" fill="none"/>
          <circle cx="{cx}" cy="{cy}" r="{radius}" stroke="{color}" stroke-width="{stroke}"
                  stroke-dasharray="{circumference:.2f}" stroke-dashoffset="{offset:.2f}"
                  stroke-linecap="round" fill="none"/>
        </svg>
        <div class="score-circle-text" style="color:{color}">
          {score_text}<span class="score-circle-max">/10</span>
        </div>
      </div>
      {sub}
    </div>
    '''


def _verdict_tone_class(verdict: str, score) -> str:
    if not verdict and score is None:
        return 'tone-neutral'
    try:
        s = float(score) if score is not None else None
    except (TypeError, ValueError):
        s = None
    if s is not None:
        if s >= 7:
            return 'tone-good'
        if s >= 5:
            return 'tone-warn'
        return 'tone-bad'
    if verdict and 'مثالي' in verdict or 'واعدة' in verdict:
        return 'tone-good'
    if verdict and 'غير مناسب' in verdict:
        return 'tone-bad'
    return 'tone-neutral'


def _hero(analysis: dict, verdict: dict | None) -> str:
    idea = analysis.get('idea', '')
    sector = analysis.get('sector', '')
    report_no = analysis.get('report_number', '-')
    created = analysis.get('created_at', '-')
    valid = analysis.get('valid_until', '-')

    score = (verdict or {}).get('overall_score')
    confidence = (verdict or {}).get('overall_confidence')
    verdict_text = (verdict or {}).get('verdict', '')

    tone = _verdict_tone_class(verdict_text, score)
    score_html = _score_circle_svg(score, size=110, label='التقييم الإجمالي') if score else ''
    confidence_pill = (
        f'<span class="meta-pill meta-pill-outline">الثقة {_esc(confidence)}/10</span>'
        if confidence else ''
    )

    return f'''
    <section class="hero">
      <div class="hero-top">
        <div class="hero-meta">
          <span class="meta-pill meta-pill-{tone}">{_esc(verdict_text or "تقرير دراسة جدوى")}</span>
          <span class="meta-pill meta-pill-secondary">{_esc(sector)}</span>
        </div>
        {score_html}
      </div>
      <h1 class="hero-title">{_esc(idea)}</h1>
      <div class="hero-meta-row">
        <span>📄 {_esc(report_no)}</span>
        <span>📅 {_esc(created)}</span>
        <span>⏱ صالح حتى {_esc(valid)}</span>
        {confidence_pill}
      </div>
    </section>
    '''


def _render_swot(swot: dict) -> str:
    def items(key):
        arr = swot.get(key) or []
        if not arr:
            return '<li class="muted">—</li>'
        out = []
        for it in arr:
            if isinstance(it, dict):
                txt = it.get('point') or it.get('title') or json.dumps(it, ensure_ascii=False)
            else:
                txt = it
            out.append(f'<li>{_replace_markers(_esc(txt))}</li>')
        return ''.join(out)

    return f'''
    <div class="swot-grid">
      <div class="swot-cell s">
        <h4>🛡️ نقاط القوة</h4>
        <ul>{items('strengths')}</ul>
      </div>
      <div class="swot-cell w">
        <h4>⚠️ نقاط الضعف</h4>
        <ul>{items('weaknesses')}</ul>
      </div>
      <div class="swot-cell o">
        <h4>💡 الفرص</h4>
        <ul>{items('opportunities')}</ul>
      </div>
      <div class="swot-cell t">
        <h4>⚔️ التهديدات</h4>
        <ul>{items('threats')}</ul>
      </div>
    </div>
    '''


def _render_action_plan(plan: dict) -> str:
    parts = []
    if plan.get('executive_summary'):
        parts.append(
            f'<div class="exec-summary"><strong>الملخص التنفيذي: </strong>'
            f'{_replace_markers(_esc(plan["executive_summary"]))}</div>'
        )
    if plan.get('total_budget'):
        parts.append(f'<div class="budget-pill">💰 الميزانية: {_esc(plan["total_budget"])}</div>')

    phases = plan.get('phases') or []
    if phases:
        parts.append('<h4 class="section-h">مراحل التنفيذ</h4>')
        parts.append('<ol class="timeline">')
        for i, ph in enumerate(phases, 1):
            name = ph.get('name', f'مرحلة {i}')
            duration = ph.get('duration') or ''
            tasks = ph.get('tasks') or []
            duration_chip = (
                f'<span class="phase-duration">⏱ {_esc(duration)}</span>' if duration else ''
            )
            tasks_html = ''.join(
                f'<li><span class="check">✓</span>{_replace_markers(_esc(t))}</li>' for t in tasks
            ) if tasks else '<li class="muted">لا توجد مهام محددة</li>'
            parts.append(
                f'<li class="phase-item">'
                f'<span class="phase-num">{i}</span>'
                f'<div class="phase-card">'
                f'<div class="phase-head"><strong>{_esc(name)}</strong>{duration_chip}</div>'
                f'<ul class="phase-tasks">{tasks_html}</ul>'
                f'</div></li>'
            )
        parts.append('</ol>')

    triple_blocks = []
    for label, key, variant, icon in [
        ('مؤشرات النجاح', 'key_metrics', 'success', '📈'),
        ('عوامل النجاح الحرجة', 'critical_success_factors', 'info', '🎯'),
        ('تخفيف المخاطر', 'risk_mitigation', 'warning', '⚠️'),
    ]:
        arr = plan.get(key) or []
        if arr:
            items_html = ''.join(f'<li>{_replace_markers(_esc(x))}</li>' for x in arr)
            triple_blocks.append(
                f'<div class="block block-{variant}">'
                f'<h4>{icon} {label}</h4>'
                f'<ul>{items_html}</ul>'
                f'</div>'
            )
    if triple_blocks:
        parts.append(f'<div class="triple-grid">{"".join(triple_blocks)}</div>')

    return '\n'.join(parts) or '<p class="muted">لا توجد بيانات.</p>'


def _render_verdict(verdict: dict) -> str:
    parts = []

    summary = verdict.get('summary')
    if isinstance(summary, str):
        nested = _try_json(summary)
        if isinstance(nested, dict):
            verdict = {**nested, **{k: v for k, v in verdict.items() if k != 'summary'}}
            summary = verdict.get('summary')

    score = verdict.get('overall_score')
    confidence = verdict.get('overall_confidence')
    verdict_text = verdict.get('verdict')

    summary_html = ''
    if summary and isinstance(summary, str):
        summary_html = f'<p>{_replace_markers(_esc(summary))}</p>'

    if score or verdict_text:
        score_html = _score_circle_svg(score, size=100, label='') if score else ''
        confidence_pill = (
            f'<span class="meta-pill meta-pill-outline">الثقة {_esc(confidence)}/10</span>'
            if confidence else ''
        )
        verdict_pill = (
            f'<span class="meta-pill meta-pill-{_verdict_tone_class(verdict_text, score)}">'
            f'{_esc(verdict_text)}</span>'
            if verdict_text else ''
        )
        parts.append(
            f'<div class="verdict-banner">'
            f'<div class="verdict-banner-text">'
            f'{verdict_pill}'
            f'{summary_html}'
            f'{confidence_pill}'
            f'</div>'
            f'{score_html}'
            f'</div>'
        )
    elif summary_html:
        parts.append(summary_html)

    if verdict.get('recommended_model'):
        model_just_html = ''
        if verdict.get('model_justification'):
            model_just_html = (
                f'<p class="rec-model-just">'
                f'{_replace_markers(_esc(verdict["model_justification"]))}</p>'
            )
        parts.append(
            f'<div class="rec-model">'
            f'<h4>📊 النموذج الموصى به</h4>'
            f'<p class="rec-model-name">{_esc(verdict["recommended_model"])}</p>'
            f'{model_just_html}'
            f'</div>'
        )

    if verdict.get('score_justification'):
        parts.append(
            f'<div class="callout"><strong>تبرير التقييم: </strong>'
            f'{_replace_markers(_esc(verdict["score_justification"]))}</div>'
        )

    consensus = verdict.get('consensus') or []
    advice = verdict.get('advice') or []
    pair_blocks = []
    if consensus:
        pair_blocks.append(
            '<div class="block block-success"><h4>🤝 إجماع المحلّلين</h4><ul>'
            + ''.join(f'<li>{_replace_markers(_esc(c))}</li>' for c in consensus)
            + '</ul></div>'
        )
    if advice:
        pair_blocks.append(
            '<div class="block block-info"><h4>💬 نصائح عملية</h4><ul>'
            + ''.join(f'<li>{_replace_markers(_esc(a))}</li>' for a in advice)
            + '</ul></div>'
        )
    if pair_blocks:
        parts.append(f'<div class="pair-grid">{"".join(pair_blocks)}</div>')

    breakdown = verdict.get('weighted_breakdown') or {}
    if isinstance(breakdown, dict) and breakdown:
        rows = []
        for key, dim in breakdown.items():
            if not isinstance(dim, dict):
                continue
            sc = dim.get('score', '—')
            sc_color = _score_color(sc) if sc != '—' else '#9ca3af'
            rows.append(
                f'<tr>'
                f'<td>{_esc(DIM_LABELS.get(key, key))}</td>'
                f'<td><span class="dim-score" style="background:{sc_color}1a;color:{sc_color}">{_esc(sc)}/10</span></td>'
                f'<td>{_esc(dim.get("weight", "—"))}</td>'
                f'<td>{_esc(dim.get("confidence", "—"))}</td>'
                f'</tr>'
            )
        if rows:
            parts.append(
                '<h4 class="section-h">التقييم المرجَّح حسب البُعد</h4>'
                '<table class="dim-table"><thead><tr>'
                '<th>البُعد</th><th>الدرجة</th><th>الوزن</th><th>الثقة</th>'
                '</tr></thead>'
                f'<tbody>{"".join(rows)}</tbody></table>'
            )
            justifications = []
            for key, dim in breakdown.items():
                if isinstance(dim, dict) and dim.get('justification'):
                    justifications.append(
                        f'<div class="dim-just"><strong>{_esc(DIM_LABELS.get(key, key))}: </strong>'
                        f'{_replace_markers(_esc(dim["justification"]))}</div>'
                    )
            if justifications:
                parts.append(f'<div class="dim-justs">{"".join(justifications)}</div>')

    inconsistencies = verdict.get('numerical_inconsistencies') or []
    if inconsistencies:
        parts.append('<h4 class="section-h">⚖️ تناقضات رقمية تم حسمها</h4>')
        for inc in inconsistencies:
            if not isinstance(inc, dict):
                continue
            adopted = (
                f'<div><span class="muted">المعتمد: </span><strong>{_esc(inc.get("adopted_value", ""))}</strong></div>'
                if inc.get('adopted_value') else ''
            )
            parts.append(
                f'<div class="conflict">'
                f'<strong>{_esc(inc.get("field", "—"))}</strong>'
                f'<div><span class="muted">القيم المُبلَّغة: </span>{_replace_markers(_esc(inc.get("values_reported", "")))}</div>'
                f'<div><span class="muted">الحسم: </span>{_replace_markers(_esc(inc.get("resolution", "")))}</div>'
                f'{adopted}'
                f'</div>'
            )

    misleading = verdict.get('misleading_citations') or []
    if misleading:
        parts.append('<h4 class="section-h">⚠️ استشهادات مضلِّلة مرصودة</h4>')
        for m in misleading:
            if not isinstance(m, dict):
                continue
            citation_html = ''
            if m.get('citation'):
                citation_html = (
                    f'<p class="italic">«{_replace_markers(_esc(m["citation"]))}»</p>'
                )
            issue_html = ''
            if m.get('issue'):
                issue_html = (
                    f'<div><span class="muted">المشكلة: </span>'
                    f'{_replace_markers(_esc(m["issue"]))}</div>'
                )
            parts.append(
                f'<div class="conflict warn">'
                f'<strong>{_esc(m.get("agent", "—"))}</strong>'
                f'{citation_html}'
                f'{issue_html}'
                f'</div>'
            )

    conflicts = verdict.get('conflicts') or verdict.get('contradictions_found') or []
    if conflicts:
        parts.append('<h4 class="section-h">التناقضات بين الوكلاء</h4>')
        for i, c in enumerate(conflicts, 1):
            if not isinstance(c, dict):
                parts.append(f'<div class="conflict">{_esc(c)}</div>')
                continue
            agents = c.get('agents') or []
            head = ' ↔ '.join(agents) if agents else f'تناقض {i}'
            resolution_html = (
                f'<div class="resolution"><strong>الحل: </strong>{_replace_markers(_esc(c["resolution"]))}</div>'
                if c.get('resolution') else ''
            )
            description_html = (
                f'<div><span class="muted">الوصف: </span>{_replace_markers(_esc(c["description"]))}</div>'
                if c.get('description') else ''
            )
            parts.append(
                f'<div class="conflict">'
                f'<strong>{_esc(head)}</strong>'
                f'{description_html}'
                f'{resolution_html}'
                f'</div>'
            )

    if verdict.get('critical_data_gaps'):
        parts.append(
            '<div class="block block-danger"><h4>🔍 فجوات بيانات حرجة</h4><ul>'
            + ''.join(f'<li>{_replace_markers(_esc(g))}</li>' for g in verdict['critical_data_gaps'])
            + '</ul></div>'
        )

    if verdict.get('advisor_opinion'):
        parts.append(
            f'<div class="advisor"><h4>💼 رأي المستشار</h4>'
            f'<p>{_replace_markers(_esc(verdict["advisor_opinion"]))}</p></div>'
        )

    return '\n'.join(parts) or '<p class="muted">لا توجد بيانات.</p>'


def _render_section(title: str, body_html: str, anchor: str = '') -> str:
    return (
        f'<section class="section" id="{_esc(anchor)}">'
        f'<h2>{_esc(title)}</h2>'
        f'<div class="body">{body_html}</div>'
        f'</section>'
    )


def _render_field(value, kind: str = 'markdown') -> str:
    if not value:
        return '<p class="muted">غير متوفر.</p>'
    if kind == 'markdown':
        parsed = _try_json(value)
        if isinstance(parsed, dict):
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


def _agent_section(title: str, content: str, anchor: str) -> str:
    """Agent report with score-tinted left edge."""
    if not content:
        return _render_section(title, '<p class="muted">غير متوفر.</p>', anchor)
    score = None
    m = _SCORE_PREFIX_RE.search(content)
    if m:
        score = float(m.group(1))
    edge_color = _score_color(score) if score is not None else '#cbd5e1'
    score_pill = (
        f'<span class="agent-score" style="background:{edge_color}1a;color:{edge_color}">{score:g}/10</span>'
        if score is not None else ''
    )
    body = _render_markdown(content)
    return f'''
    <section class="section agent-section" id="{_esc(anchor)}" style="border-right-color:{edge_color}">
      <div class="agent-head">
        <h2>{_esc(title)}</h2>
        {score_pill}
      </div>
      <div class="body">{body}</div>
    </section>
    '''


def _build_html(analysis: dict) -> str:
    verdict = _try_json(analysis.get('final_verdict'))
    verdict = verdict if isinstance(verdict, dict) else None

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>تقرير دراسة الجدوى - {_esc(analysis.get('report_number', ''))}</title>
<style>
  @page {{
    size: A4;
    margin: 1.6cm 1.4cm 2cm;
    @bottom-center {{
      content: "صفحة " counter(page) " من " counter(pages);
      color: #6b7280;
      font-size: 8.5pt;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'Tajawal', 'Segoe UI', 'Tahoma', sans-serif;
    font-size: 10.5pt;
    color: #1f2937;
    line-height: 1.75;
    margin: 0;
  }}
  h1 {{ color: #0D47A1; font-size: 22pt; margin: 0 0 6px; }}
  h2 {{
    color: #1565C0;
    margin: 0 0 14px;
    font-size: 14pt;
    border-right: 5px solid #1565C0;
    padding-right: 12px;
  }}
  h3 {{ color: #1f2937; margin: 16px 0 6px; font-size: 12pt; }}
  h4 {{ color: #374151; margin: 10px 0 6px; font-size: 11pt; }}
  p {{ margin: 6px 0; }}
  ul, ol {{ padding-right: 22px; margin: 6px 0; }}
  li {{ margin: 4px 0; }}
  .muted {{ color: #9ca3af; font-style: italic; }}
  .italic {{ font-style: italic; }}
  .section-h {{ font-weight: 600; font-size: 11.5pt; margin: 14px 0 8px; color: #374151; }}

  /* HERO */
  .hero {{
    background: linear-gradient(225deg, rgba(13, 71, 161, 0.10) 0%, rgba(21, 101, 192, 0.04) 50%, transparent 100%);
    border: 2px solid rgba(21, 101, 192, 0.25);
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 22px;
    page-break-inside: avoid;
  }}
  .hero-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    margin-bottom: 12px;
  }}
  .hero-meta {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  .hero-title {{ font-size: 17pt; font-weight: 700; line-height: 1.6; margin: 8px 0 12px; color: #0f172a; }}
  .hero-meta-row {{
    display: flex; gap: 16px; flex-wrap: wrap;
    font-size: 9pt; color: #64748b;
    padding-top: 10px; border-top: 1px dashed #cbd5e1;
  }}

  /* META PILLS */
  .meta-pill {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 9pt;
    font-weight: 600;
    border: 1px solid transparent;
  }}
  .meta-pill-tone-good {{ background: #d1fae5; color: #065f46; border-color: #6ee7b7; }}
  .meta-pill-tone-warn {{ background: #fef3c7; color: #92400e; border-color: #fcd34d; }}
  .meta-pill-tone-bad {{ background: #fee2e2; color: #991b1b; border-color: #fca5a5; }}
  .meta-pill-tone-neutral {{ background: #f1f5f9; color: #334155; border-color: #cbd5e1; }}
  .meta-pill-secondary {{ background: #e0e7ff; color: #3730a3; }}
  .meta-pill-outline {{ background: transparent; border-color: #cbd5e1; color: #475569; }}

  /* SCORE CIRCLE */
  .score-circle-wrap {{ display: inline-flex; flex-direction: column; align-items: center; gap: 4px; }}
  .score-circle {{ position: relative; }}
  .score-circle svg {{ display: block; }}
  .score-circle-text {{
    position: absolute; inset: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 24pt; font-weight: 700;
  }}
  .score-circle-max {{ font-size: 11pt; color: #94a3b8; font-weight: 400; margin-bottom: 4px; }}
  .score-circle-sub {{ font-size: 8.5pt; color: #64748b; }}

  /* SECTIONS */
  .section {{ margin-bottom: 18px; page-break-inside: avoid; }}
  .body {{
    background: #f9fafb;
    padding: 14px 18px;
    border-radius: 8px;
    border: 1px solid #f1f5f9;
  }}

  /* AGENT SECTIONS */
  .agent-section {{
    background: #f9fafb;
    border-right: 5px solid #cbd5e1;
    border-radius: 0 8px 8px 0;
    padding: 14px 18px 14px 18px;
  }}
  .agent-section .body {{ background: transparent; padding: 0; border: 0; }}
  .agent-head {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 10px; }}
  .agent-head h2 {{ border: 0; padding: 0; margin: 0; font-size: 13pt; }}
  .agent-score {{
    display: inline-block; padding: 3px 10px;
    border-radius: 999px; font-size: 10pt; font-weight: 700;
  }}

  /* SCORE BADGE (markdown prefix) */
  .score-badge {{
    display: inline-block; background: #1565C0; color: #fff;
    padding: 3px 12px; border-radius: 999px;
    font-size: 9pt; font-weight: 700; margin-bottom: 10px;
  }}

  /* MARKERS (inline pills inside text) */
  .marker {{
    display: inline-block;
    padding: 1px 7px;
    border-radius: 4px;
    font-size: 8pt;
    font-weight: 700;
    margin: 0 2px;
    border: 1px solid;
    vertical-align: 1pt;
  }}
  .marker-data {{ background: #d1fae5; color: #065f46; border-color: #6ee7b7; }}
  .marker-estimate {{ background: #fef3c7; color: #92400e; border-color: #fcd34d; }}
  .marker-assumption {{ background: #ffedd5; color: #9a3412; border-color: #fdba74; }}
  .marker-unknown {{ background: #fee2e2; color: #991b1b; border-color: #fca5a5; }}

  /* VERDICT BANNER */
  .verdict-banner {{
    display: flex; gap: 16px;
    background: linear-gradient(135deg, rgba(21, 101, 192, 0.08), rgba(21, 101, 192, 0.02));
    border: 1px solid rgba(21, 101, 192, 0.2);
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 14px;
    page-break-inside: avoid;
  }}
  .verdict-banner-text {{ flex: 1; }}
  .verdict-banner-text p {{ margin-top: 8px; font-size: 10pt; line-height: 1.7; }}

  /* RECOMMENDED MODEL */
  .rec-model {{
    background: linear-gradient(225deg, rgba(13, 71, 161, 0.10), rgba(13, 71, 161, 0.02));
    border: 2px solid rgba(13, 71, 161, 0.25);
    border-radius: 10px;
    padding: 14px 18px;
    margin: 14px 0;
    page-break-inside: avoid;
  }}
  .rec-model h4 {{ color: #0D47A1; margin: 0 0 6px; font-size: 11pt; }}
  .rec-model-name {{ font-size: 12.5pt; font-weight: 700; margin: 4px 0; color: #0f172a; }}
  .rec-model-just {{ font-size: 9.5pt; color: #475569; line-height: 1.65; margin-top: 6px; }}

  /* CALLOUT */
  .callout {{
    border-right: 4px solid #94a3b8;
    background: #f8fafc;
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 10pt;
    line-height: 1.65;
    margin: 10px 0;
  }}

  /* PAIR GRID (consensus + advice) */
  .pair-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0; }}

  /* TRIPLE GRID (metrics + factors + risks) */
  .triple-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin: 14px 0; }}

  /* COLORED BLOCKS */
  .block {{
    border: 1px solid #e5e7eb;
    border-right: 4px solid;
    border-radius: 6px;
    padding: 10px 12px;
    background: #fff;
  }}
  .block h4 {{ margin: 0 0 6px; font-size: 10pt; }}
  .block ul {{ margin: 0; padding-right: 18px; }}
  .block li {{ font-size: 9.5pt; }}
  .block-success {{ border-right-color: #10b981; background: #ecfdf5; }}
  .block-info {{ border-right-color: #0ea5e9; background: #eff6ff; }}
  .block-warning {{ border-right-color: #f59e0b; background: #fffbeb; }}
  .block-danger {{ border-right-color: #ef4444; background: #fef2f2; }}

  /* DIM TABLE */
  .dim-table {{ width: 100%; border-collapse: collapse; font-size: 9.5pt; }}
  .dim-table th, .dim-table td {{ border: 1px solid #e2e8f0; padding: 6px 10px; text-align: right; }}
  .dim-table th {{ background: #f1f5f9; font-weight: 600; }}
  .dim-score {{ display: inline-block; padding: 2px 8px; border-radius: 6px; font-weight: 700; font-size: 9pt; }}
  .dim-justs {{ margin-top: 8px; }}
  .dim-just {{ font-size: 9.5pt; color: #475569; padding: 4px 0; }}

  /* CONFLICTS */
  .conflict {{
    background: #fff;
    border: 1px solid #e5e7eb;
    border-right: 3px solid #94a3b8;
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-size: 10pt;
  }}
  .conflict.warn {{ background: #fffbeb; border-right-color: #f59e0b; }}
  .conflict strong {{ display: block; margin-bottom: 4px; }}
  .conflict .resolution {{
    background: #eff6ff;
    border-right: 3px solid #1565C0;
    padding: 6px 10px; margin-top: 6px; border-radius: 4px;
  }}

  /* SWOT */
  .swot-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .swot-cell {{ padding: 12px 14px; border-radius: 8px; border: 1.5px solid; }}
  .swot-cell.s {{ background: #ecfdf5; border-color: #10b981; }}
  .swot-cell.w {{ background: #fef2f2; border-color: #ef4444; }}
  .swot-cell.o {{ background: #eff6ff; border-color: #0ea5e9; }}
  .swot-cell.t {{ background: #fffbeb; border-color: #f59e0b; }}
  .swot-cell h4 {{ margin: 0 0 8px; font-size: 10.5pt; }}
  .swot-cell.s h4 {{ color: #047857; }}
  .swot-cell.w h4 {{ color: #b91c1c; }}
  .swot-cell.o h4 {{ color: #0369a1; }}
  .swot-cell.t h4 {{ color: #b45309; }}
  .swot-cell ul {{ margin: 0; padding-right: 18px; }}
  .swot-cell li {{ font-size: 9.5pt; }}

  /* TIMELINE */
  .exec-summary {{
    background: #f1f5f9;
    border-right: 4px solid #64748b;
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 10pt;
    margin-bottom: 10px;
  }}
  .budget-pill {{
    display: inline-block;
    background: #fff7ed; color: #9a3412;
    border: 1px solid #fed7aa;
    padding: 4px 12px; border-radius: 999px;
    font-size: 9.5pt; font-weight: 600;
    margin: 6px 0 12px;
  }}
  .timeline {{
    list-style: none;
    padding: 0; margin: 6px 16px 0 0;
    border-right: 2px solid rgba(21, 101, 192, 0.25);
  }}
  .phase-item {{
    position: relative;
    padding-right: 22px;
    margin-bottom: 12px;
    page-break-inside: avoid;
  }}
  .phase-num {{
    position: absolute;
    right: -16px; top: 0;
    width: 28px; height: 28px;
    border-radius: 50%;
    background: #1565C0;
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 10pt;
    box-shadow: 0 0 0 4px #fff;
  }}
  .phase-card {{
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 10px 14px;
  }}
  .phase-head {{ display: flex; justify-content: space-between; gap: 8px; margin-bottom: 6px; }}
  .phase-duration {{
    background: #f1f5f9; color: #475569;
    padding: 2px 8px; border-radius: 999px;
    font-size: 8.5pt;
  }}
  .phase-tasks {{ margin: 4px 0 0; padding: 0; list-style: none; }}
  .phase-tasks li {{ font-size: 9.5pt; padding-right: 18px; position: relative; line-height: 1.65; }}
  .check {{
    position: absolute; right: 0; top: 4px;
    color: #1565C0; font-weight: 700;
  }}

  /* ADVISOR QUOTE */
  .advisor {{
    background: linear-gradient(225deg, rgba(13, 71, 161, 0.08), rgba(13, 71, 161, 0.02));
    border: 2px solid rgba(13, 71, 161, 0.25);
    border-radius: 10px;
    padding: 14px 18px;
    margin: 14px 0;
    page-break-inside: avoid;
  }}
  .advisor h4 {{ color: #0D47A1; margin: 0 0 8px; font-size: 11pt; }}
  .advisor p {{ font-size: 10pt; line-height: 1.85; white-space: pre-line; margin: 0; }}

  /* META */
  .meta {{ color: #6b7280; font-size: 9pt; margin-bottom: 18px; }}
</style>
</head>
<body>
  {_hero(analysis, verdict)}

  {_render_section('موضوع الدراسة', f'<p>{_esc(analysis.get("idea", ""))}</p>', 'idea')}
  {_render_section('الحكم النهائي', _render_field(analysis.get('final_verdict'), 'verdict'), 'verdict')}
  {_agent_section('تحليل السوق والطلب', analysis.get('market_analysis', ''), 'market')}
  {_agent_section('التحليل المالي', analysis.get('financial_analysis', ''), 'financial')}
  {_agent_section('تحليل المنافسة', analysis.get('competitive_analysis', ''), 'competitive')}
  {_agent_section('التحليل القانوني', analysis.get('legal_analysis', ''), 'legal')}
  {_agent_section('التحليل التقني', analysis.get('technical_analysis', ''), 'technical')}
  {_agent_section('نماذج الوساطة', analysis.get('brokerage_models_analysis', ''), 'brokerage')}
  {_render_section('تحليل SWOT', _render_field(analysis.get('swot_analysis'), 'swot'), 'swot')}
  {_render_section('خطة العمل', _render_field(analysis.get('action_plan'), 'plan'), 'plan')}
</body>
</html>"""


def render_pdf(analysis: dict) -> tuple[bytes | None, str | None, str]:
    """Returns (pdf_bytes, html_fallback, filename)."""
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
