"""Server-side PDF generation for analyses.

Uses weasyprint when available; falls back to a simple printable HTML
response that the browser can save as PDF (for environments where
weasyprint's native deps are missing).
"""
import io
import json
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_weasyprint_broken = False


def _section(title: str, body: str) -> str:
    return f"""
    <section class="section">
      <h2>{title}</h2>
      <div class="body">{body}</div>
    </section>
    """


def _stringify(json_str) -> str:
    if not json_str:
        return '<em>غير متوفر</em>'
    try:
        data = json.loads(json_str) if isinstance(json_str, str) else json_str
        if isinstance(data, dict):
            lines = []
            for k, v in data.items():
                if isinstance(v, list):
                    lines.append(f"<strong>{k}:</strong><ul>" +
                                 ''.join(f"<li>{item}</li>" for item in v) + "</ul>")
                else:
                    lines.append(f"<strong>{k}:</strong> {v}")
            return '<br>'.join(lines)
        return str(data)
    except (json.JSONDecodeError, TypeError):
        return str(json_str).replace('\n', '<br>')


def _build_html(analysis: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>تقرير دراسة الجدوى - {analysis.get('report_number', '')}</title>
<style>
  @page {{ size: A4; margin: 2cm; }}
  body {{ font-family: 'Tajawal', sans-serif; font-size: 11pt; color: #1f2937; line-height: 1.7; }}
  h1 {{ color: #0D47A1; border-bottom: 3px solid #1565C0; padding-bottom: 10px; }}
  h2 {{ color: #1565C0; margin-top: 20px; }}
  .meta {{ color: #6b7280; font-size: 9pt; margin-bottom: 20px; }}
  .section {{ margin-bottom: 24px; page-break-inside: avoid; }}
  .body {{ background: #f9fafb; padding: 12px; border-right: 4px solid #1565C0; border-radius: 4px; }}
  ul {{ padding-right: 24px; }}
</style>
</head>
<body>
  <h1>تقرير دراسة جدوى الوساطة التجارية</h1>
  <div class="meta">
    <strong>رقم التقرير:</strong> {analysis.get('report_number', '-')} |
    <strong>صادر بتاريخ:</strong> {analysis.get('created_at', '-')} |
    <strong>صالح حتى:</strong> {analysis.get('valid_until', '-')}
  </div>
  {_section('موضوع الدراسة', analysis.get('idea', ''))}
  {_section('الحكم النهائي', _stringify(analysis.get('final_verdict')))}
  {_section('تحليل السوق', _stringify(analysis.get('market_analysis')))}
  {_section('التحليل المالي', _stringify(analysis.get('financial_analysis')))}
  {_section('تحليل المنافسة', _stringify(analysis.get('competitive_analysis')))}
  {_section('التحليل القانوني', _stringify(analysis.get('legal_analysis')))}
  {_section('التحليل التقني', _stringify(analysis.get('technical_analysis')))}
  {_section('نماذج الوساطة', _stringify(analysis.get('brokerage_models_analysis')))}
  {_section('تحليل SWOT', _stringify(analysis.get('swot_analysis')))}
  {_section('خطة العمل', _stringify(analysis.get('action_plan')))}
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
        logger.warning(f"weasyprint unavailable ({type(e).__name__}); using HTML fallback")
        return None, html, filename
