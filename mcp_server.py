import sys, os
sys.path.insert(0, os.path.expanduser("~/growth-cli"))
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/growth-cli/.env"))
from main import get_naver_trends, get_gsc_data, get_threads_data, get_meta_data, get_ga4_data

mcp = FastMCP("hydra_growth_mcp")

@mcp.tool(name="hydra_get_threads_insights", annotations={"readOnlyHint": True})
def hydra_get_threads_insights() -> str:
    """Threads 7일 인사이트: 조회수, 좋아요, 댓글, 리포스트, TOP 게시물"""
    data = get_threads_data()
    if not data:
        return "Threads 데이터 없음. THREADS_ACCESS_TOKEN 확인 필요."
    def pct(c, p):
        if not p or abs((c-p)/p*100)>500: return "(신규)"
        v=(c-p)/p*100; return f"({'▲' if v>0 else '▼'}{abs(v):.0f}%)"
    lines=[f"Threads @{data['username']} | 팔로워:{data['followers']:,}",
           f"조회:{data['views']:,} {pct(data['views'],data['views_prev'])}",
           f"좋아요:{data['likes']:,} {pct(data['likes'],data['likes_prev'])}",
           f"댓글:{data['replies']:,} / 리포스트:{data['reposts']:,}"]
    if data.get("top_posts"):
        lines.append("TOP 게시물:")
        for i,p in enumerate(data["top_posts"],1):
            lines.append(f"  {i}위 조회:{p['views']:,} | {p['text'][:60]}")
    return "\n".join(lines)

@mcp.tool(name="hydra_get_naver_trends", annotations={"readOnlyHint": True})
def hydra_get_naver_trends(keywords: str = "") -> str:
    """네이버 DataLab 키워드 트렌드 (최근 3개월). keywords=쉼표구분 예: 기타,통기타"""
    if keywords: os.environ["NAVER_TREND_KEYWORDS"] = keywords
    results = get_naver_trends()
    if not results: return "네이버 트렌드 데이터 없음."
    lines = ["네이버 키워드 트렌드 (3개월)"]
    for r in results:
        sign = "+" if r["diff"]>0 else ""
        lines.append(f"{r['trend']} {r['keyword']} 검색량:{r['latest']} 전월대비:{sign}{r['diff']}")
    return "\n".join(lines)

@mcp.tool(name="hydra_get_seo_report", annotations={"readOnlyHint": True})
def hydra_get_seo_report() -> str:
    """Google Search Console SEO 현황 (7일): 클릭, 노출, 순위, TOP 키워드"""
    results = get_gsc_data()
    if not results: return "GSC 데이터 없음. Google 인증 확인 필요."
    lines = ["SEO 현황 (7일)"]
    for s in results:
        lines.append(f"사이트: {s['site']}")
        lines.append(f"클릭:{s['clicks']} 노출:{s['impressions']} 평균순위:{s['avg_position']:.1f}위")
        for kw in (s.get("top_keywords") or [])[:5]:
            lines.append(f"  {kw['query']} | 클릭:{kw['clicks']} 순위:{kw['position']:.1f}위")
    return "\n".join(lines)

@mcp.tool(name="hydra_get_meta_ads", annotations={"readOnlyHint": True})
def hydra_get_meta_ads() -> str:
    """Meta 광고 성과 (7일): 지출, 전환수, CPA, CTR"""
    data = get_meta_data()
    if not data: return "Meta 광고 데이터 없음."
    lines = [f"Meta 광고 (7일) | 지출:{data.get('spend',0):,.0f}원",
             f"전환:{data.get('conversions',0)} CPA:{data.get('cpa',0):,.0f}원 CTR:{data.get('ctr',0):.2f}%"]
    if data.get("prev_spend"):
        c=(data.get('spend',0)-data['prev_spend'])/data['prev_spend']*100
        lines.append(f"전주대비: {'▲' if c>0 else '▼'}{abs(c):.0f}%")
    return "\n".join(lines)

