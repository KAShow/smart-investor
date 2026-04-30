"""Direct API test client for Smart Investor — bypasses any frontend.

Reads a Supabase JWT from --jwt or SMART_INVESTOR_JWT env var, runs a full
analysis via SSE, prints progress with `rich` formatting, and saves each
agent's output to `test_outputs/<run-id>/` for offline reading.

Usage:
  .venv/Scripts/python.exe test_analyze.py --sector food
  .venv/Scripts/python.exe test_analyze.py --sector food --budget 25000 --notes "..."
  .venv/Scripts/python.exe test_analyze.py --list-sectors
  .venv/Scripts/python.exe test_analyze.py --analysis-id 1   # fetch existing

JWT can be obtained once from any logged-in browser session:
  DevTools → Console → run:
    JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k=>k.includes('auth-token')))).access_token
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.json import JSON
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

load_dotenv()

API_BASE = os.getenv('SMART_INVESTOR_API', 'https://smart-investor-api-szvb.onrender.com')
console = Console()

AGENT_LABELS = {
    'market_analysis': 'تحليل الطلب والسوق',
    'financial_analysis': 'التحليل المالي',
    'competitive_analysis': 'تحليل المنافسة',
    'legal_analysis': 'التحليل القانوني',
    'technical_analysis': 'التحليل التقني',
    'brokerage_models_analysis': 'نماذج الوساطة',
    'final_verdict': 'الحكم النهائي',
    'swot_analysis': 'تحليل SWOT',
    'action_plan': 'خطة العمل',
}


def get_jwt() -> str:
    jwt = os.environ.get('SMART_INVESTOR_JWT', '').strip()
    if not jwt:
        console.print("[red]✗ JWT غير موجود[/red]")
        console.print("ضعه في .env كـ [cyan]SMART_INVESTOR_JWT=...[/cyan] أو مرّره عبر [cyan]--jwt[/cyan]")
        console.print("\nللحصول على JWT من المتصفح:")
        console.print("  1. سجّل دخولك في hawsh-khalifa.lovable.app")
        console.print("  2. افتح DevTools → Console")
        console.print("  3. شغّل:")
        console.print("     [cyan]JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k=>k.includes('auth-token')))).access_token[/cyan]")
        sys.exit(1)
    return jwt


def list_sectors():
    r = requests.get(f'{API_BASE}/api/sectors', timeout=30)
    r.raise_for_status()
    sectors = r.json()
    table = Table(title=f"القطاعات المتاحة ({len(sectors)})")
    table.add_column("القيمة", style="cyan")
    table.add_column("الاسم", style="white")
    table.add_column("الأيقونة")
    for s in sectors:
        table.add_row(s['value'], s['name_ar'], s.get('icon', ''))
    console.print(table)


def parse_sse_chunk(chunk: str):
    event = 'message'
    data = ''
    for line in chunk.split('\n'):
        if line.startswith(':'):
            continue
        if line.startswith('event:'):
            event = line[6:].strip()
        elif line.startswith('data:'):
            data += line[5:].strip()
    if not data:
        return None
    try:
        return event, json.loads(data)
    except json.JSONDecodeError:
        return event, data


def render_agent(name: str, content: str, out_dir: Path):
    label = AGENT_LABELS.get(name, name)
    out_file = out_dir / f"{name}.md"

    parsed = None
    if isinstance(content, str):
        s = content.strip()
        if s.startswith('{') or s.startswith('['):
            try:
                parsed = json.loads(s)
            except json.JSONDecodeError:
                pass

    if parsed is not None:
        out_file = out_dir / f"{name}.json"
        out_file.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding='utf-8')
        console.print(Panel(JSON.from_data(parsed), title=f"📋 {label}", border_style="green"))
    else:
        text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, indent=2)
        out_file.write_text(text, encoding='utf-8')
        console.print(Panel(Markdown(text), title=f"📋 {label}", border_style="cyan"))

    console.print(f"  💾 محفوظ: [dim]{out_file}[/dim]\n")


def run_analysis(sector: str, budget: str, notes: str, jwt: str) -> dict | None:
    out_dir = Path('test_outputs') / datetime.now().strftime('%Y%m%d-%H%M%S')
    out_dir.mkdir(parents=True, exist_ok=True)
    console.rule(f"[bold]تحليل قطاع: {sector}[/bold]")
    console.print(f"📁 ملفات الإخراج: [cyan]{out_dir}[/cyan]\n")

    body = {'sector': sector, 'budget': budget, 'notes': notes}
    headers = {
        'Authorization': f'Bearer {jwt}',
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
    }

    started = time.time()
    completed_stages: set[str] = set()
    done_event = None

    with requests.post(
        f'{API_BASE}/api/analyze',
        json=body,
        headers=headers,
        stream=True,
        timeout=600,
    ) as resp:
        if resp.status_code != 200:
            console.print(f"[red]✗ فشل بدء التحليل ({resp.status_code})[/red]")
            try:
                console.print_json(data=resp.json())
            except Exception:
                console.print(resp.text[:500])
            return None

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=False,
        ) as progress:
            task = progress.add_task("جاري...", total=None)
            buffer = ''
            for chunk_bytes in resp.iter_content(chunk_size=None):
                if not chunk_bytes:
                    continue
                buffer += chunk_bytes.decode('utf-8', errors='replace')
                while '\n\n' in buffer:
                    part, buffer = buffer.split('\n\n', 1)
                    if not part.strip():
                        continue
                    parsed = parse_sse_chunk(part)
                    if not parsed:
                        continue
                    event, data = parsed

                    if event == 'done':
                        done_event = data
                        progress.update(task, description="✅ اكتمل")
                        break
                    if event == 'error':
                        msg = data.get('error') if isinstance(data, dict) else str(data)
                        console.print(f"\n[red]✗ {msg}[/red]")
                        return None

                    completed_stages.add(event)
                    elapsed = int(time.time() - started)
                    label = AGENT_LABELS.get(event, event)
                    progress.update(task, description=f"[{elapsed}s] {label} ({len(completed_stages)})")

                    # Save reportable events as we receive them
                    if event in AGENT_LABELS and isinstance(data, dict) and 'content' in data:
                        progress.stop()
                        render_agent(event, data['content'], out_dir)
                        progress.start()

                if done_event:
                    break

    elapsed = int(time.time() - started)
    console.rule(f"[bold green]انتهى في {elapsed}s[/bold green]")
    if done_event:
        console.print(Panel(JSON.from_data(done_event), title="🎉 done", border_style="green"))
        (out_dir / 'meta.json').write_text(
            json.dumps({**done_event, 'sector': sector, 'elapsed_s': elapsed},
                       ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
    return done_event


def fetch_existing(analysis_id: int, jwt: str):
    r = requests.get(
        f'{API_BASE}/api/analyses/{analysis_id}',
        headers={'Authorization': f'Bearer {jwt}'},
        timeout=30,
    )
    if r.status_code != 200:
        console.print(f"[red]✗ {r.status_code}: {r.text[:300]}[/red]")
        return
    data = r.json()
    out_dir = Path('test_outputs') / f"analysis-{analysis_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"📁 [cyan]{out_dir}[/cyan]\n")
    for key in AGENT_LABELS:
        if key in data and data[key]:
            render_agent(key, data[key], out_dir)
    (out_dir / 'meta.json').write_text(
        json.dumps({k: v for k, v in data.items() if k not in AGENT_LABELS},
                   ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


def main():
    p = argparse.ArgumentParser(description='Smart Investor direct API tester')
    p.add_argument('--sector', help='sector value (e.g. food, education)')
    p.add_argument('--budget', default='', help='optional budget in BHD')
    p.add_argument('--notes', default='', help='optional notes')
    p.add_argument('--jwt', help='Supabase JWT (or set SMART_INVESTOR_JWT in .env)')
    p.add_argument('--list-sectors', action='store_true', help='list available sectors and exit')
    p.add_argument('--analysis-id', type=int, help='fetch existing analysis by id')
    p.add_argument('--api-base', default=None, help='API base URL override')
    args = p.parse_args()

    if args.api_base:
        global API_BASE
        API_BASE = args.api_base.rstrip('/')

    if args.jwt:
        os.environ['SMART_INVESTOR_JWT'] = args.jwt

    if args.list_sectors:
        list_sectors()
        return

    if args.analysis_id:
        fetch_existing(args.analysis_id, get_jwt())
        return

    if not args.sector:
        console.print("[yellow]الرجاء تحديد --sector أو --list-sectors أو --analysis-id[/yellow]")
        list_sectors()
        return

    run_analysis(args.sector, args.budget, args.notes, get_jwt())


if __name__ == '__main__':
    main()
