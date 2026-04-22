import typer
import anthropic
import requests
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
import config

app = typer.Typer()
console = Console()

def get_meta_data():
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    start_date_prev = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    end_date_prev = (datetime.now() - timedelta(days=8)).strftime('%Y-%m-%d')

    def fetch(since, until):
        url = f"https://graph.facebook.com/v18.0/{config.META_AD_ACCOUNT_ID}/insights"
        params = {
            'access_token': config.META_ACCESS_TOKEN,
            'fields': 'spend,actions,clicks,impressions',
            'time_range': f'{{"since":"{since}","until":"{until}"}}',
            'level': 'account'
        }
        r = requests.get(url, params=params).json()
        if 'error' in r or not r.get('data'):
            return None
        item = r['data'][0]
        spend = float(item.get('spend', 0))
        clicks = int(item.get('clicks', 0))
        impressions = int(item.get('impressions', 0))
        conversions = sum(
            int(float(a['value'])) for a in item.get('actions', [])
            if a['action_type'] in ['purchase', 'lead', 'complete_registration']
        )
        cpa = spend / conversions if conversions > 0 else 0
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        roas = 0
        return {'spend': spend, 'conversions': conversions, 'cpa': cpa, 'ctr': ctr, 'roas': roas}

    current = fetch(start_date, end_date)
    previous = fetch(start_date_prev, end_date_prev)
    if current and previous:
        current['prev_cpa'] = previous['cpa']
        current['prev_conversions'] = previous['conversions']
    return current

def cpa_status(cpa, prev_cpa):
    if prev_cpa == 0:
        return "🟡", 0
    change = (cpa - prev_cpa) / prev_cpa * 100
    if change <= -5:
        return "🟢", change
    elif change >= 10:
        return "🔴", change
    else:
        return "🟡", change

def budget_bar(amount, total, width=20):
    ratio = amount / total if total > 0 else 0
    filled = int(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar} {ratio*100:.0f}%"

def get_ai_suggestions(data_summary):
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    prompt = f"""
퍼포먼스 마케팅 전문가로서 아래 데이터를 분석해서 한국어로 답해줘.

{data_summary}

아래 형식으로 정확히 작성해줘 (이모지 포함):
🔴 긴급: (지금 당장 해야 할 것 - 구체적 수치 포함)
🟡 권장: (이번 주 안에 할 것 - 예상 효과 포함)
🟢 선택: (여유 있을 때 할 것)
💰 예산 시뮬레이션: (예산 조정 시 예상 전환 변화)
"""
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def render_dashboard(channels, is_demo=False):
    label = " [dim](데모)[/dim]" if is_demo else ""
    console.print(f"\n[bold blue]📊 Hydra Growth CLI[/bold blue]{label}")
    console.print(f"[dim]최근 7일 · {(datetime.now()-timedelta(days=7)).strftime('%Y.%m.%d')} ~ {datetime.now().strftime('%Y.%m.%d')}[/dim]\n")

    # 성과 테이블
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold white on blue")
    table.add_column("채널", style="cyan", width=12)
    table.add_column("비용", justify="right", style="yellow", width=14)
    table.add_column("전환", justify="right", style="green", width=8)
    table.add_column("CPA", justify="right", width=14)
    table.add_column("CTR", justify="right", style="dim", width=8)
    table.add_column("vs 지난주", justify="right", width=12)

    total_spend = sum(c['spend'] for c in channels)

    for c in channels:
        status_icon, change = cpa_status(c['cpa'], c.get('prev_cpa', 0))
        cpa_text = Text(f"₩{c['cpa']:,.0f}")
        if status_icon == "🟢":
            cpa_text.stylize("green")
        elif status_icon == "🔴":
            cpa_text.stylize("red")
        else:
            cpa_text.stylize("yellow")

        if change > 0:
            change_str = f"[red]▲{abs(change):.0f}%[/red]"
        elif change < 0:
            change_str = f"[green]▼{abs(change):.0f}%[/green]"
        else:
            change_str = "[dim]-[/dim]"

        table.add_row(
            f"{status_icon} {c['name']}",
            f"₩{c['spend']:,.0f}",
            f"{c['conversions']}건",
            cpa_text,
            f"{c['ctr']:.1f}%",
            change_str
        )

    console.print(table)

    # 예산 비중 바
    console.print("\n[bold]예산 비중[/bold]")
    for c in channels:
        bar = budget_bar(c['spend'], total_spend)
        console.print(f"  [cyan]{c['name']:<10}[/cyan] {bar}  ₩{c['spend']:,.0f}")

    # AI 제안
    console.print("\n[bold yellow]🤖 AI 액션 제안[/bold yellow]")
    with console.status("[dim]분석 중...[/dim]"):
        summary = "\n".join([
            f"{c['name']}: 비용 ₩{c['spend']:,.0f} / 전환 {c['conversions']}건 / CPA ₩{c['cpa']:,.0f} / CTR {c['ctr']:.1f}% / 지난주 대비 CPA {'▲' if c.get('prev_cpa',0) and c['cpa']>c['prev_cpa'] else '▼'}"
            for c in channels
        ])
        suggestion = get_ai_suggestions(summary)

    panel = Panel(suggestion, border_style="yellow", padding=(1, 2))
    console.print(panel)
    console.print()

@app.command()
def status():
    """실제 데이터 기반 성과 현황"""
    with console.status("[bold green]데이터 가져오는 중...[/bold green]"):
        meta = get_meta_data()

    if not meta:
        console.print("[red]데이터를 가져올 수 없어요.[/red]")
        raise typer.Exit()

    channels = [{"name": "메타", **meta}]
    render_dashboard(channels)

@app.command()
def demo():
    """데모 데이터로 미리보기"""
    channels = [
        {"name": "구글", "spend": 2100000, "conversions": 67, "cpa": 31343, "ctr": 4.2, "prev_cpa": 25000},
        {"name": "네이버", "spend": 1250000, "conversions": 38, "cpa": 32894, "ctr": 3.1, "prev_cpa": 34500},
        {"name": "메타",   "spend": 1840000, "conversions": 41, "cpa": 44878, "ctr": 1.8, "prev_cpa": 39000},
    ]
    render_dashboard(channels, is_demo=True)

if __name__ == "__main__":
    app()