@mcp.tool(name="hydra_get_ga4_data", annotations={"readOnlyHint": True})
def hydra_get_ga4_data() -> str:
    """GA4 트래픽 (7일): 세션, 전환, 매출"""
    data = get_ga4_data()
    if not data: return "GA4 데이터 없음."
    lines = [f"GA4 (7일) | 세션:{data.get('sessions',0):,} 전환:{data.get('conversions',0):,} 매출:{data.get('revenue',0):,.0f}원"]
    if data.get("prev_conversions") and data["prev_conversions"]>0:
        c=(data.get('conversions',0)-data['prev_conversions'])/data['prev_conversions']*100
        lines.append(f"전환 전주대비: {'▲' if c>0 else '▼'}{abs(c):.0f}%")
    return "\n".join(lines)

@mcp.tool(name="hydra_full_report", annotations={"readOnlyHint": True})
def hydra_full_report() -> str:
    """전체 마케팅 통합 리포트: Threads + 네이버트렌드 + SEO + Meta + GA4"""
    sections = []
    t = get_threads_data()
    if t:
        sections.append(f"[Threads] @{t['username']} 조회:{t['views']:,} 좋아요:{t['likes']:,}")
        for p in (t.get("top_posts") or [])[:2]:
            sections.append(f"  TOP: {p['text'][:50]}")
    for r in (get_naver_trends() or [])[:3]:
        sections.append(f"[네이버] {r['keyword']} {r['latest']} {r['trend']}")
    for s in (get_gsc_data() or []):
        sections.append(f"[SEO] {s['site']} 클릭:{s['clicks']} 순위:{s['avg_position']:.1f}위")
    m = get_meta_data()
    if m: sections.append(f"[Meta] 지출:{m.get('spend',0):,.0f}원 CPA:{m.get('cpa',0):,.0f}원")
    g = get_ga4_data()
    if g: sections.append(f"[GA4] 세션:{g.get('sessions',0):,} 전환:{g.get('conversions',0):,}")
    return "Hydra Growth 통합 리포트\n" + "\n".join(sections) if sections else "데이터 없음. .env API 키 확인 필요."



@mcp.tool(name="hydra_demo_report", annotations={"readOnlyHint": True})
def hydra_demo_report() -> str:
    """데모용 통합 리포트. 실제 연결 없이도 마케팅 데이터 분석 시연 가능."""
    return """📊 Hydra Growth 데모 리포트 (샘플 데이터)

[Threads] @lavamusic_kr 조회:12,847 좋아요:342 (▲38%)
  TOP: 기타 처음 시작하는 사람들이 가장 많이 하는 실수 (조회8,201)
  TOP: 독학 3개월차 vs 레슨 3개월차 차이 (조회3,102)

[네이버트렌드] 기타 검색량:68.2 ▲ (+4.1)
[네이버트렌드] 통기타 검색량:41.5 ▲ (+2.8)
[네이버트렌드] 기타레슨 검색량:33.1 ▲ (+5.2)

[SEO] lavamusic.kr 클릭:247 순위:4.2위 (▲1.3)
  키워드: 기타독학 (3위) / 어쿠스틱기타추천 (5위) / 기타레슨비용 (7위)

[Meta광고] 지출:₩320,000 CPA:₩8,900 CTR:2.41%
  전주대비: 지출▲15% / 전환▲28% → ROAS 개선 중

[GA4] 세션:1,842 전환:36 매출:₩1,240,000
  전환 전주대비: ▲22%"""


@mcp.tool(name="hydra_demo_dashboard", annotations={"readOnlyHint": True})
def hydra_demo_dashboard() -> str:
    """마케팅 성과 시각화 대시보드 (데모). Chart.js 차트 + 액션 아이템 + 라이트/다크 토글을 HTML로 반환합니다."""
    return """<!DOCTYPE html>
<html lang=\"ko\" data-theme=\"dark\">
<head>
<meta charset=\"UTF-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<script src=\"https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js\"></script>
<style>
:root{--bg:#111113;--surface:#18181c;--border:#2c2c32;--accent:#6e79d6;--accent-dim:rgba(110,121,214,0.15);--green:#3dd68c;--green-dim:rgba(61,214,140,0.12);--text-primary:#f0f0f2;--text-secondary:#b0b0be;--text-muted:#787888;--chart-grid:#2c2c32;--chart-tick:#787888}
[data-theme=\"light\"]{--bg:#f9f9fb;--surface:#ffffff;--border:#e4e4ea;--accent:#4f5bbf;--accent-dim:rgba(79,91,191,0.08);--green:#1a9e5f;--green-dim:rgba(26,158,95,0.08);--text-primary:#111113;--text-secondary:#4a4a5a;--text-muted:#8a8a9a;--chart-grid:#e8e8f0;--chart-tick:#8a8a9a}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,\'SF Pro Display\',\'Inter\',sans-serif;background:var(--bg);color:var(--text-primary);padding:28px;transition:background .2s,color .2s}
.header{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:24px}
.header h1{font-size:16px;font-weight:600;letter-spacing:-.01em;margin-bottom:4px}
.header .meta{font-size:12px;color:var(--text-muted)}
.header-right{display:flex;align-items:center;gap:10px}
.badge{display:inline-flex;align-items:center;gap:6px;background:var(--accent-dim);border:1px solid rgba(110,121,214,.25);color:var(--accent);font-size:11px;font-weight:500;padding:5px 11px;border-radius:6px}
.dot-live{width:6px;height:6px;background:var(--accent);border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.theme-toggle{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:5px 10px;font-size:12px;color:var(--text-secondary);cursor:pointer}
.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px}
.kpi-label{font-size:11px;color:var(--text-muted);font-weight:500;letter-spacing:.05em;text-transform:uppercase;margin-bottom:10px}
.kpi-value{font-size:26px;font-weight:650;letter-spacing:-.03em;margin-bottom:8px;font-variant-numeric:tabular-nums}
.kpi-change{font-size:11px;font-weight:600;display:inline-flex;align-items:center;gap:3px;padding:3px 8px;border-radius:5px}
.kpi-change.up{color:var(--green);background:var(--green-dim)}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px}
.chart-box,.actions{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px}
.section-label{font-size:11px;font-weight:600;color:var(--text-secondary);letter-spacing:.04em;text-transform:uppercase;margin-bottom:14px}
.actions-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.action-count{font-size:11px;color:var(--text-muted)}
.action-item{display:flex;gap:12px;align-items:flex-start;padding:12px 0;border-bottom:1px solid var(--border)}
.action-item:last-child{border-bottom:none;padding-bottom:0}
.priority-tag{font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;white-space:nowrap;margin-top:1px}
.p1{background:var(--accent-dim);color:var(--accent);border:1px solid rgba(110,121,214,.3)}
.p2{background:var(--green-dim);color:var(--green);border:1px solid rgba(61,214,140,.25)}
.p3{background:rgba(128,128,128,.08);color:var(--text-secondary);border:1px solid var(--border)}
.action-title{font-size:13px;font-weight:600;margin-bottom:4px;letter-spacing:-.01em}
.action-desc{font-size:12px;color:var(--text-secondary);line-height:1.65}
</style>
</head>
<body>
<div class=\"header\">
  <div><h1>Hydra Growth · Marketing Overview</h1><div class=\"meta\">W17 · All channels</div></div>
  <div class=\"header-right\">
    <button class=\"theme-toggle\" onclick=\"toggleTheme()\" id=\"themeBtn\">☀️ Light</button>
    <div class=\"badge\"><span class=\"dot-live\"></span>Live via MCP</div>
  </div>
</div>
<div class=\"kpi-row\">
  <div class=\"kpi\"><div class=\"kpi-label\">Threads Views</div><div class=\"kpi-value\">12,847</div><span class=\"kpi-change up\">↑ 38% WoW</span></div>
  <div class=\"kpi\"><div class=\"kpi-label\">SEO Avg Rank</div><div class=\"kpi-value\">#4.2</div><span class=\"kpi-change up\">↑ 1.3 positions</span></div>
  <div class=\"kpi\"><div class=\"kpi-label\">Meta CPA</div><div class=\"kpi-value\">₩8,900</div><span class=\"kpi-change up\">전환 ↑ 28%</span></div>
  <div class=\"kpi\"><div class=\"kpi-label\">GA4 Revenue</div><div class=\"kpi-value\">₩1.24M</div><span class=\"kpi-change up\">↑ 22% WoW</span></div>
</div>
<div class=\"charts\">
  <div class=\"chart-box\"><div class=\"section-label\">Threads · Top Posts</div><canvas id=\"tc\" height=\"130\"></canvas></div>
  <div class=\"chart-box\"><div class=\"section-label\">Naver · Keyword Trend</div><canvas id=\"nc\" height=\"130\"></canvas></div>
</div>
<div class=\"actions\">
  <div class=\"actions-header\"><div class=\"section-label\" style=\"margin:0\">Action Items</div><div class=\"action-count\">3 open</div></div>
  <div class=\"action-item\"><span class=\"priority-tag p1\">P1</span><div><div class=\"action-title\">기타레슨 랜딩페이지 최적화</div><div class=\"action-desc\">네이버 검색량 +5.2 상승. 내부링크 강화 시 이달 전환 20% 개선 가능.</div></div></div>
  <div class=\"action-item\"><span class=\"priority-tag p2\">P2</span><div><div class=\"action-title\">Threads 초보자 시리즈 2편 발행</div><div class=\"action-desc\">"실수" 게시물 8,201회 1위. 같은 포맷 시리즈 이어가면 알고리즘 탈 가능성 높음.</div></div></div>
  <div class=\"action-item\"><span class=\"priority-tag p3\">P3</span><div><div class=\"action-title\">Meta 광고 예산 10% 증액 검토</div><div class=\"action-desc\">ROAS 개선 중, CPA ₩8,900 효율적. 스케일업 타이밍.</div></div></div>
</div>
<script>
let d=true,tC,nC;
function toggleTheme(){d=!d;document.documentElement.setAttribute("data-theme",d?"dark":"light");document.getElementById("themeBtn").textContent=d?"☀️ Light":"🌙 Dark";upd()}
function gc(){return{g:d?"#2c2c32":"#e8e8f0",t:d?"#787888":"#8a8a9a",b1:d?"#6e79d6":"#4f5bbf",b2:d?"#454880":"#9aa0d8",b3:d?"#2c2c38":"#e8e8f0",l1:d?"#6e79d6":"#4f5bbf",l2:d?"#3dd68c":"#1a9e5f",l3:d?"#b0b0be":"#8a8a9a",lg:d?"#b0b0be":"#4a4a5a"}}
function upd(){const c=gc();tC.data.datasets[0].backgroundColor=[c.b1,c.b2,c.b3];[tC,nC].forEach(ch=>{ch.options.scales.x.grid.color=c.g;ch.options.scales.x.ticks.color=c.t;ch.options.scales.y.grid.color=c.g;ch.options.scales.y.ticks.color=c.t;ch.update()});nC.data.datasets[0].borderColor=nC.data.datasets[0].pointBackgroundColor=gc().l1;nC.data.datasets[1].borderColor=nC.data.datasets[1].pointBackgroundColor=gc().l2;nC.data.datasets[2].borderColor=nC.data.datasets[2].pointBackgroundColor=gc().l3;nC.options.plugins.legend.labels.color=gc().lg;nC.update()}
const c=gc(),f={size:11,family:"system-ui,sans-serif"};
tC=new Chart(document.getElementById("tc"),{type:"bar",data:{labels:["실수 게시물","독학 vs 레슨","기타"],datasets:[{data:[8201,3102,1544],backgroundColor:[c.b1,c.b2,c.b3],borderRadius:5,borderSkipped:false}]},options:{plugins:{legend:{display:false}},scales:{x:{grid:{color:c.g},ticks:{color:c.t,font:f}},y:{grid:{color:c.g},ticks:{color:c.t,font:f}}}}});
nC=new Chart(document.getElementById("nc"),{type:"line",data:{labels:["1월","2월","3월","4월"],datasets:[{label:"기타",data:[60.1,62.3,64.1,68.2],borderColor:c.l1,borderWidth:2,tension:0.4,pointRadius:3,pointBackgroundColor:c.l1,backgroundColor:"transparent"},{label:"통기타",data:[36.2,37.8,38.7,41.5],borderColor:c.l2,borderWidth:2,tension:0.4,pointRadius:3,pointBackgroundColor:c.l2,backgroundColor:"transparent"},{label:"기타레슨",data:[24.1,26.3,27.9,33.1],borderColor:c.l3,borderWidth:2,tension:0.4,pointRadius:3,pointBackgroundColor:c.l3,backgroundColor:"transparent"}]},options:{plugins:{legend:{labels:{color:c.lg,font:f,boxWidth:8,boxHeight:8}}},scales:{x:{grid:{color:c.g},ticks:{color:c.t,font:f}},y:{grid:{color:c.g},ticks:{color:c.t,font:f}}}}});
</script>
</body>
</html>"""


if __name__ == "__main__":
    mcp.run(transport="stdio")
